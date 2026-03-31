# User Stories - Phase 9
## Production-Safe Answer Delivery

**Status:** Draft implementation stories  
**Updated:** 2026-03-31

---

## US-90 - Prevent overlapping browser-backed runs

As an operator, I want the system to block or queue overlapping browser-backed runs safely, so that one run cannot corrupt another through a shared browser profile.

Acceptance criteria:

- only one run can hold the browser execution lease at a time
- a second run receives a clear queued or busy state
- browser lease is released on success, failure, and cancellation

---

## US-91 - Distinguish infra failure from logic failure

As an operator, I want run statuses to show whether a failure came from infrastructure or product logic, so that production analysis is accurate.

Acceptance criteria:

- browser boot failure has its own failure class
- queued/busy admission is not reported as generic step failure
- run reports expose a machine-readable failure class or equivalent reason

---

## US-92 - Continue automatically from labels to answer

As a user, I want the system to keep going after labels are ready, so that a successful run ends with answer-ready output instead of stopping at intermediate artifacts.

Acceptance criteria:

- if accepted records exist, label completion triggers theme synthesis automatically
- the orchestration is idempotent
- the run can reach an `answer-ready` outcome or equivalent

---

## US-93 - Prioritize high-yield search posture earlier

As the system, I want to bring stronger query postures earlier in the run, so that accepted evidence appears sooner and weak steps do not dominate budget.

Acceptance criteria:

- route posture can be ranked before execution
- trust/fraud/complaint posture can outrank generic brand posture when evidence suggests it should
- the route decision is persisted or auditable

---

## US-94 - Reformulate weak paths using rejection reasons

As the system, I want to reformulate queries based on dominant reject reasons, so that the next path is intentionally different instead of only being another weak variant.

Acceptance criteria:

- weak batches can produce a reason cluster
- reason cluster maps to the next posture or query rewrite
- reformulated attempts are marked and auditable

---

## US-95 - Validate OCR / vision on real image-bearing evidence

As the team, I want a repeatable validation flow for image-bearing records, so that OCR and vision support is proven with real use cases before wider rollout.

Acceptance criteria:

- there is a defined validation scenario set for images
- runs can record whether image understanding was triggered and whether it changed the final decision
- the team can report at least one validated production-like use case
