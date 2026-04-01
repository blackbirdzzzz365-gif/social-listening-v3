# User Stories - Phase 12

## Epic: No-answer closeout

### Story 1

As an end user, when a run finds no trustworthy evidence, I want to see a final explanation so I know the system finished and why it could not answer.

Acceptance criteria:

- terminal run returns a final no-answer payload
- payload explains the run finished intentionally, not due to crash
- payload summarizes attempted query paths and dominant reject patterns

### Story 2

As an operator, I want to see which query paths were attempted and why they failed so I can decide whether to retry with a better scope.

Acceptance criteria:

- final outcome includes attempted queries with zero-accept counts
- final outcome includes top reject reason clusters
- final outcome includes recommended next actions

## Epic: Goal-aware exhaustion

### Story 3

As the runtime, I want to stop obviously exhausted weak tails earlier so I do not waste browser budget after the answer is already impossible under the current plan.

Acceptance criteria:

- repeated weak zero-accept paths can trigger early run exhaustion
- skipped tail steps are visible in run state or checkpoint output
- terminal outcome remains `NO_ELIGIBLE_RECORDS`, not generic failure

### Story 4

As a product owner, I want answer-ready runs to remain unchanged so Phase 12 does not regress successful paths.

Acceptance criteria:

- an existing answer-ready regression case still reaches `ANSWER_READY`
- no-answer closeout does not run over answer-ready runs in a way that hides themes/results
