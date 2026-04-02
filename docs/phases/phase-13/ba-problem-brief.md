# BA Problem Brief - Phase 13

## Problem statement

The product now handles zero-evidence outcomes correctly, but it still fails a more basic promise: a browser-backed run can start even when the Facebook session is already expired.

This produces a bad user and operator outcome:

- the run looks like a product failure instead of an action-required state
- no useful evidence is collected
- the operator is not told clearly that re-authentication is the next required action
- the health model becomes contradictory and therefore hard to trust

## User problem

When the session is not runnable, the user does not want a fake attempt. They want the system to tell the truth immediately:

- the account needs re-authentication
- the run cannot proceed yet
- once re-auth is completed, the run can be retried safely

## Business impact

- wasted browser/runtime budget on doomed runs
- confusing production audit signals
- harder operator support and slower incident recovery
- lower trust in monitor statuses and automation loops

## Desired business outcome

- stop doomed browser-backed runs before evidence collection starts
- turn auth/session problems into explicit operator actions
- keep production audits clean by separating retrieval quality issues from session validity issues

## Constraints

- Phase 12 no-answer closeout must stay intact
- healthy valid-session flows must not regress
- platform auth guard remains in place

## Decision

Create a dedicated phase for `Session Truthfulness And Re-Auth Admission` instead of a contained patch, because the issue spans runtime truth, admission control, terminal semantics, and operator visibility.
