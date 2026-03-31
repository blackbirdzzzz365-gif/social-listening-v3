# BRD / BA Problem Brief - Phase 9
## Production-Safe Answer Delivery

**Status:** Scope locked for implementation planning  
**Updated:** 2026-03-31

---

## 1. Executive Summary

Phase 8 proved that research-aware judging can reject most weak records and still find some accepted evidence in production.

But production also showed that the product still has two severe gaps:

- the run layer is not safe enough under concurrent browser-backed execution
- the workflow does not automatically continue from accepted evidence to final answer delivery

Phase 9 exists to fix those gaps first, then improve routing and reformulation based on real yield.

---

## 2. Production Evidence

Relevant production observations from **March 31, 2026**:

### Observation A - Browser-backed concurrency is unsafe

`run-e4ed95bc41` failed with:

- `FAILED`
- `completion_reason=STEP_ERROR`
- browser startup timeout on `launch_persistent_context`
- shared profile startup artifacts and session state contention symptoms

This indicates concurrent or overlapping use of the same persistent browser profile.

### Observation B - Evidence can now be found

`run-2b87665c15` succeeded with:

- `DONE`
- `COMPLETED`
- `135` persisted records
- `10 ACCEPTED`
- `125 REJECTED`

Accepted examples included:

- FE Credit trustworthiness concerns
- fee complaints
- fraud warnings
- customer experience narratives

### Observation C - Answer delivery still stops too early

For the successful run:

- label job completed `10/10`
- `theme_results = 0`

This means the system produced filtered evidence, but did not finish synthesizing the answer.

### Observation D - High-yield posture came late

Weak paths:

- early `SEARCH_POSTS` brand posture
- `SEARCH_IN_GROUP` fee posture in noisy groups

High-yield path:

- later trust/fraud posture such as `vay FE Credit bị lừa`

### Observation E - Reformulation and vision remain under-proven

- `used_reformulation` did not materially appear in the real run
- `judge_used_image_understanding = 0` for the successful run

---

## 3. Current Product Problem

### Problem A - The run layer can fail for the wrong reason

The user sees a failed run even when the core product logic may be correct, because shared browser resources are not protected.

### Problem B - The product still stops at "evidence found"

The workflow can label valid records but still fail to deliver themes or answer-level output.

### Problem C - The plan spends too much budget before reaching high-yield paths

The system can discover the right query posture, but too late in the plan.

### Problem D - Reformulation exists in contract more than in behavior

The current loop is mostly:

- continue
- stop

instead of:

- continue
- reformulate
- stop

### Problem E - Vision capability is not production-proven

The product claims conditional OCR/vision support, but production has not yet validated it on real evidence-bearing image flows.

---

## 4. Product Decision For Phase 9

Phase 9 will focus on **production-safe answer completion**.

The system must:

1. protect shared browser execution
2. continue automatically from accepted evidence to answer synthesis
3. route plans toward higher-yield postures earlier
4. reformulate based on rejection reasons, not only ratios
5. validate OCR/vision on real use cases

---

## 5. Goals

### Product goals

- fewer false failed runs caused by shared browser contention
- more runs that reach answer-ready state after finding accepted evidence
- faster time to first accepted record
- clearer route from weak batch to better next query posture
- real evidence that vision fallback adds value when relevant

### Operational goals

- one active browser-backed run per protected execution slot
- explicit run status for infra failure vs logic failure
- automatic downstream orchestration after label completion
- auditable routing and reformulation decisions

---

## 6. Phase 9 In-Scope

### P0

- run admission control for browser-backed execution
- browser profile lease or equivalent guard
- clearer failure taxonomy and run-state reporting
- closeout orchestration from labels to themes/insights

### P1

- yield-aware route prioritization
- reason-code-driven reformulation policy

### P2

- image/OCR validation harness and metrics

---

## 7. Phase 9 Out-Of-Scope

- multi-profile distributed browser farm
- full planner replacement
- universal multimodal judgment for every run
- final production analytics dashboard redesign

---

## 8. Key Constraints

- the current app runtime must remain the source of orchestration truth
- production changes must not weaken Phase 8 validity judgment
- the first safety fix should prefer simplicity and reliability over architectural elegance
- answer delivery must be idempotent and retryable
- routing changes must stay auditable and explainable

---

## 9. Success Criteria

Phase 9 should improve all of the following:

- `P0`: no overlapping browser-backed production runs can corrupt or block each other
- `P0`: runs with accepted evidence auto-progress to themes/insights
- `P1`: lower time-to-first-accepted for topics where trust/fraud posture is stronger
- `P1`: real production evidence of at least one reformulated path improving yield
- `P2`: at least one validated image-bearing use case for OCR / vision fallback
