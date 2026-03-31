# Phase 7 - Retrieval Quality Gating Before AI Cost
## AI Facebook Social Listening & Engagement v3

**Status:** Locked direction for Phase 8 implementation  
**Depends on:** Phase 6 - Responsive Mobile Web for All Web Surfaces  
**Updated:** 2026-03-31

---

## Why Phase 7 Exists

Phase 1 proved the crawl loop.  
Phase 2 proved labeling and theme analysis.  
Phase 6 improved the web UX.

The next bottleneck is upstream quality:

- retrieval can miss relevant posts when Facebook search is cold or over-personalized
- retrieval can also return noisy posts that should never reach comment crawl or AI
- extracted text can stay dirty enough that labeling and theme analysis become expensive cleanup work

Phase 7 exists to lock one clear operating model before Phase 8 implementation starts:

- retrieve from more than one query/source
- score fast with deterministic rules before deep crawl and before AI
- continue exploring a query only while its retrieved batches stay healthy
- only send accepted records, or an explicitly allowed uncertain band, to AI
- route every AI call through one central provider strategy: `chiasegpu` primary, Claude fallback

---

## Locked Direction

### 1. Retrieval is query-family based, not single-query based

One topic must produce a `retrieval_profile` with:

- anchor clusters
- related-term clusters
- negative patterns
- query families such as `brand`, `pain_point`, `question`, `comparison`, `complaint`
- optional seed groups and source hints

### 2. Query execution is batch-gated

For each query/source path:

- fetch roughly the top `20` posts
- persist them as candidates
- score each candidate with deterministic rules
- compute batch health
- continue the same query only while the batch stays healthy

This is the key Phase 7 V2 decision. The system should stop wasting crawl effort on a weak query path early, then move to another query family or source strategy.

### 3. Record gating happens before deep crawl and before AI

Every retrieved post or comment must become a candidate first, then receive one of:

- `ACCEPTED`
- `REJECTED`
- `UNCERTAIN`

Only accepted posts can trigger comment crawl by default. AI is never the first-pass filter.

### 4. AI provider strategy is part of the same cost-control story

After retrieval quality is gated, all remaining AI interactions must go through a central `AIClient`:

- `chiasegpu` is the default provider
- Claude is fallback only
- fallback is allowed only for provider/runtime failures, not deterministic payload or prompt bugs

This keeps provider routing separate from business services and prevents hidden double-cost behavior.

---

## Solution Flow V2

```text
Topic + keyword map
        |
        v
RetrievalProfileBuilder
        |
        v
Query families + source hints
        |
        v
For each query/source:
  fetch top 20 posts
        |
        v
Persist candidate batch
        |
        v
DeterministicRelevanceEngine
  - per-post score
  - per-post status
        |
        v
BatchHealthEvaluator
  - accepted ratio
  - strong accept count
  - consecutive weak batches
        |
        +--> weak batch -> stop this query/source path
        |
        +--> healthy batch -> continue same path
        |
        v
SelectiveExpansionPolicy
  - ACCEPTED post -> crawl comments
  - UNCERTAIN post -> optional by mode
  - REJECTED post -> stop
        |
        v
Comment scoring with parent context
        |
        v
CleanPayloadBuilder
        |
        v
AIBudgetGuardrail
        |
        v
AIClient
  primary: chiasegpu
  fallback: Claude
        |
        v
Labeling + Theme Analysis
```

---

## What Phase 7 Locks

Phase 7 now acts as a decision package for Phase 8. The locked outputs are:

- the problem framing and constraints
- the Solution Flow V2
- the batch-gating logic for search quality
- the deterministic relevance model shape
- the selective expansion policy
- the clean-payload stage
- the AI budget and provider routing rules

---

## What Phase 8 Will Implement

Phase 8 should deliver the first production implementation of:

1. retrieval profile builder and diversified query execution
2. candidate persistence and deterministic relevance scoring
3. batch-health gating per query/source path
4. selective comment expansion
5. clean payload builder
6. AI budget guardrails plus provider telemetry

---

## Documents

- [BRD / BA Problem Brief](./ba-problem-brief.md)
- [Technical Solution](./technical-solution.md)
- [User Stories](./user-stories.md)
- [AI Provider Strategy](./ai-provider-strategy.md)
- [Production Run Audit - run-c973315b04](./production-run-c973315b04-analysis.md)

Document roles:

- `ba-problem-brief.md`: source of truth for context, problem, scope, and decisions
- `technical-solution.md`: source of truth for Solution Flow V2 and implementation architecture
- `user-stories.md`: source of truth for phase-scoped acceptance criteria
- `ai-provider-strategy.md`: source of truth for all AI routing, failover, and telemetry rules
