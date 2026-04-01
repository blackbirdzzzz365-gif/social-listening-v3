# Phase 12 - No-Answer Closeout And Goal-Aware Exhaustion

## Why this phase exists

Run [run-6ae4a961c0](/Users/nguyenquocthong/project/social-listening-v3-worktrees/codex-phase-12/reports/production/run-6ae4a961c0/final_report.md) proved a product gap that Phase 11 did not cover:

- the run ended correctly as `DONE / NO_ELIGIBLE_RECORDS`
- all `198` records were rejected
- no label/theme work started, which is correct
- but the user still received no real final outcome beyond a terminal status badge

That means the system already knows when it has no trustworthy answer, but it still does not know how to close the loop with a user-facing explanation.

## Locked direction

- `NO_ELIGIBLE_RECORDS` must become a first-class final outcome, not only a technical terminal status.
- The product must explain why no answer was produced:
  - what was searched
  - why records were rejected
  - why the run stopped
  - what the next best action is
- If a plan is already exhausted with repeated zero-accept weak paths, the runner should stop earlier instead of spending the full tail budget.

## Expected outcomes

- Every terminal run produces a final outcome payload:
  - `ANSWER_READY`
  - `NO_ELIGIBLE_RECORDS`
  - `NO_ANSWER_CONTENT`
  - `FAILED` with salvage truth where relevant
- Zero-evidence runs generate a deterministic no-answer summary with reject reasons, attempted queries, and next-step guidance.
- Monitor/API expose final outcome details instead of only badges.
- Goal-aware exhaustion cuts off obviously hopeless tails once repeated weak zero-accept paths make the answer impossible under the current plan.

## Scope

### In scope

- terminal no-answer outcome model and persistence
- deterministic no-answer closeout service
- goal-aware exhaustion policy for repeated weak zero-accept paths
- API + monitor surface for final outcome payloads
- Phase 12 production case pack and revalidation

### Out of scope

- replacing deterministic gating with AI-first retrieval
- broad planner redesign
- solving all image-bearing retrieval gaps from Phase 11

## Success criteria

- A run like `run-6ae4a961c0` ends with a visible no-answer explanation instead of only `NO_ELIGIBLE_RECORDS`.
- A weak plan tail stops earlier once the system has enough evidence that no answer can be produced.
- Existing `ANSWER_READY` runs still complete normally with no regression.
