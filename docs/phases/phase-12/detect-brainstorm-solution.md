# Detect / Brainstorm Solution - Phase 12

## What the Shinhan run really says

`run-6ae4a961c0` is not a runtime failure.

It says:

- the system searched widely
- the system gated correctly
- the system concluded there is no trustworthy answer under the current plan
- but the product never translated that conclusion into a final user-facing result

## Wrong fixes to avoid

- Lowering thresholds just to force weak accepts
- Running theme synthesis on rejected evidence
- Treating `NO_ELIGIBLE_RECORDS` as a backend-only concern

## Better direction

- keep strict gating
- explain zero-answer outcomes explicitly
- stop weak tails earlier once the plan is clearly exhausted
