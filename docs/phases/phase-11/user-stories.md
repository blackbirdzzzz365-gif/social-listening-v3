# User Stories - Phase 11

## Epic 1 - Planner resilience

### Story 1.1

As an operator,
I want session analysis and clarifications to survive transient provider overload,
so that I can continue topic setup without manually retrying every failure.

Acceptance criteria:

- transient retryable planner failures are retried automatically with bounded backoff
- if recovery succeeds, the session is created or updated normally
- if recovery fails, the API returns a planner/provider failure instead of a generic validation error

### Story 1.2

As an operator,
I want to inspect planner provider attempts,
so that I can understand whether fallback or retries were used.

Acceptance criteria:

- session payload exposes planning metadata for the latest analysis/clarification stage
- plan payload exposes generation metadata for plan creation/refinement
- metadata contains attempt count, provider used, fallback used, and failure reason

## Epic 2 - Image-bearing evidence acquisition

### Story 2.1

As a user researching image-heavy topics,
I want the planner to search with image-bearing posture early,
so that the system does not waste most of the run on generic product-term noise.

Acceptance criteria:

- retrieval profile supports image-bearing intent families
- planner/runtime can prioritize those families for image-led topics

### Story 2.2

As an operator,
I want timeout runs to leave a salvageable audit record,
so that I can tell whether search found evidence before timing out.

Acceptance criteria:

- stuck `SEARCH_POSTS` steps publish collected vs persisted progress
- timeout terminal artifacts include salvage metadata
- audit can distinguish "no evidence found" from "evidence collected but not persisted"

### Story 2.3

As a product team,
I want production audit to prove whether vision fallback contributed,
so that we can decide whether to deepen or reduce multimodal investment.

Acceptance criteria:

- audit reports include image-bearing counts and vision-assisted decision counts
- at least one Phase 11 case can conclude either `ANSWER_READY`, `NO_VISUAL_EVIDENCE`, or a classified failure with salvage evidence
