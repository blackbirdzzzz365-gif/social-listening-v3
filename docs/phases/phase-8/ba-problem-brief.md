# BRD / BA Problem Brief - Phase 8
## Research-Aware Model Gating In Production Workflow

**Status:** Scope locked for implementation planning  
**Updated:** 2026-03-31

---

## 1. Executive Summary

The product can already:

- generate a research plan
- retrieve posts and comments
- persist crawled content
- label accepted records
- generate themes

Phase 7 improved cost control by rejecting many records before labeling.

However, production evidence showed that the core notion of "valid post" is still not modeled well enough by deterministic lexical rules.

Phase 8 exists to implement a stronger validity decision model:

- research-aware
- spec-driven
- multimodal-capable
- structured and auditable

---

## 2. Current Product Problem

The current system still suffers from these failure modes:

### Problem A - Lexical relevance is not the same as research value

A post can:

- match topic terms
- mention pain-point words
- avoid explicit negative terms

and still be:

- promotion
- seller content
- low-value buyer intent
- not useful for the real research objective

### Problem B - Comment gating can still leak low-value transactional content

Comments such as:

- `xin giá`
- `ib`
- short transactional replies

can survive if parent context is accepted.

### Problem C - Image content is underused

Some posts carry meaningful signal in:

- product images
- screenshots
- embedded text
- visual context

but current gating remains mostly text-driven.

### Problem D - Validity is context-specific, not global

What counts as valid depends on:

- research objective
- target audience
- signal type
- exclusions
- examples

The current deterministic gate is not rich enough to represent this well.

---

## 3. Product Decision For Phase 8

Phase 8 will treat validity as a compiled research-time artifact.

The system must:

1. gather full research context
2. compile that context into a structured `validity_spec`
3. judge each post or comment against that spec
4. return a structured decision used by later workflow steps

---

## 4. Goals

### Product goals

- increase precision of accepted records
- reduce promotional false positives
- reduce low-value transactional comments in insight flows
- make image-bearing records judgeable without brittle ad hoc logic

### Operational goals

- make validity decisions auditable
- support caching and reuse of prior judgments
- support model changes without breaking product contracts

---

## 5. Phase 8 In-Scope

- research-context compilation into `validity_spec`
- post and comment judging using external model APIs
- hybrid runtime gating
- OCR / image fallback policy
- batch-level routing updates
- persistence of judge result fields in the existing workflow

---

## 6. Phase 8 Out-Of-Scope

- self-host inference infrastructure
- dedicated model-serving platform
- full training and fine-tuning loop
- generalized reusable model service extraction into another repository

Those concerns are documented separately in the external `llm-model` project and can be integrated later.

---

## 7. Key Constraints

- current implementation speed is more important than self-host cost optimization
- development-phase model access will use APIs supplied interactively by the operator
- Phase 8 must remain compatible with the existing plan/run/crawl pipeline
- the system must preserve explainability and not become prompt-only spaghetti

---

## 8. Success Criteria

Phase 8 should improve all of the following compared with Phase 7 behavior:

- fewer accepted posts later labeled as `brand_official` or `seller_affiliate`
- fewer accepted comments that are only transactional
- better usefulness of `end_user_only` themes
- lower ratio of accepted records later excluded as low relevance
- clearer auditability of why one record passed and another failed

