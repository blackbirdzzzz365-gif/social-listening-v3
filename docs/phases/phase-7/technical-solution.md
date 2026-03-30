# Technical Solution - Phase 7
## Solution Flow V2 For Phase 8 Delivery

**Status:** Locked architecture for implementation  
**Updated:** 2026-03-31

---

## 1. Technical Objective

Implement a retrieval-to-analysis pipeline that:

- explores Facebook with more than one query/source path
- stops weak paths early at the batch level
- scores each post/comment deterministically before deep expansion
- produces a cleaner accepted dataset for labeling and theme analysis
- routes every AI call through one provider policy

---

## 2. Current-State Findings From The Repo

### Retrieval and scoring

- planner logic can normalize and generate topic-oriented text, but retrieval still behaves too much like one short search string
- browser retrieval paths can collect posts/comments, but they do not yet enforce a pre-AI relevance gate
- comment expansion is not yet strongly guarded by post quality

### Persistence

- `crawled_posts` already exists and is the fastest path for adding pre-AI state
- there is no candidate-stage schema yet

### AI routing

- `AIClient` already centralizes provider access
- current implementation prefers `chiasegpu` and only falls back on timeout
- failover policy and telemetry need to be made explicit and broader

---

## 3. Locked Architecture

```text
Topic + keyword map
        |
        v
RetrievalProfileBuilder
        |
        v
QueryExecutionPlanner
  - query families
  - source hints
  - batch budget
        |
        v
For each query/source path:
  fetch top 20 posts
        |
        v
Candidate persistence
        |
        v
DeterministicRelevanceEngine
  - post-level scoring
        |
        v
BatchHealthEvaluator
  - continue / downgrade / stop path
        |
        +--> stop weak path
        |
        +--> continue healthy path
        |
        v
SelectiveExpansionPolicy
  - crawl comments only for allowed posts
        |
        v
Comment candidate persistence
        |
        v
ParentAwareCommentScorer
        |
        v
CleanPayloadBuilder
        |
        v
AIBudgetGuardrail
        |
        v
AIClient
  - primary: chiasegpu
  - fallback: Claude
        |
        v
Labeling + Theme Analysis
```

---

## 4. Solution Flow V2

### Step 1 - Build retrieval profile

Input:

- topic
- keyword map
- optional exclusions
- optional seed groups

Output:

- `anchors`
- `related_terms`
- `negative_terms`
- `query_families`
- `source_hints`

### Step 2 - Plan query/source paths

Each run builds a queue of paths such as:

- `SEARCH_POSTS + brand`
- `SEARCH_POSTS + pain_point`
- `SEARCH_GROUPS + brand`
- `SEARCH_IN_GROUP + accepted_group`
- `CRAWL_FEED + accepted_group`

### Step 3 - Fetch one batch of roughly 20 posts

The system should not blindly crawl one path forever.

For one query/source path:

- fetch the next top `20` posts
- normalize lightweight metadata
- persist them immediately with query/source/batch context

This preserves auditability before any accept/reject decision is made.

### Step 4 - Score each post candidate

Each candidate is scored by deterministic rules, not AI.

Initial score dimensions:

- `anchor_score`
- `related_score`
- `negative_penalty`
- `quality_score`
- `source_score`

Output:

- `ACCEPTED`
- `REJECTED`
- `UNCERTAIN`
- `score_total`
- `score_breakdown`
- `rejection_reason` or decision reason

### Step 5 - Evaluate batch health

After scoring the batch, compute:

- `accepted_ratio`
- `uncertain_ratio`
- `strong_accept_count`
- `consecutive_weak_batches`

Initial default policy for Phase 8:

- continue path when `accepted_ratio >= 0.25`
- also continue when `strong_accept_count >= 3` even if accepted ratio is slightly lower
- mark batch weak when `accepted_ratio < 0.10` and `uncertain_ratio < 0.20`
- stop a path after `2` consecutive weak batches
- also stop a path when `60` scanned posts still produce fewer than `3` accepted posts

These values are default heuristics, not hard product law. They should be configurable.

### Step 6 - Selective expansion

For posts in the batch:

- `ACCEPTED` -> allow comment crawl
- `UNCERTAIN` -> allow comment crawl only in balanced mode
- `REJECTED` -> do not crawl comments

This is record-level gating. It exists at the same time as batch-level gating.

### Step 7 - Score comments with parent context

Comments are handled like posts, but with parent context added:

- comment becomes a candidate
- comment receives deterministic scoring
- parent post validity contributes to score

Short comments can still pass if parent context is strong.

### Step 8 - Build clean accepted payload

Before labeling/theme analysis:

- normalize whitespace
- strip duplicated lines
- strip UI chrome fragments
- compute canonical URL and normalized hash
- attach quality flags
- reject or downgrade records that remain too noisy

### Step 9 - Guard AI budget and route provider calls

Only then may records go to AI:

- strict mode -> accepted only
- balanced mode -> accepted first, uncertain second

All AI calls go through `AIClient`:

- primary provider: `chiasegpu`
- fallback provider: Claude
- fallback only for provider/runtime failure classes

---

## 5. Record State Model

### Record-level states

- `DISCOVERED`
- `SCORED_ACCEPTED`
- `SCORED_REJECTED`
- `SCORED_UNCERTAIN`
- `EXPANDED`
- `CLEAN_ACCEPTED`
- `AI_QUEUED`
- `AI_DONE`

### Query-path states

- `ACTIVE`
- `WEAK`
- `STOPPED`
- `EXHAUSTED`

---

## 6. Phase 8 Persistence Path

Phase 8 should extend `crawled_posts` instead of adding a new candidate table first.

Recommended new fields:

- `processing_stage`
- `pre_ai_status`
- `pre_ai_score`
- `pre_ai_reason`
- `score_breakdown_json`
- `quality_flags_json`
- `query_family`
- `source_type`
- `source_batch_index`
- `batch_decision`
- `provider_used`
- `fallback_used`

Why this path is locked:

- it fits the current codebase fastest
- it avoids a bigger migration before the scoring model is validated
- it still leaves room for a future dedicated candidate table if needed

---

## 7. Core Modules

### RetrievalProfileBuilder

Builds the structured retrieval profile from topic input.

### QueryExecutionPlanner

Creates ordered query/source paths and manages batch budgets.

### DeterministicRelevanceEngine

Scores posts before expansion and before AI.

### BatchHealthEvaluator

Decides whether a query/source path should continue.

### SelectiveExpansionPolicy

Allows or blocks comment crawl per post and per mode.

### ParentAwareCommentScorer

Scores comments with parent-post context.

### CleanPayloadBuilder

Prepares accepted records for downstream AI.

### AIBudgetGuardrail

Controls which records are eligible for labeling/theme analysis.

### AIClient Provider Router

Enforces provider selection, retry, fallback, and telemetry rules.

---

## 8. AI Provider Routing

Provider flow for every AI interaction:

1. call `chiasegpu`
2. retry once for retryable provider failure
3. fallback to Claude only if retryable failure persists
4. fail hard when fallback also fails

Fallback is allowed for:

- timeout
- transport/network failure
- HTTP 429
- HTTP 5xx
- invalid provider envelope
- empty model content

Fallback is not allowed for:

- unsupported model configuration
- invalid request payload
- prompt/schema design bugs
- deterministic validation failures after receiving a valid response

---

## 9. Metrics And Audit Output

The system should produce:

- accepted/rejected/uncertain counts per query family
- accepted/rejected/uncertain counts per source type
- batch health per query/source path
- number of comments crawled from accepted posts
- accepted-to-AI ratio
- provider usage by service
- fallback count and fallback reason

---

## 10. Phase 8 Implementation Slices

### Slice 1

Retrieval profile builder plus query/source metadata persistence.

### Slice 2

Post candidate scoring and `pre_ai_status` persistence.

### Slice 3

Batch health evaluation and path stopping rules.

### Slice 4

Selective expansion and parent-aware comment scoring.

### Slice 5

Clean payload builder and dedupe/quality flags.

### Slice 6

AI budget guardrail, provider failover, and telemetry.

---

## 11. Design Summary

Phase 7 Solution Flow V2 is intentionally simple:

`scan in small batches -> score quickly -> continue only healthy paths -> expand only accepted records -> clean payload -> call AI carefully`

That is the concrete architecture Phase 8 should now build.
