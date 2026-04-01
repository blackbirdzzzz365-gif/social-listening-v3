# Checkpoint Verdict - phase-11

## Context
- Current phase under audit: `phase-11`
- Run id: `run-6ae4a961c0`
- Topic: `vay tiền mặt ở shin han`
- Report packet: [run-6ae4a961c0](/Users/nguyenquocthong/project/social-listening-v3-worktrees/codex-phase-12/reports/production/run-6ae4a961c0)

## Expectation vs Actual
- Expected:
  - a text-led finance topic should either reach `ANSWER_READY` or at least leave the user with a clear terminal outcome
  - weak retrieval paths should stop once the plan is obviously exhausted
- Actual:
  - the run reached terminal state cleanly as `DONE / NO_ELIGIBLE_RECORDS`
  - it persisted `198` records, all `REJECTED`
  - no label job or theme synthesis started
  - the operator can see the terminal status in monitor, but the user still does not receive a final explanatory outcome beyond the badge

## What is actually broken
- The run did finish technically.
- The missing result is product-level:
  - `NO_ELIGIBLE_RECORDS` is not converted into a user-facing final outcome
  - the system does not explain why the answer is missing, what queries were tried, or what should happen next
- The plan also kept spending budget after repeated `generic_weak` zero-accept batches:
  - `SEARCH_IN_GROUP` and later reformulations consumed time without any accepted evidence

## User problem solved or not
- Verdict: `Not solved`
- Why:
  - from a backend/status perspective the run is complete
  - from a user perspective the product still feels unfinished because there is no final no-answer explanation

## What should remain unchanged
- Keep deterministic gating and `NO_ELIGIBLE_RECORDS` as a valid terminal state
- Keep strict-mode behavior that skips labeling/theme work when there are zero eligible records
- Keep reformulation signals and batch summaries; they are needed to explain no-answer outcomes

## Route Decision
- `new-phase`
- Why:
  - the required fix changes the product contract from “only answer when accepted evidence exists” to “always return a final outcome, including no-answer”
  - it also introduces a goal-aware stopping policy, not just a UI label tweak

## Recommended next phase
- `Phase 12 - No-Answer Closeout And Goal-Aware Exhaustion`
