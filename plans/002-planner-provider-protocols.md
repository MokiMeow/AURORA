# Plan 002: Correct planner provider protocols and retries

> Executor instructions: Execute step by step and preserve all public data models unless an additive field is explicitly listed. Stop on a STOP condition. The reviewer owns the plan index.
>
> Drift check: `git diff --stat 843a5cdf9ba3c944f844e6eea78030a8a01857bb..HEAD -- aurora/planner/client.py aurora/planner/config.py aurora/planner/config_loader.py tests/test_planner_client.py configs/model.yaml docs/architecture/overview.md`

## Status

- Priority: P1
- Effort: M
- Risk: MED
- Depends on: none
- Category: correctness / reliability
- Planned at: `843a5cd`, 2026-07-22

## Why this matters

The planner advertises Ollama, OpenAI, Anthropic, and Gemini adapters, but the
wire behavior is not provider-correct. Ollama receives `stream` under `options`
instead of at the request root and its NDJSON stream is parsed as one JSON
document. OpenAI streaming deltas are ignored. Every API key is sent as a Bearer
token even though Anthropic and Gemini require provider-specific headers. HTTP
4xx responses can be treated as empty successful output, while all thrown
errors are retried indiscriminately. These defects make configured routes fail
or add latency while hiding the real provider error.

## Current evidence

- `aurora/planner/client.py:67-87` retries every exception and only explicitly rejects status codes >= 500.
- `aurora/planner/client.py:143-148` places Ollama `stream` under `options`.
- `aurora/planner/client.py:153-159` always builds `Authorization: Bearer`.
- `aurora/planner/client.py:161-187` only recognizes SSE and treats multi-line Ollama NDJSON as ordinary JSON.
- `aurora/planner/client.py:189-205` reads OpenAI `message.content` but not streaming `delta.content`.
- Official provider references confirm Ollama uses a top-level `stream` field and NDJSON, Anthropic Messages requires its API/version headers, and Gemini accepts `x-goog-api-key`.

## Scope

In scope:

- `aurora/planner/client.py`
- `aurora/planner/config.py`
- `aurora/planner/config_loader.py`
- `tests/test_planner_client.py`
- `configs/model.yaml`
- `docs/architecture/overview.md`

Out of scope:

- Changing model selection, endpoint ownership, or enabling cloud routes by default.
- Adding provider SDK dependencies.
- Logging response bodies or credentials.
- Changing critic consensus semantics.

## Steps

### Step 1: Build provider-correct request metadata

Keep JSON-over-httpx but centralize payload/header construction per provider.
Ollama must send top-level `stream`; OpenAI keeps Bearer auth; Anthropic uses
`x-api-key` and an explicit configurable/default API version; Gemini uses
`x-goog-api-key`. If a configured cloud route names a key environment variable
that is absent, fail clearly before network I/O without printing the key name's
value. Add an optional provider field to critic configuration so critic auth is
not inferred from display names.

Verify: focused unit tests inspect outgoing headers and bodies for all four providers.

### Step 2: Classify retries explicitly

Treat 2xx as success. Retry only transport/timeouts and HTTP 408, 425, 429, and
5xx up to the configured attempt count. Return nonretryable 4xx errors after one
attempt. Keep exponential backoff bounded and inject a sleep seam for tests.
Honor a valid bounded `Retry-After` value if present. Error messages may include
provider, status, and request ID header but never response bodies or credentials.

Verify: tests assert exact call counts for 401, 429, 501, timeout recovery, and exhausted retries.

### Step 3: Parse each supported response stream

Support Ollama `application/x-ndjson` chunks including mid-stream `error`
records; OpenAI SSE `choices[].delta.content`; Anthropic SSE text deltas; and
the existing non-streaming response shapes. Ignore terminal sentinel lines but
raise a clear error when a successful response contains no usable content.
Malformed chunks may be skipped only when later valid content exists.

Verify: focused streaming tests cover accumulated text, terminal markers,
mid-stream provider errors, and an empty-content failure.

### Step 4: Document the contract

Document supported auth environment variables, response modes, retryable
statuses, and the fact that cloud routes remain opt-in. Keep sample values free
of credentials.

Verify: full Ruff, mypy, and pytest gates pass.

## Done criteria

- Ollama, OpenAI, Anthropic, and Gemini requests use the documented wire shape.
- Nonretryable failures make one request; transient failures retry within bounds.
- Streaming and non-streaming outputs produce the same content abstraction.
- Missing credentials fail before network I/O and no secret value is logged.
- Full project gates pass with only in-scope files changed.

## STOP conditions

- A provider requires a new SDK or credential type that cannot be represented by the current config without a product decision.
- Correct streaming requires changing PlannerResponse or SelfEdit schemas incompatibly.
- Tests would need live provider credentials or paid API calls.
- Verification fails twice.
