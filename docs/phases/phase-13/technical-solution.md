# Technical Solution - Phase 13

## Solution summary

Phase 13 adds a truth-first control layer before and during browser-backed execution:

1. `session truth contract`
2. `re-auth admission gate`
3. `auth-specific terminal outcome and operator surface`

The goal is to prevent generic step failures when the real problem is simply that the Facebook session is no longer valid.

## Track A - Session truth contract

### A1. Normalize runnable state

Make runtime health derive a truthful `runnable` decision from session state. At minimum:

- `session_status = VALID` can be runnable
- `session_status = EXPIRED` cannot be runnable
- `HEALTHY + EXPIRED` must be impossible

Add explicit reason fields where needed:

- `health_block_reason`
- `action_required`
- `last_session_check_at`

### A2. Truthful degradation

When browser runtime detects session expiry:

- update health state immediately
- mark session as expired
- mark account as non-runnable
- preserve the concrete reason for operators and later audits

## Track B - Re-auth admission gate

### B1. Preflight before step execution

Before a browser-backed run moves from `QUEUED` or `RUNNING` into the first browser step:

- check current session truth
- if not runnable, do not start `step-1`
- terminate the run deterministically as `REAUTH_REQUIRED`

### B2. Mid-run expiry handling

If session expiry is discovered during a browser step:

- stop the step
- update health truth immediately
- terminate the run with auth-specific classification, not generic `STEP_ERROR`
- preserve salvage if anything was already collected

## Track C - Terminal semantics

### C1. Dedicated outcome

Introduce a first-class terminal contract for auth problems. Preferred shape:

- `status = DONE`
- `completion_reason = REAUTH_REQUIRED`
- `failure_class = AUTH_SESSION_EXPIRED` only when useful for engineering detail
- optional `answer_status = REAUTH_REQUIRED`

The product meaning is action-required, not product failure.

### C2. No regression rule

Do not change:

- Phase 12 no-answer closeout
- answer-ready closeout
- planner/provider resilience logic

## Track D - API and operator surface

### D1. Browser status

Expose explicit fields for:

- `session_status`
- `health_status`
- `runnable`
- `action_required`
- `last_checked`

### D2. Monitor UI

Show:

- session expired state distinctly
- why new runs are blocked
- what operator action is needed
- when the last successful validation happened

## Exit criteria

- Expired-session runs are blocked before `step-1`.
- Production cannot expose `HEALTHY + EXPIRED`.
- FE Credit-style auth regressions produce `REAUTH_REQUIRED` instead of generic `STEP_ERROR`.
- A valid-session control case still behaves like Phase 12.
