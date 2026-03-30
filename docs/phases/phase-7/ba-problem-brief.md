# BRD / BA Problem Brief - Phase 7
## Retrieval Quality Gating Before AI Cost

**Status:** Locked scope feeding Phase 8 implementation  
**Updated:** 2026-03-31

---

## 1. Executive Summary

`social-listening-v3` already has:

- browser retrieval
- crawl persistence
- content labeling
- theme analysis

But the system still spends too much effort and AI cost on weak input. The core problem is no longer "can we crawl?" but "can we decide early which records are worth crawling deeper and worth paying AI for?"

Phase 7 locks the operating model that Phase 8 must implement:

- diversified retrieval instead of one search string
- deterministic relevance gating before deep crawl and before AI
- query/source continuation only while retrieved batches stay healthy
- clean payload generation before labeling/theme analysis
- centralized AI provider routing with `chiasegpu` as primary and Claude as fallback

---

## 2. Product Context

### Current product capability

The product can already:

- generate a plan from topic input
- execute browser actions against Facebook
- persist crawled posts/comments
- label content and generate themes

### Current product weakness

The quality of downstream insight is capped by the quality of retrieval and extraction:

- cold or weak Facebook search gives poor recall
- noisy retrieved records waste crawl and AI budget
- dirty payloads reduce labeling and theme quality

### Why this must be solved now

If retrieval quality stays weak, every later phase keeps paying for garbage-in:

- comment crawl expands weak threads
- AI is used on records that should have been rejected by rules
- operators cannot explain why one query/source worked and another failed

---

## 3. Problem Statement

The system currently lacks a strong pre-AI gating model across retrieval, expansion, and provider execution. As a result:

- relevant posts can be missed because Facebook search is context-dependent
- low-quality posts can still move forward to comment crawl and labeling
- extraction noise reaches downstream analysis
- AI cost is spent before enough deterministic filtering has happened

---

## 4. Users Affected

- researcher who needs relevant qualitative signal fast
- marketer who wants actual user pain points, not retrieval noise
- founder or operator who cares about trustworthy insight and AI cost efficiency

---

## 5. Root Causes

### Problem A - Search miss

Root causes:

- Facebook global search is personalized
- cold accounts lack graph/group context
- current query generation is too shallow
- source diversification is underused

### Problem B - Weak filtering

Root causes:

- no deterministic relevance engine before deep crawl
- no batch-level decision on whether one query/source path is still worth pursuing
- comment crawl can start from posts that have not been strongly validated

### Problem C - Dirty payload

Root causes:

- extraction text can include UI chrome, duplicate fragments, and generic noise
- there is no dedicated clean-payload stage before AI
- raw candidates and analysis-ready records are not clearly separated

### Problem D - AI routing is not yet governed as part of cost control

Root causes:

- provider strategy is documented separately but not yet locked into the same retrieval-quality story
- fallback conditions are currently too narrow and too implicit
- telemetry for provider usage and failover is not yet part of retrieval-to-analysis auditability

---

## 6. What We Are Deciding In Phase 7

### D-70 - Retrieval must be profile-driven

Each topic must produce a `retrieval_profile` containing:

- anchor clusters
- related-term clusters
- negative patterns
- query families
- optional seed groups and source hints

### D-71 - Query execution must be batch-gated

For each query/source path:

- fetch roughly the top `20` posts
- score them deterministically
- calculate batch health
- continue the path only while the batch remains healthy

This is the main Solution Flow V2 upgrade.

### D-72 - Candidate persistence happens before the relevance decision

Every retrieved item is first stored as a candidate with source and query context, then scored into:

- `ACCEPTED`
- `REJECTED`
- `UNCERTAIN`

This preserves explainability, rejection reasons, and source/query diagnostics.

### D-73 - Record-level gating drives selective expansion

- accepted posts may trigger comment crawl
- uncertain posts may trigger comment crawl only in allowed modes
- rejected posts do not expand further

### D-74 - Query-level gating and record-level gating both exist

Phase 7 does not choose between them. It uses both:

- record-level gating decides whether one post/comment can move forward
- batch-level gating decides whether one query/source path is still worth exploring

### D-75 - Phase 8 implementation will use the minimal-change persistence path

To reduce schema churn and ship faster on the current codebase, Phase 8 should extend `crawled_posts` with pre-AI fields instead of introducing a new `retrieval_candidates` table in the first delivery slice.

Future migration to a separate candidate table remains allowed, but it is not the Phase 8 default path.

### D-76 - AI remains behind the quality gate

AI is allowed only for:

- accepted records
- uncertain records when the run is in an explicitly configured balanced mode

AI must not become the first-pass relevance filter.

### D-77 - AI provider routing is centralized and policy-driven

All AI calls must go through `AIClient`:

- primary provider: `chiasegpu`
- fallback provider: Claude
- fallback allowed only for provider/runtime failures
- no automatic fallback for deterministic request, prompt, schema, or payload bugs

---

## 7. Goals

### Product goals

- increase precision of accepted posts/comments
- reduce wasted comment crawl on weak posts
- reduce AI calls per useful insight run
- improve trust in theme outputs by improving input quality

### Operational goals

- expose accepted/rejected ratios by query family and source
- expose why a record was rejected
- expose when and why provider fallback happened

---

## 8. Success Metrics

Phase 8 should measure at least:

- `candidates_retrieved`
- `accepted_count`
- `rejected_count`
- `uncertain_count`
- `accepted_ratio`
- `comments_crawled_from_accepted_posts`
- `ai_records_processed`
- `accepted_to_ai_ratio`
- `accepted_ratio_by_query_family`
- `accepted_ratio_by_source_type`
- `provider_usage_by_service`
- `fallback_count_by_reason`

---

## 9. Requirements Split

### Retrieval

- build query families from one topic
- support multiple source paths
- attach source and query metadata to each candidate

### Validation

- deterministic scoring for posts and comments
- parent-aware scoring for comments
- record decisions must be explainable

### Batch Gating

- assess each 20-post batch
- stop weak query/source paths early
- continue healthy ones

### Expansion

- comment crawl only for passed posts by policy
- no blind expansion from weak candidates

### Clean Payload

- normalize text
- strip UI noise
- detect duplicates
- attach quality flags before AI

### AI Routing

- use `chiasegpu` first
- fallback to Claude only for allowed provider failures
- record provider telemetry

### Auditability

- query/source/batch metrics
- record-level score breakdown
- provider and fallback metadata

---

## 10. Scope For Phase 8

Phase 8 should implement:

1. retrieval profile builder
2. batch-based query execution
3. deterministic post scoring
4. selective comment expansion
5. parent-aware comment scoring
6. clean payload builder
7. AI budget guardrail
8. AI provider failover policy and telemetry

Phase 8 does not need to implement:

- full semantic retrieval outside Facebook
- automatic query self-learning loops
- human review UI for all rejected records
- a new standalone candidate table if the extended `crawled_posts` path is sufficient

---

## 11. Constraints

- retrieval logic must stay explainable and debuggable
- exact mandatory keywords cannot be the only gate
- Vietnamese text normalization must support no-diacritic, slang, and mild typo variations
- AI cannot hide deterministic product bugs via automatic fallback

---

## 12. Recommendation

The system should be built around one concrete rule:

`retrieve broadly -> score fast -> continue only healthy paths -> crawl deeper only for accepted records -> clean payload -> spend AI carefully`

That is the locked business direction for Phase 7 and the implementation contract for Phase 8.
