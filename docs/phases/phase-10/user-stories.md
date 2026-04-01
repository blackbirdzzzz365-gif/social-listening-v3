# Phase 10 User Stories

## Epic 1 - Cancel-safe execution

### Story 1.1

As an operator, when I stop a run, I want the run to enter a visible `CANCELLING` state first so I know the system is converging the active work instead of pretending it is already done.

Acceptance criteria:

- stop API returns a run payload with `status = CANCELLING`
- the stream emits `run_cancelling`
- the run later converges to terminal `CANCELLED`

### Story 1.2

As an operator, when a run is cancelled, I want no later records to be persisted after terminal cancellation so the audit trail stays trustworthy.

Acceptance criteria:

- active running step does not remain `RUNNING` after terminal cancellation
- pending steps are marked skipped after cancellation
- no new `crawled_posts` appear after `ended_at`

## Epic 2 - Runtime heartbeat

### Story 2.1

As an operator, I need every long browser-backed step to update heartbeat and progress while it is running so I can distinguish slow work from dead work.

Acceptance criteria:

- step checkpoint contains `heartbeat_at`
- step checkpoint contains a `progress` object while active
- monitor UI and production monitor script surface that progress

### Story 2.2

As an analyst, I want live `total_records` to reflect persisted rows during the run so the monitor does not lag behind reality.

Acceptance criteria:

- `plan_runs.total_records` changes while the step is still active
- step progress payload includes the live total record count

## Epic 3 - Clear stuck-step behavior

### Story 3.1

As an operator, when browser-backed work exceeds its allowed time budget, I want the run to fail with a timeout class that clearly says the step was stuck.

Acceptance criteria:

- timed-out browser actions fail with `failure_class = STEP_STUCK_TIMEOUT`
- the run artifact makes timeout distinct from browser boot failure and generic step error

## Epic 4 - Production revalidation

### Story 4.1

As a product reviewer, I want a small Phase 10 production case pack so I can verify answer closeout and image-bearing scenarios after shipping the control-layer fix.

Acceptance criteria:

- a Phase 10 case pack exists under `docs/production/case-packs/phase-10-core.json`
- at least one case targets answer closeout proof
- at least one case targets image-bearing validation
