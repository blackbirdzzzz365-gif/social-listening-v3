# User Stories - Phase 8
## Research-Aware Model Gating

**Status:** Draft implementation stories  
**Updated:** 2026-03-31

---

## US-80 - Compile research context into a validity spec

As an operator, I want the system to compile the full research context into a structured definition of valid content, so that runtime judgment uses the real research intent instead of only keywords.

Acceptance criteria:

- the system generates one `validity_spec` per run or equivalent research context version
- the spec includes target and reject signals
- the spec is stored and traceable

---

## US-81 - Judge posts with structured output

As the system, I want to judge each candidate post against the current `validity_spec`, so that downstream workflow can continue only with records that are actually useful.

Acceptance criteria:

- each candidate post gets `ACCEPTED`, `REJECTED`, or `UNCERTAIN`
- each judgment includes score and confidence
- each judgment includes short reason codes

---

## US-82 - Judge comments with a comment-specific policy

As the system, I want comments to be judged with comment-aware logic, so that short transactional comments do not leak into end-user insight flows.

Acceptance criteria:

- comment judging can use parent context
- parent context alone cannot rescue obviously low-value transactional comments
- comments such as `xin giá`, `ib`, or similar can be rejected for end-user insight runs

---

## US-83 - Use image fallback only when needed

As the system, I want to use OCR or vision fallback only for uncertain or image-reliant records, so that multimodal judgment improves quality without exploding cost.

Acceptance criteria:

- image fallback does not run for every post
- uncertain text judgments with images can trigger OCR or vision processing
- the final decision records whether image understanding was used

---

## US-84 - Route weak batches away from dead paths

As the system, I want batch-level path control to use model-based signal quality, so that retrieval can reformulate or stop when a path is not producing enough valid content.

Acceptance criteria:

- batch decisions support `continue`, `reformulate`, and `stop`
- the decision can use confidence-aware metrics
- the decision is persisted or auditable per batch

---

## US-85 - Keep development fast with API models

As the operator, I want Phase 8 to work with externally supplied model APIs during development, so that the team can iterate on quality before building dedicated inference infrastructure.

Acceptance criteria:

- model integration is adapter-based
- prompt/response normalization is isolated
- later migration to self-host remains possible without redesigning the whole product

