# Plan 003: Make executor failures transactional

> Executor instructions: Keep the patch bounded to executor failure handling and tests. Do not weaken policy, secret scanning, approval, or CI requirements. Stop on a STOP condition. The reviewer updates plan status.
>
> Drift check: `git diff --stat 843a5cdf9ba3c944f844e6eea78030a8a01857bb..HEAD -- aurora/executor/service.py aurora/executor/patch.py tests/test_executor_service.py docs/architecture/overview.md docs/runbooks/end_to_end.md`

## Status

- Priority: P1
- Effort: M
- Risk: MED
- Depends on: none
- Category: data integrity / reliability
- Planned at: `843a5cd`, 2026-07-22

## Why this matters

Executor patches are applied before secret scanning, CI, and final policy
evaluation. When any later stage fails, `ExecutorService.apply` raises but
leaves the workspace modified even though a rollback helper already exists and
the architecture claims auto-revert behavior. An unknown profile is also
detected only after mutation. Failed automation must restore the exact clean
pre-run workspace or clearly report that recovery failed.

## Current evidence

- `aurora/executor/service.py:51-70` validates and applies patches before running CI.
- `aurora/executor/service.py:103-109` can reject policy after patches are already present.
- Exception handlers at `aurora/executor/service.py:71-83` record failure but do not roll back.
- `aurora/executor/service.py:143-147` detects an unknown profile only when CI begins.
- `aurora/executor/patch.py:56-64` has a reverse-apply helper but ignores its return code and is unused.
- There is no executor transaction regression test.

## Scope

In scope:

- `aurora/executor/service.py`
- `aurora/executor/patch.py`
- `tests/test_executor_service.py` (new)
- `docs/architecture/overview.md`
- `docs/runbooks/end_to_end.md`

Out of scope:

- Weakening required CI/policy steps or secret scanning.
- Resetting, cleaning, or discarding user changes that existed before the run.
- Committing successful executor changes.
- Adding distributed locks or changing sandbox implementations.

## Steps

### Step 1: Complete all non-mutating validation first

Validate the SelfEdit, requested profile, workspace cleanliness, patch dry-runs,
and required configuration before applying the first patch. Dry-run every patch
against the expected sequence where possible; if sequential dependencies make
that impossible, keep an explicit applied-patch journal from the first mutation.
An unknown profile must fail with zero workspace changes.

Verify: unit tests assert the workspace remains byte-for-byte clean for invalid
profiles and invalid patches.

### Step 2: Journal and reverse applied patches on failure

Track each successfully applied diff. If secret scanning, approval, CI,
artifact generation, or policy evaluation fails, reverse applied diffs in
strict reverse order. Make `patch.rollback` check and report git's return code.
Preserve the original exception when rollback succeeds. If rollback fails,
raise a composite recovery error, record both failure categories, and do not run
destructive git reset/clean commands.

Verify: tests use a real temporary git repository and injected CI/policy/secret
failures to assert tracked files match HEAD after failure.

### Step 3: Preserve successful behavior and telemetry

A successful executor run must leave intended changes present and return an
additive structured result or summary path that callers can consume. Failure
telemetry should state whether rollback succeeded without embedding diff content
or secrets.

Verify: a success test asserts the patch remains and existing summary artifacts
are produced; Ruff, mypy, and the full suite pass.

### Step 4: Update operator guidance

Document transactional scope, recovery failure handling, and the fact that
pre-existing user changes are never discarded. Add a runbook check for manual
inspection when reverse apply cannot restore the workspace.

## Done criteria

- All feasible validation occurs before mutation.
- Every post-apply failure attempts bounded reverse-order rollback.
- Successful rollback restores the clean pre-run tracked state.
- Rollback failure is explicit and never triggers reset/clean.
- Successful runs retain changes and existing security/policy gates.
- Full project gates pass with only in-scope files changed.

## STOP conditions

- Correct recovery would require deleting untracked user files or resetting unrelated changes.
- The existing patch format cannot be reversed reliably and no bounded journal can solve it.
- A test reveals successful runs are expected to auto-commit or push.
- Verification fails twice.
