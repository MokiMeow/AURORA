# Plan 004: Turn local API controls into a real loopback service

> Executor instructions: Implement only a local, unauthenticated loopback health/status service. Do not expose a remote bind or invent a public automation API. Stop on any STOP condition. The reviewer owns the plan index.
>
> Drift check: `git diff --stat 843a5cdf9ba3c944f844e6eea78030a8a01857bb..HEAD -- aurora/api cli/main.py tests/test_cli_api.py docs/cli/api.md README.md`

## Status

- Priority: P2
- Effort: M
- Risk: MED
- Depends on: Plan 001
- Category: feature / operational correctness
- Planned at: `843a5cd`, 2026-07-22

## Why this matters

The CLI advertises `api start`, `api stop`, and `api status`, but the service
only writes a JSON file saying "running". It opens no socket, performs no health
check, stores no process identity, and can report a stale running state forever.
For a local-first tool, these controls should manage a real loopback process or
state clearly that the service is stopped.

## Current evidence

- `aurora/api/service.py:19-23` describes an external manager, but no manager exists in the repository.
- `aurora/api/service.py:25-38` only writes state for start/stop.
- `aurora/api/service.py:40-50` trusts stored JSON without probing a process.
- `cli/main.py:1010-1040` exposes the state-only methods as API controls.
- `scripts/load_test_k6.js` expects `http://localhost:8000/health`, but no repository code serves it.

## Scope

In scope:

- `aurora/api/service.py`
- `aurora/api/server.py` (new)
- `aurora/api/__init__.py`
- `cli/main.py`
- `tests/test_cli_api.py`
- `docs/cli/api.md` (new)
- `README.md`

Out of scope:

- Binding outside loopback.
- Planner/executor mutation endpoints, authentication, TLS, CORS, user data, or remote access.
- Replacing a general process supervisor.
- Killing a process unless its persisted identity and health endpoint match AURORA.

## Steps

### Step 1: Add a minimal loopback HTTP runtime

Use the Python standard library to serve `GET /health` and `GET /v1/status` on
`127.0.0.1`. Responses are small JSON documents containing service status,
version, and start time only. All other routes return 404; non-GET methods
return 405. Add graceful SIGINT/SIGTERM shutdown and no request logging that can
capture secrets.

Verify: handler tests cover health, status, 404, and 405 without opening a public interface.

### Step 2: Manage a verified child process

`APIService.start` should launch `sys.executable -m aurora.api.server` without a
shell, wait for bounded loopback health, and persist host, port, PID, and start
time atomically. Starting twice should return the existing healthy state.
`status` must verify both process liveness and the AURORA health response; stale
or malformed state becomes stopped. `stop` must terminate only the verified
managed process, wait within a bound, and then update state. Hide background
windows on Windows and detach safely on POSIX.

Verify: service tests inject process/probe seams for idempotence, stale state,
bounded startup failure, and safe stop targeting.

### Step 3: Preserve CLI shape and add useful output

Keep `aurora-se api start|stop|status`. Add only bounded optional controls such
as `--port` and `--timeout`; host remains fixed to loopback. Render PID/URL in
text and JSON-compatible output without changing other command groups.

Verify: `python -m pytest tests/test_cli_api.py` passes and leaves no child process or timer behind.

### Step 4: Document the boundary

Add CLI documentation and README guidance for local health usage, state-file
recovery, and the deliberate absence of remote/authenticated automation routes.

Verify: Ruff, mypy, full pytest, and an isolated installed-wheel smoke test pass.

## Done criteria

- Start creates a real loopback service and waits for health.
- Status cannot report stale state as running.
- Stop targets only the verified managed AURORA process.
- No service binds to a non-loopback address.
- Tests leave no background process behind.
- Full gates pass with only in-scope files changed.

## STOP conditions

- Cross-platform process identity cannot be verified without a new dependency.
- Safe stop would require terminating an unverified PID.
- A requested endpoint would expose workspace data or mutation controls.
- Verification fails twice.
