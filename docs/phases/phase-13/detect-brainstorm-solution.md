# Detect And Brainstorm - Phase 13

## What production proved

- Phase 12 solved the no-answer closeout gap.
- FE Credit regression failed for a different reason: session expiry, not retrieval logic.
- Production exposed contradictory state: `session_status = EXPIRED` while `health_status = HEALTHY`.

## Options considered

### Option A - Small contained fix on step error handling

Reject.

This would only relabel one failure path and would leave run admission and monitor truth inconsistent.

### Option B - New phase for session truth and re-auth admission

Choose this.

This matches the real boundary:

- health truth
- admission control
- runtime expiry propagation
- terminal outcome semantics
- operator surface

## Locked recommendation

Open Phase 13 and treat the issue as a production runtime contract problem, not as a retrieval bug.
