# Phase 9 - Production-Safe Answer Delivery
## AI Facebook Social Listening & Engagement v3

**Status:** Scope locked on branch `codex/phase-9`  
**Depends on:** Phase 8 - Research-Aware Model Gating In Production Workflow  
**Updated:** 2026-03-31

---

## Why Phase 9 Exists

Production on **March 31, 2026** exposed two truths at the same time:

- Phase 8 logic can now find valid accepted evidence in production
- the product still does not reliably convert that evidence into a final answer

Concrete production evidence:

- `run-e4ed95bc41` failed at browser startup with `STEP_ERROR` and `0 records`
- `run-2b87665c15` finished `DONE/COMPLETED` with `135 records`
- inside `run-2b87665c15`, the system produced `10 ACCEPTED` records and finished labeling `10/10`
- but `theme_results = 0`, so the product still stopped before a real answer was delivered

This means Phase 8 improved content judgment, but Phase 9 must make the production workflow:

1. safe to run reliably
2. able to continue from evidence to answer
3. better at spending search budget on paths that actually work

Priority lock for Phase 9:

- `P0`: browser-backed production safety and answer delivery closeout
- `P1`: yield-aware routing and reason-aware reformulation
- `P2`: vision validation on real image-bearing evidence

---

## Phase 9 Goal

Turn a production run from:

- "maybe fail at browser startup"
- or "find accepted evidence but stop at labels"

into:

- a safe, serializable browser-backed execution
- an evidence-to-answer workflow that closes automatically
- a plan that prioritizes higher-yield postures sooner

Phase 9 is not a new retrieval engine.
It is the production execution and answer-delivery layer that makes Phase 8 useful in the real product.

---

## Product Thesis

The user does not care that the system successfully labeled ten valid records.

The user cares that:

- the run actually completes
- the system reaches a usable answer
- the system does not waste time on obviously weak search paths

So Phase 9 must optimize for:

- safe execution
- answer completion
- earlier yield
- clearer run outcomes

---

## Locked Direction

### 1. Production safety is a product requirement

Concurrent browser-backed runs must not compete for the same persistent browser profile.

### 2. A run is not complete when labeling is done

If accepted evidence exists, the system must continue into theme and insight synthesis automatically.

### 3. Plan routing must be yield-aware

The runtime should bring high-yield search postures earlier when production evidence proves they work better.

### 4. Reformulation must become reason-aware

Weak batches should not only stop.
They should explain how the next query posture should change.

### 5. Vision support must be validated, not just implemented

OCR and image-understanding should be proven on real runs before being treated as a solved capability.

---

## What Phase 9 Will Deliver

### P0

1. browser run admission control and profile safety
2. clearer infra-vs-logic failure taxonomy
3. automatic answer delivery after successful labeling

### P1

4. yield-aware query posture routing
5. reason-code-driven reformulation

### P2

6. a real validation harness for OCR / vision fallback

---

## What Phase 9 Will Not Do

- replace the Phase 8 validity-spec model
- redesign the whole planner from scratch
- make OCR/vision always-on for every record
- build self-host browser orchestration infrastructure outside the app runtime

---

## Documents

- [BRD / BA Problem Brief](./ba-problem-brief.md)
- [Technical Solution](./technical-solution.md)
- [User Stories](./user-stories.md)
- [Detect -> Brainstorm -> Proposed Direction](./detect-brainstorm-solution.md)
- [Vision Validation Scenarios](./vision-validation-scenarios.md)
- [Checkpoints README](./checkpoints/README.md)

Document roles:

- `ba-problem-brief.md`: source of truth for product problem, production evidence, scope, and constraints
- `technical-solution.md`: source of truth for Phase 9 architecture and runtime flow
- `user-stories.md`: source of truth for acceptance-oriented behavior
- `detect-brainstorm-solution.md`: source of truth for the reasoning path from production failure modes to the chosen direction
