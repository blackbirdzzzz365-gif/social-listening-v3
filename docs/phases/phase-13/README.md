# Phase 13 - Session Truthfulness And Re-Auth Admission

## Why this phase exists

Phase 12 solved the original product gap from the no-answer path: production can now end a zero-evidence run with a real final outcome instead of only a terminal badge.

But the latest live regression case exposed a different production contract bug:

- `run-ba6fc47411` failed at `step-1 SEARCH_POSTS` with `Facebook session expired`
- no evidence was collected
- the run ended as generic `STEP_ERROR`
- production health still showed an impossible mixed state:
  - `session_status = EXPIRED`
  - `health_status = HEALTHY`

That means the system still allows a browser-backed run to start even when the Facebook session is already not runnable.

## Locked direction

- Browser session truth must become first-class runtime state.
- `HEALTHY + EXPIRED` must not exist at the same time.
- Browser-backed runs must be blocked before `step-1` when session truth is not runnable.
- The operator must receive a clear terminal outcome such as `REAUTH_REQUIRED`, not a generic `STEP_ERROR`.
- Monitor/API must show why the run cannot proceed and what the operator needs to do next.

## Expected outcomes

- An expired Facebook session is surfaced as a non-runnable state before a run starts.
- Browser-backed runs are preflight-blocked with a deterministic re-auth outcome.
- Mid-run session expiry degrades health truth immediately and exits with a clear auth-specific terminal reason.
- Existing no-answer and answer-ready flows remain unchanged once the session is valid.

## Scope

### In scope

- session truth contract and health-state invariants
- preflight re-auth admission gate for browser-backed runs
- runtime propagation when browser actions detect expired Facebook session
- explicit terminal outcome for re-auth-required runs
- API + monitor visibility for session truth and re-auth action
- Phase 13 case pack and production revalidation

### Out of scope

- planner redesign
- retrieval strategy changes
- image-bearing evidence acquisition work
- replacing platform auth gate or changing SSO product policy

## Success criteria

- A run like `run-ba6fc47411` no longer starts `step-1` and then dies with generic `STEP_ERROR`.
- Production never exposes `session_status = EXPIRED` while still marking the account runnable/healthy.
- Operator-facing monitor clearly states when re-auth is required.
- A valid-session control case still reaches the same business outcome as before.
