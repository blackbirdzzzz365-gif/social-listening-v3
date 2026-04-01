# Phase 10 BRD / BA Problem Brief

## Problem Statement

The product can now retrieve and judge evidence better than before, but production still breaks operator trust because execution state is not reliable enough.

The most damaging gap is not "we cannot score content."
It is "we cannot trust what the runtime is doing while a long browser step is active."

## Production Evidence

### Evidence A - Cancel did not actually stop work

From the Phase 9 smoke packet:

- `run-3f07eac44d` was marked `CANCELLED` at `2026-03-31T15:28:09Z`
- `step-1 SEARCH_POSTS` continued until `2026-03-31T15:28:49Z`
- records were still persisted after the run had already ended

Business meaning:

- operator trust is broken
- audit truth is corrupted
- downstream analysis of the run becomes ambiguous

### Evidence B - Active step looked dead for minutes

- `run-5582f7cbae` stayed on `step-1 SEARCH_POSTS` for more than 6 minutes
- there was no meaningful heartbeat explaining whether the system was searching, scrolling, or stuck

Business meaning:

- operators cannot distinguish "slow but progressing" from "hung"
- humans intervene too early or too late

### Evidence C - Monitoring artifacts were not fully aligned

- the production monitor script still queried stale schema fields like `label_jobs.completed_at`
- the live run view had very weak step-level progress detail

Business meaning:

- the production loop itself becomes noisy
- diagnosis effort is wasted on tooling gaps instead of product gaps

## Users Affected

### Primary user - Operator / builder

Needs to:

- stop a run and trust it actually halts
- know whether a long browser step is alive, slow, or stuck
- read a production artifact set that matches the real schema

### Secondary user - End user of the product

Indirectly affected because:

- if runs are cancelled or timed out incorrectly, the product may never reach answer closeout
- production evidence quality cannot be judged fairly if the execution layer lies

## Jobs To Be Done

1. When I stop a production run, I need it to converge to a real terminal halt so I can trust the audit trail.
2. When a search step takes time, I need live heartbeat and progress so I know whether to wait or intervene.
3. When a step is truly stuck, I need a specific timeout class instead of a generic failure blob.
4. When I review a shipped phase, I need monitoring artifacts that match current production schema and signals.
5. After shipping this phase, I need to re-run one answer-closeout case and one image-bearing case to verify the runtime is now trustworthy enough for product judgment.

## Scope

### In scope

- cancel-safe step execution
- `CANCELLING` transitional run state
- heartbeat/progress payload in step checkpoints
- live sync of `plan_runs.total_records`
- timeout classification for long browser-backed actions
- monitor script alignment with production schema
- Phase 10 production revalidation pack

### Out of scope

- planner redesign
- new retrieval families beyond what is needed for revalidation
- new labeling taxonomy
- broad OCR / vision expansion beyond validation

## Success Metrics

### P0 runtime control

- `cancel_to_actual_halt <= 15s`
- `records_persisted_after_cancel = 0`
- no step remains `RUNNING` after the run has reached `CANCELLED`

### P0 observability

- every long browser-backed step has `heartbeat_at` updates while active
- `plan_runs.total_records` changes while records are persisted, not only after the full step ends

### P1 failure clarity

- truly stuck browser work ends with `failure_class = STEP_STUCK_TIMEOUT`
- production artifacts distinguish cancel, timeout, infra boot failure, and generic step failure

### P1 production revalidation

- at least one trusted case reaches answer closeout terminal state
- one image-bearing case either exercises image understanding or produces a clear documented reason why none was found

## Constraints

- must stay within the current FastAPI + SQLite + browser-agent runtime
- must not regress the Phase 9 admission-control behavior
- must remain deployable through the current GitHub -> GHCR -> production workflow
