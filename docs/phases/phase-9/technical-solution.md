# Technical Solution - Phase 9
## Production-Safe Answer Delivery

**Status:** Proposed implementation architecture  
**Updated:** 2026-03-31

---

## 1. Technical Objective

Implement a production workflow that:

- prevents browser-backed run contention
- finishes the answer pipeline after labels are ready
- routes search posture by observed yield
- reformulates using structured judge reasons
- validates OCR / vision on real production-like evidence

---

## 2. Phase 9 Architecture

```text
Run request
  |
  v
RunAdmissionController
  |
  +--> reject / queue when browser slot busy
  |
  v
BrowserProfileLease
  |
  v
RunnerService
  |
  +--> Phase 8 validity-spec judging
  +--> batch-health + reason-code audit
  +--> yield-aware route prioritization
  +--> reason-aware reformulation
  |
  v
Accepted evidence
  |
  v
LabelJobService
  |
  v
RunCloseoutOrchestrator
  |
  +--> Theme synthesis
  +--> Insight response packaging
  +--> terminal answer-ready state
  |
  v
Production report / UI state
```

---

## 3. Main Design Decisions

### D-90 - Browser execution must be serialized by lease

The first production-safe fix should not try to clone full browser profiles per run.

Instead:

- protect one persistent browser profile with a lease
- allow at most one browser-backed run to own that lease
- expose `queued`, `blocked`, or equivalent operator-visible state

### D-91 - Run terminal state must separate infra failure from product failure

Examples:

- `INFRA_BROWSER_BOOT_FAILURE`
- `INFRA_BROWSER_SLOT_BUSY`
- `NO_ELIGIBLE_RECORDS`
- `ANSWER_READY`

This prevents production analysis from mixing operational failure with logic quality.

### D-92 - Label completion is not the final step

When a run has accepted evidence and labeling finishes, the system should automatically continue into:

- theme generation
- insight packaging

This should run under a closeout orchestrator or equivalent retryable job.

### D-93 - Routing should be posture-aware, not only step-order-aware

The plan generator can still create the raw steps.
But before execution, the runtime should re-rank or reprioritize search postures using:

- `validity_spec.target_signal_types`
- known high-yield posture classes
- prior production yield where available

### D-94 - Reformulation must use reason-code clusters

Reformulation should not depend only on `uncertain_ratio`.

It should inspect dominant reject reasons such as:

- `no_target_mention`
- `wrong_product_type`
- `pure_promotional_content`
- `no_interest_rate_discussion`

and derive the next posture from those clusters.

### D-95 - Vision validation needs a dedicated harness

OCR / vision should be measured on a curated set of image-bearing production-like cases, not just left as dormant code.

---

## 4. Recommended Runtime Flow

### Step 1 - Admit or defer the run

When a run starts:

- check whether browser-backed execution is already leased
- if yes, either queue the run or reject with explicit busy reason
- if no, acquire the lease and start

### Step 2 - Execute Phase 8 judging safely

Keep all current Phase 8 validity judgment, batch health, and selective expansion logic.

### Step 3 - Re-rank search posture

Before executing later search paths:

- score planned postures by expected yield
- move trust/fraud/complaint posture earlier when the topic and prior results justify it

### Step 4 - Reformulate weak paths using reason clusters

When a batch is weak:

- cluster dominant reject reasons
- map cluster -> next posture
- persist why reformulation happened

### Step 5 - Continue automatically after labeling

If eligible records exist:

- auto-start label job
- on label completion, auto-run theme synthesis
- package the answer-level outcome

### Step 6 - Release execution resources cleanly

On success, failure, or cancellation:

- release browser lease
- persist terminal reason
- emit answer-delivery status

---

## 5. Integration With Existing Repo

### Existing places likely affected

- [browser_agent.py](/Users/nguyenquocthong/project/social-listening-v3/backend/app/infra/browser_agent.py) for profile safety
- [runner.py](/Users/nguyenquocthong/project/social-listening-v3/backend/app/services/runner.py) for run admission, route ordering, reformulation, and terminal states
- [label_job_service.py](/Users/nguyenquocthong/project/social-listening-v3/backend/app/services/label_job_service.py) for closeout trigger
- [insight.py](/Users/nguyenquocthong/project/social-listening-v3/backend/app/services/insight.py) for answer synthesis continuation
- planner / run schemas / APIs for new statuses and observability

### Recommended migration path

1. add browser lease and run admission controller
2. add explicit failure taxonomy and queued/busy states
3. add answer closeout orchestration after labeling
4. add posture re-ranking ahead of weak paths
5. add reason-code reformulation mapper
6. add vision validation harness and metrics

---

## 6. Proposed Data Shape Additions

Phase 9 should add or persist conceptually:

- `browser_slot_status`
- `lease_owner_run_id`
- `run_failure_class`
- `answer_status`
- `answer_generated_at`
- `route_posture`
- `route_priority_score`
- `reformulation_reason_cluster`
- `reformulated_from_query`
- `vision_validation_case_id`

---

## 7. Key Risks and Mitigations

- Risk: queued runs create operator confusion  
  Mitigation: expose clear run admission state and reason

- Risk: auto-closeout causes duplicate theme jobs  
  Mitigation: idempotent closeout job keyed by run

- Risk: route re-ranking overrides planner too aggressively  
  Mitigation: keep re-ranker narrow and auditable

- Risk: reason-code reformulation becomes brittle  
  Mitigation: start with a small stable mapping table and expand from evidence

- Risk: vision validation burns cost without proof  
  Mitigation: run only against selected validation scenarios first

---

## 8. Recommendation

Implement Phase 9 in this order:

1. `P0`: production safety and run admission
2. `P0`: answer delivery closeout
3. `P1`: route posture prioritization
4. `P1`: reason-aware reformulation
5. `P2`: vision validation harness

That order fixes reliability first, then usefulness, then optimization.
