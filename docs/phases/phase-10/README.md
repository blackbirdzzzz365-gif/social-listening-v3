# Phase 10 - Execution Control And Production Observability
## AI Facebook Social Listening & Engagement v3

**Status:** Active on branch `codex/phase-10`  
**Depends on:** Phase 9 - Production-Safe Answer Delivery  
**Updated:** 2026-04-01

## Why Phase 10 Exists

Phase 9 improved browser admission and answer closeout, but production on **March 31, 2026** still showed that the runtime contract was weak:

- `run-3f07eac44d` persisted records after the run had already been marked `CANCELLED`
- `run-5582f7cbae` stayed on `step-1 SEARCH_POSTS` for minutes with no usable heartbeat
- the operator could not tell whether the step was slow, stuck, or still making progress
- the monitoring script itself still lagged behind production schema details

This means the next phase is not more retrieval sophistication first.
The next phase is to make execution truth match operator truth.

## Phase 10 Goal

Turn a production run from:

- "stop requested but work still leaks afterward"
- "step looks dead for minutes"
- "timeout or cancel reason is unclear"

into:

- a run lifecycle where `stop -> cancelling -> cancelled` is real
- a browser-backed step that emits heartbeat and live progress while it is running
- a runtime that classifies stuck work explicitly instead of hiding it inside generic `STEP_ERROR`
- a production audit loop that can re-measure answer closeout and vision scenarios with trustworthy artifacts

## Locked Direction

1. **Cancellation is an execution boundary**
   - No new records may be persisted after the run has converged to `CANCELLED`.
2. **Heartbeat is required, not optional**
   - Every long browser-backed step must keep updating checkpoint progress while it runs.
3. **Slow and stuck are different states**
   - A long step must either show heartbeat or fail with a timeout class that operators can reason about.
4. **Run counters must reflect reality while the run is still active**
   - `plan_runs.total_records` should no longer lag until the whole step is over.
5. **Phase 10 is only complete after production revalidation**
   - We must re-run one trusted answer-closeout case and one image-bearing case after shipping the control layer.

## What Phase 10 Will Deliver

- `P0` cancel-safe step execution and terminal convergence
- `P0` step heartbeat plus live record counter synchronization
- `P1` stuck-step timeout classification and clearer run/step observability
- `P1` production audit tooling aligned with current schema and checkpoint signals
- `P1` production revalidation pack for answer closeout and vision scenarios

## What Phase 10 Will Not Do

- redesign the validity-spec or judge policy from Phase 8
- replace the planner with a new exploration engine
- claim OCR / vision is solved without production proof
- build distributed browser orchestration outside the current app runtime

## Documents

- [BRD / BA Problem Brief](./ba-problem-brief.md)
- [Technical Solution](./technical-solution.md)
- [User Stories](./user-stories.md)
- [Detect -> Brainstorm -> Proposed Direction](./detect-brainstorm-solution.md)
- [Vision Validation Scenarios](./vision-validation-scenarios.md)
- [Checkpoints README](./checkpoints/README.md)
- [Phase Manifest](./phase-manifest.md)

Document roles:

- `ba-problem-brief.md`: production evidence, user problem, scope, and success metrics
- `technical-solution.md`: source of truth for the Phase 10 runtime design
- `user-stories.md`: operator- and analyst-facing acceptance behavior
- `detect-brainstorm-solution.md`: why this phase focuses on execution control before deeper retrieval work
- `vision-validation-scenarios.md`: bounded production truth criteria for image-bearing evidence
