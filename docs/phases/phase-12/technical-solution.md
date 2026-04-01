# Technical Solution - Phase 12

## Solution summary

Phase 12 adds two control layers on top of the existing run lifecycle:

1. `no-answer closeout layer`
2. `goal-aware exhaustion layer`

The first turns `NO_ELIGIBLE_RECORDS` into a persisted final outcome payload. The second ends weak plans earlier when repeated completed steps already prove the answer cannot be produced under the current search path.

## Track A - No-answer closeout

### A1. Outcome payload on the run

Persist a structured terminal payload on `plan_runs`, for example:

- `outcome_type`
- `title`
- `summary`
- `dominant_reject_reasons`
- `attempted_queries`
- `evidence_stats`
- `recommended_next_actions`

This payload must exist for:

- `NO_ELIGIBLE_RECORDS`
- `NO_ANSWER_CONTENT`
- optionally `ANSWER_READY` later for contract symmetry

### A2. Deterministic no-answer synthesizer

Build a service that inspects:

- step checkpoints
- `query_attempts`
- `batch_summaries`
- reject reason codes on `crawled_posts`
- top near-miss records

and produces a deterministic final outcome payload without depending on a second LLM pass.

### A3. Closeout hook

When `LabelJobService.ensure_job_for_run()` detects zero eligible records, it should call the no-answer closeout service and persist the outcome before returning.

## Track B - Goal-aware exhaustion

### B1. Exhaustion policy

Add a run-level stop rule that checks:

- repeated completed search steps with `accepted_count = 0`
- dominant `generic_weak` or equivalent reason clusters
- cumulative step budget spent without any accepted evidence

When the threshold is crossed, remaining weak tail steps should be skipped and the run should go directly to no-answer closeout.

### B2. Preserve what already works

Do not change:

- answer-ready closeout
- strict-mode gating semantics
- timeout salvage behavior from Phase 11

## Track C - API/UI surface

### C1. API

Expose the terminal outcome payload on the run response.

### C2. Monitor UI

Render a dedicated “final outcome” card for:

- no-answer explanation
- dominant reject reasons
- attempted queries
- suggested next actions

## Exit criteria

- A run like `run-6ae4a961c0` surfaces a final no-answer explanation in API/UI.
- Goal-aware exhaustion prevents obviously weak tails from running to the end.
- A known answer-ready case still reaches `ANSWER_READY`.
