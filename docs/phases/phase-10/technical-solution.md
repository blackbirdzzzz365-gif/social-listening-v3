# Phase 10 Technical Solution

## Design Intent

Phase 10 hardens the runtime boundary around browser-backed steps.

It does not replace the Phase 8/9 retrieval and answer pipeline.
It wraps that pipeline so operators can trust what the run is doing in real time.

## Runtime Changes

### 1. Transitional run state: `CANCELLING`

Current problem:

- the old flow jumped directly from `RUNNING` to `CANCELLED` during the API stop request
- actual browser work could still continue afterward

Phase 10 flow:

```text
RUNNING -> CANCELLING -> CANCELLED
```

Behavior:

- `POST /api/runs/{run_id}/stop` sets `stop_requested=true`
- run status becomes `CANCELLING`
- the active browser step is cancelled cooperatively
- only after the runner has converged the active step and pending steps does the run become `CANCELLED`

### 2. Timed browser action wrapper

Every browser-backed action is executed inside a runner wrapper that:

- starts the browser action as its own asyncio task
- emits step heartbeat updates every `step_heartbeat_interval_sec`
- cancels the task if the run enters stop-requested mode
- cancels the task and raises `StepActionTimeout` if elapsed time exceeds the action timeout

Covered actions:

- `SEARCH_GROUPS`
- `JOIN_GROUP`
- `CHECK_JOIN_STATUS`
- `SEARCH_POSTS`
- `SEARCH_IN_GROUP`
- `CRAWL_FEED`
- `CRAWL_COMMENTS`

### 3. Step heartbeat and progress contract

Each running step checkpoint must carry:

```json
{
  "phase": "running",
  "step_id": "step-1",
  "started_at": "...",
  "heartbeat_at": "...",
  "progress": {
    "activity": "search_posts",
    "elapsed_sec": 42.1,
    "query": "...",
    "collected_count": 8,
    "batch_index": 1
  }
}
```

Progress sources:

- runner wrapper heartbeat
- browser-agent callbacks at meaningful milestones
- candidate scoring loop updates while batches are being judged and persisted

### 4. Live record counter sync

Current problem:

- `plan_runs.total_records` only moved after the step completed

Phase 10 change:

- each progress update re-syncs `plan_runs.total_records` from `crawled_posts`
- step completion also re-syncs from actual persisted rows instead of incrementing a cached delta

### 5. Cancel-safe persistence

Phase 10 adds stop checks:

- before batch scoring starts
- during record scoring loops
- before batch persistence

This prevents the old failure mode where a stop request arrives but the runner still persists a later batch.

### 6. Failure taxonomy

New failure split:

- `INFRA_BROWSER_BOOT_FAILURE`
- `STEP_STUCK_TIMEOUT`
- `STEP_EXECUTION_ERROR`
- `POST_RUN_ERROR`

This keeps stuck browser work separate from generic step bugs.

### 7. Production audit tooling alignment

The monitor script is updated to:

- use `label_jobs.ended_at` instead of stale columns
- read heartbeat/progress payloads from step checkpoints
- compute `time_to_first_record` and `time_to_first_accepted`
- report `CANCELLING` distinctly from terminal `CANCELLED`

## Browser-Agent Progress Hooks

The browser agent now emits lightweight progress payloads during:

- navigation to search/feed/group pages
- applying recent filters
- scanning articles and comment expansions
- group inspection during `SEARCH_POSTS`

These payloads are not business signals.
They are operator-observability signals.

## Validation Plan

### Local validation

- compile backend/tests/scripts
- run targeted runner tests for cancel convergence and heartbeat
- run existing gating / closeout / admission tests
- build frontend
- run alembic upgrade to head

### Production validation

Use the Phase 10 core case pack:

1. one trusted finance or banking case to verify answer closeout can finish with the new control layer
2. one image-bearing skincare case to verify heartbeat, timeout, and image-path auditability

## Non-goals

- changing deterministic gating thresholds
- introducing a new planner policy
- claiming OCR / vision value without real production evidence
