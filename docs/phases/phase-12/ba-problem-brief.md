# BA Problem Brief - Phase 12

## Problem framing

The system can already detect when no trustworthy evidence survived pre-AI gating.

The problem is that this detection is only reflected as backend state:

- `completion_reason=NO_ELIGIBLE_RECORDS`
- `answer_status=NO_ELIGIBLE_RECORDS`

For the user, that is not a complete product outcome.

## User pain

- The user cannot tell whether the system:
  - is still working
  - failed
  - or deliberately found no trustworthy answer
- The user does not see:
  - which query paths were attempted
  - why evidence was rejected
  - whether the run should be retried with a different angle

## Business impact

- The product looks unfinished even when the backend behaved correctly.
- Long weak plan tails waste browser budget without increasing answer probability.
- Operators have to inspect logs or reports manually to explain outcomes that should already be in-product.

## Desired business outcome

- Zero-evidence runs end with a clear, explainable, user-facing result.
- The system spends less budget on obviously exhausted paths.
- Operators can distinguish:
  - “no answer because no valid evidence exists under this search scope”
  - from “no answer because the system failed”

## Non-goals

- We are not trying to make every weak run produce an answer.
- We are trying to make every weak run produce a final, trustworthy explanation.
