# Detect -> Brainstorm -> Proposed Direction
## Phase 9 Architecture Reasoning Trail

**Purpose:** keep an explicit reasoning record from observed production problems to the proposed Phase 9 direction  
**Updated:** 2026-03-31

---

## 1. Detect - What Production Behavior Exposed

Production after Phase 8 showed two different classes of outcome:

- one run failed before useful execution because browser startup was unsafe under overlapping conditions
- another run succeeded semantically, but still stopped before answer-level synthesis

Concrete evidence:

- `run-e4ed95bc41` failed at browser boot with `STEP_ERROR`
- `run-2b87665c15` produced `10 ACCEPTED` records and finished labels
- yet `theme_results = 0`

This established a clear conclusion:

> the next bottleneck is no longer only content validity, but production-safe execution and answer completion

---

## 2. Brainstorm - What Options Were Considered

### Option A - Keep patching operational symptoms only

Pros:

- fast tactical fixes

Cons:

- does not solve answer-delivery gap
- likely creates more scattered conditions in runner code

### Option B - Rebuild orchestration broadly

Pros:

- could produce a cleaner long-term runtime

Cons:

- too large for the immediate product need
- risky while production behavior is still being validated

### Option C - Targeted production-safe answer loop

Pros:

- directly addresses the confirmed production gaps
- preserves Phase 8 validity logic
- creates a bridge from evidence to answer
- keeps routing improvements tied to real yield

Cons:

- requires careful state design around leases and closeout jobs
- needs production verification to prove each piece

Decision:

- choose Option C

---

## 3. Proposed Direction

The proposed Phase 9 direction is:

1. protect browser-backed execution with admission control
2. distinguish infra failure from logic failure
3. auto-close the run from labels to themes/insights
4. re-rank search posture by expected yield
5. reformulate using reject-reason clusters
6. validate OCR / vision on a dedicated set of real cases

This changes the key product question from:

- "did the run find accepted records?"

to:

- "did the run safely reach a usable answer?"

---

## 4. Why This Direction Is Better

It improves on Phase 8 because:

- it makes production behavior trustworthy
- it turns accepted evidence into answer delivery
- it optimizes for earlier yield rather than only eventual yield
- it treats vision as a measured capability, not a checkbox

---

## 5. Current Development Stance

For now:

- keep the app runtime as the main orchestrator
- favor a narrow, reliable browser lease over a more ambitious multi-profile design
- keep routing logic explicit and auditable

Later:

- queueing, multi-slot execution, or distributed browser execution can be revisited
- answer packaging can evolve into richer stakeholder-facing output

---

## 6. Scope Boundary For Phase 9

Phase 9 should answer:

- how to run browser-backed production safely
- how to move from labels to answer automatically
- how to route and reformulate based on real evidence
- how to validate vision with real use cases

Phase 9 should not yet answer:

- full distributed browser scheduling
- full production analytics warehouse design
- universal multimodal default execution
