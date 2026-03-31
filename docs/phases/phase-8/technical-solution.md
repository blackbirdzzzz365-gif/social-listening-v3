# Technical Solution - Phase 8
## Hybrid Research-Aware Model Gating

**Status:** Proposed implementation architecture  
**Updated:** 2026-03-31

---

## 1. Technical Objective

Implement a production-ready validity judgment flow that:

- compiles research context into a stable `validity_spec`
- judges posts and comments against that spec
- combines hard filters with model-driven scoring
- supports image/OCR fallback when text is insufficient
- preserves batch-level routing and observability

---

## 2. Phase 8 Architecture

```text
Research context
  - topic
  - clarification history
  - keyword package
  - plan intent
        |
        v
ValiditySpecBuilder
        |
        v
ValiditySpec
        |
        v
For each candidate item:
  hard filter
        |
        +--> obvious reject
        |
        v
  text judge via model API
        |
        +--> accepted / rejected / uncertain
        |
        +--> uncertain + image present -> OCR / vision fallback
        |
        v
  decision aggregator
        |
        v
  JudgeResult persistence
        |
        v
BatchHealthEvaluator V2
        |
        +--> continue path
        +--> reformulate path
        +--> stop path
        |
        v
Selective expansion
  - accepted parents
  - comment policy aware
        |
        v
Labeling + theme analysis
```

---

## 3. Main Design Decisions

### D-80 - `validity_spec` is the new source of truth

Instead of relying on:

- anchor terms
- related terms
- negative terms

as the primary definition of validity, Phase 8 will first generate a structured spec that includes:

- research objective
- target signal types
- target and non-target author types
- must-have signals
- hard reject signals
- comment policy
- batch policy
- examples of valid and invalid content

### D-81 - Runtime gating is hybrid

Phase 8 keeps a small deterministic layer for:

- duplicates
- empty content
- extraction failure
- severe UI noise

Then shifts the main semantic decision to a model-driven judge.

### D-82 - `judge_result` is structured

Each judged item should produce a stable payload containing at least:

- `decision`
- `relevance_score`
- `confidence_score`
- `reason_codes`
- `short_rationale`
- `used_image_understanding`

### D-83 - Vision is conditional

Image handling should not run for every record.

It should trigger only when:

- the record has images
- text is weak or insufficient
- the text judge returns `UNCERTAIN`
- the research spec explicitly cares about visual evidence

### D-84 - Batch health becomes confidence-aware

Batch routing should use:

- accept ratio
- high-confidence accept ratio
- uncertain ratio
- confidence trend

not only lexical accept counts.

---

## 4. Recommended Runtime Flow

### Step 1 - Compile `validity_spec`

Input:

- topic
- question-and-answer context from research setup
- keyword package from planning
- operator refinement from plan step

Output:

- one spec object versioned for the run

Suggested implementation:

- use a strong API model
- generate JSON only
- persist spec alongside the run or product context

### Step 2 - Hard filter candidate content

Reject without model call when:

- content is empty
- content is duplicate
- extraction is obviously broken
- content is unusable UI noise

This keeps model cost focused where semantics matter.

### Step 3 - Text judge

Input:

- `validity_spec`
- candidate text
- source metadata
- record type
- optional parent summary for comments

Output:

- structured `judge_result`

### Step 4 - Optional OCR / vision fallback

Trigger when:

- image exists and text is weak
- text judge returns `UNCERTAIN`
- or the spec marks visual evidence as relevant

Output:

- image summary
- OCR text
- revised `judge_result`

### Step 5 - Persist result

Store at least:

- decision
- relevance score
- confidence score
- reason codes
- policy/spec version
- cache key

### Step 6 - Evaluate batch health

Recommended outputs:

- `continue`
- `reformulate`
- `stop`

### Step 7 - Selective expansion

Only valid parent posts should unlock:

- comment crawl
- deeper in-group search
- downstream expensive analysis

Comment policy must explicitly reject transactional-only comments for end-user insight runs.

---

## 5. Integration With Existing Repo

Phase 8 should integrate into the current repo with minimal disruption.

### Existing places likely affected

- planner phase where context and keyword package are built
- runner flow where candidates are processed
- persistence model for candidate judgment fields
- comment gating logic
- downstream selection logic before labeling and themes

### Recommended migration path

1. keep current deterministic engine as hard-filter and fallback
2. introduce `validity_spec` generation
3. introduce one API-backed judge adapter
4. persist judge result fields beside current pre-AI fields
5. move batch-health logic to use judge outputs
6. refine comment policy and image fallback

---

## 6. Proposed Data Shape Additions

Phase 8 should add or persist conceptually:

- `validity_spec_json`
- `judge_decision`
- `judge_relevance_score`
- `judge_confidence_score`
- `judge_reason_codes_json`
- `judge_model_name`
- `judge_policy_version`
- `used_image_understanding`

These may map onto existing fields first or be added incrementally.

---

## 7. Development-Phase Model Strategy

For Phase 8 development:

- use API models provided by the operator
- optimize for speed of iteration
- keep model adapter interface narrow and replaceable

This means the implementation should isolate:

- model prompt/build logic
- response parsing
- retry/failure policy
- output normalization

so later migration to self-host or the separate `llm-model` project is straightforward.

