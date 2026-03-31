# Detect -> Brainstorm -> Proposed Direction
## Phase 8 Architecture Reasoning Trail

**Purpose:** keep an explicit reasoning record from observed production problems to the proposed Phase 8 direction  
**Updated:** 2026-03-31

---

## 1. Detect - What Production Behavior Exposed

Production analysis after Phase 7 showed:

- many records were successfully rejected before AI
- weak retrieval paths were stopped early
- but the accepted set still contained promotional records
- and transactional comments could still become "end-user themes"

Concrete example from production:

- accepted parent posts later labeled `brand_official` or `seller_affiliate`
- accepted comments such as `Xin giá` and `Ib` still surfaced in end-user-only themes

This established a clear conclusion:

> the remaining bottleneck is not just retrieval volume, but the definition of what valid content means

---

## 2. Brainstorm - What Options Were Considered

### Option A - Keep extending lexical rules

Pros:

- easy to reason about
- cheap at runtime

Cons:

- too many edge cases
- validity depends on research intent, not only on terms
- cannot handle visual context well
- brittle across new product domains

### Option B - Replace everything with a generic LLM call

Pros:

- more semantic than lexical rules
- can adapt to many cases

Cons:

- expensive if called blindly
- hard to audit if prompt shape drifts
- easy to let product logic collapse into prompt-only behavior

### Option C - Hybrid architecture

Pros:

- keeps cheap hard filters
- moves semantic validity to model judgment
- allows image fallback only when necessary
- produces a reusable contract and cleaner observability

Cons:

- more design work up front
- requires explicit spec and output schema discipline

Decision:

- choose Option C

---

## 3. Proposed Direction

The proposed Phase 8 direction is:

1. generate a `validity_spec` from the full research context
2. judge each content item against that spec
3. keep hard filters for obvious garbage
4. use OCR / vision fallback only when needed
5. keep batch routing, but make it confidence-aware

This changes the key question from:

- "does this post contain the right words?"

to:

- "does this post satisfy the current research definition of valid content?"

---

## 4. Why This Direction Is Better

It improves on Phase 7 because:

- it can represent research intent explicitly
- it can separate end-user insight from buyer-intent noise
- it allows different validity logic for different runs
- it creates a future-compatible interface with the external `llm-model` project

---

## 5. Current Development Stance

For now:

- build the architecture in `social-listening-v3`
- use external API models during active development
- optimize for speed and observability first

Later:

- migrate model-serving concerns toward the separate `llm-model` project
- optionally add self-host or dedicated inference infrastructure

---

## 6. Scope Boundary For Phase 8

Phase 8 should answer:

- how to represent validity
- how to judge posts and comments
- how to integrate model judgment into the current workflow
- how to keep the system auditable

Phase 8 should not yet answer:

- final self-host model stack
- final RAG/fine-tune platform
- final reusable service deployment topology

Those are follow-on concerns.

