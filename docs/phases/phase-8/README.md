# Phase 8 - Research-Aware Model Gating In Production Workflow
## AI Facebook Social Listening & Engagement v3

**Status:** Scope lock and architecture preparation  
**Depends on:** Phase 7 - Retrieval Quality Gating Before AI Cost  
**Updated:** 2026-03-31

---

## Why Phase 8 Exists

Phase 7 proved that pre-AI gating can reduce crawl and labeling waste.

It also exposed the next bottleneck:

- deterministic lexical gating is still too weak for defining what a truly valid post is
- accepted sets can still contain promotional or commercial records
- parent-context comment scoring can still let low-value transactional comments survive
- image-bearing posts are still under-understood

Phase 8 exists to replace the core validity decision with a stronger operating model:

- compile research intent into a reusable `validity_spec`
- judge each post or comment against that spec
- use model-driven structured decisions instead of relying only on lexical rules
- keep hard filters and batch gating where they still add value
- continue using API models during the current development phase for speed

---

## Locked Direction

### 1. Validity becomes research-aware and spec-driven

The system should no longer rely primarily on keyword heuristics to define a valid record.

Each run must first compile:

- user research need
- clarification history
- keyword/context package
- plan-time intent

into one `validity_spec`.

### 2. Runtime gating becomes hybrid, not purely rule-based

Each content item should pass through:

- hard filter layer
- text judge layer
- optional OCR / vision fallback
- structured decision output

### 3. Batch routing still matters

Phase 8 does not discard batch-level path control.

It still needs:

- continue / reformulate / stop decisions per query path
- confidence-aware routing
- explicit handling of weak or uncertain batches

### 4. Development-phase implementation will use API models

For current development speed:

- Phase 8 will integrate with external LLM model APIs provided interactively by the operator
- self-host and dedicated model-serving infrastructure remain future optimization work
- the reusable model-layer concepts are documented separately in the external `llm-model` project

---

## What Phase 8 Should Deliver

Phase 8 should deliver the first implementation of:

1. `validity_spec` generation from research context
2. structured runtime judge contract per content item
3. hybrid post gating using model API calls
4. image/OCR fallback policy for image-bearing posts
5. batch-health policy updated for model-driven judgments
6. persistence and observability for judge decisions

---

## Documents

- [BRD / BA Problem Brief](./ba-problem-brief.md)
- [Technical Solution](./technical-solution.md)
- [User Stories](./user-stories.md)
- [Detect -> Brainstorm -> Proposed Direction](./detect-brainstorm-solution.md)
- [Checkpoints README](./checkpoints/README.md)

Document roles:

- `ba-problem-brief.md`: source of truth for product problem, scope, and constraints
- `technical-solution.md`: source of truth for Phase 8 architecture and runtime flow
- `user-stories.md`: source of truth for acceptance-oriented behavior
- `detect-brainstorm-solution.md`: source of truth for the reasoning path from observed problem to proposed design

