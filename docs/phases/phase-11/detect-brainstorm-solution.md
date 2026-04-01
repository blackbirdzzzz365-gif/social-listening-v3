# Detect + Brainstorm - Phase 11

## Production truths that triggered this phase

- `run-99080352c3` proved Phase 10 answer-closeout for a text-led case.
- `run-8d38748157` proved timeout taxonomy and heartbeat, but not image-bearing evidence acquisition.
- Planning for the image-bearing flow hit transient provider overload during clarification / plan creation.
- Heartbeat showed live collection progress, but persisted records stayed at `0`.

## Key diagnosis

The current system is strong at:

- controlling execution
- classifying runtime failure
- answering when text evidence reaches accepted state

The current system is weak at:

- surviving planner provider instability
- turning long-running image-bearing collection into persisted evidence or at least salvageable audit truth

## Rejected alternatives

### Alternative A - Just increase timeout

Rejected because it only hides the loss boundary. It does not explain what was collected before timeout and may increase budget burn.

### Alternative B - Add more generic queries

Rejected because the production evidence says image-bearing cases need a different posture, not just more of the same query family.

### Alternative C - Treat provider overload as random ops noise

Rejected because users experience it during session setup. That makes it a product contract issue, not only an infra issue.

## Chosen direction

Build Phase 11 around:

- provider-resilient planning
- image-bearing retrieval posture
- timeout salvage and auditability

This preserves Phase 10 strengths while closing the next visible user-value gap.
