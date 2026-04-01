# Technical Solution - Phase 11

## Solution summary

Phase 11 adds two new control layers:

1. `planner resilience layer`
2. `image-bearing retrieval salvage layer`

The first protects session analysis and plan creation from transient provider instability. The second ensures search-step timeout no longer erases collected evidence from the audit trail.

## Solution track A - Planner resilience

### A1. Planner retry and fallback wrapper

All planner-facing AI calls must flow through a wrapper that:

- records per-attempt metadata
- retries transient provider failures with bounded backoff
- distinguishes retryable overload from non-retryable bad input
- returns a planner-classified failure when recovery does not succeed

### A2. Planner metadata persistence

Persist planner metadata on:

- `product_contexts` for analysis / clarification phases
- `plans` for plan generation and refinement

Metadata should include:

- planner stage
- attempt count
- provider used
- fallback used
- failure reason
- attempt history snapshot

### A3. API taxonomy

Planner endpoints must stop mapping provider failures to generic `400`.

Expected behavior:

- `400/404` only for domain validation and missing resources
- `503` for planner/provider unavailability
- response detail remains string-safe for the current frontend

## Solution track B - Image-bearing evidence acquisition

### B1. Image-first retrieval posture

Extend retrieval planning with explicit image-bearing posture:

- before-after review
- screenshot proof
- visual packaging / texture / side-effect proof
- complaint-with-photo posture

This posture should influence:

- query family generation
- query ordering
- reformulation choices for image-led topics

### B2. Timeout salvage

Current behavior persists candidates only after the browser search action returns. Phase 11 adds a salvage boundary so long-running search steps can expose:

- collected count
- last visible raw candidates or audit snapshot
- persisted count
- lost-before-persist estimate

The goal is not full raw scraping persistence for every scroll. The goal is an auditable checkpoint when timeout happens.

### B3. Vision proof instrumentation

Audit artifacts must answer:

- how many image-bearing candidates were seen
- how many triggered OCR / image understanding
- how many accepted decisions depended on image understanding

## Architecture delta

Likely modules affected:

- `backend/app/services/planner.py`
- `backend/app/api/plans.py`
- `backend/app/schemas/plans.py`
- `backend/app/models/product_context.py`
- `backend/app/models/plan.py`
- `backend/app/services/runner.py`
- `backend/app/services/retrieval_quality.py`
- `backend/app/services/research_gating.py`
- `backend/app/schemas/runs.py`
- `frontend/src/pages/MonitorPage.tsx`
- `backend/alembic/versions/*`

## Exit criteria

- planner metadata visible in API and stored in DB
- planner overload failure classified cleanly
- image-bearing posture exists in retrieval profile / runtime ordering
- timeout salvage leaves inspectable artifacts for stuck search steps
- production case pack proves whether image fallback is actually used
