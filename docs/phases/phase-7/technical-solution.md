# Technical Solution — Phase 7
## Retrieval Quality Gating Before AI Cost

**Updated:** 2026-03-30  
**Status:** Brainstorm solution draft

---

## Locked Direction

- Phase 7 uu tien giai bai toan retrieval quality truoc AI
- Rule-based gate la lop default de quyet dinh record nao duoc di tiep
- AI chi vao sau cho accepted band, hoac uncertain band neu mode cho phep
- Comment scoring phai parent-aware

---

## Current-State Findings From Repo

### 1. Query generation van don gian

- Search query hien duoc planner normalize manh
- query length va wording hien van thien ve 1 search string ngan
- chua co retrieval profile da query theo intent

### 2. Browser retrieval layer chua co relevance gate that su

- `search_posts()`, `search_in_group()`, `crawl_feed()`, `crawl_comments()` chu yeu collect text + URL
- chua co scoring theo:
  - anchor relevance
  - related context
  - negative commercial patterns
  - extraction quality

### 3. Selective expansion chua duoc ap dung

- comments co the duoc crawl tu discovered post refs ma chua qua quality gate
- day la noi de tieu ton effort va AI cost nhat

### 4. Accepted payload chua duoc clean rieng

- text extraction hien tai de lan UI chrome va noisy fragments
- label/theme services phai xu ly input khong deu chat

---

## Proposed Architecture

```text
Topic + keyword map
        |
        v
Retrieval Profile Builder
        |
        v
Multi-source Retrieval
  - SEARCH_POSTS
  - SEARCH_GROUPS
  - SEARCH_IN_GROUP
  - CRAWL_FEED
        |
        v
Candidate Store
        |
        v
Deterministic Relevance Engine
  -> ACCEPTED
  -> REJECTED
  -> UNCERTAIN
        |
        +--> selective expansion (comments / more group crawl)
        |
        v
Clean Payload Builder
        |
        v
AI Labeling + Theme Analysis
```

---

## Module Proposal

### 1. RetrievalProfileBuilder

Responsibility:

- tao `query families`
- tao `anchor term clusters`
- tao `related term clusters`
- tao `negative patterns`
- tao `source hints` cho group scoring

Inputs:

- topic
- keyword map tu Phase 1
- optional user hints / excluded terms / seed groups

Outputs:

- `retrieval_profile`

Example shape:

```json
{
  "anchors": ["tpbank evo", "the evo", "tpbank"],
  "related_terms": ["phi thuong nien", "cashback", "han muc", "mien phi", "review"],
  "negative_terms": ["ib", "inbox", "mo the", "ref", "chot don"],
  "query_families": [
    {"intent": "brand", "query": "tpbank evo"},
    {"intent": "pain_point", "query": "phi tpbank evo"},
    {"intent": "question", "query": "tpbank evo co tot khong"}
  ]
}
```

### 2. RetrievalCandidateStore

Decision:

- can co candidate layer truoc accepted analysis set

Implementation options:

- Option A:
  them bang moi `retrieval_candidates`
- Option B:
  mo rong `crawled_posts` voi stages

Recommendation:

- Neu muon lam nhanh: Option B
- Neu muon kien truc sach va audit tot: Option A

Key fields:

- `candidate_id`
- `run_id`
- `source_type`
- `query_family`
- `record_type`
- `source_url`
- `raw_text`
- `normalized_text`
- `parent_ref`
- `candidate_status`
- `score_total`
- `score_breakdown_json`
- `rejection_reason`

### 3. DeterministicRelevanceEngine

Responsibility:

- score post/comment truoc AI
- tra ve `ACCEPTED`, `REJECTED`, `UNCERTAIN`

Score dimensions:

- `anchor_score`
- `related_score`
- `negative_penalty`
- `quality_score`
- `source_score`
- `parent_context_score` cho comments

Decision shape:

```json
{
  "status": "ACCEPTED",
  "score_total": 0.78,
  "score_breakdown": {
    "anchor_score": 0.40,
    "related_score": 0.20,
    "quality_score": 0.10,
    "source_score": 0.08,
    "negative_penalty": 0.00
  },
  "reason": "matched brand anchor + pain context + clean text"
}
```

### 4. SelectiveExpansionPolicy

Responsibility:

- chi quyet dinh co crawl tiep khong

Rules:

- `ACCEPTED` post -> cho crawl comments
- `REJECTED` post -> khong crawl comments
- `UNCERTAIN` post -> optional theo mode
- group/source co accepted ratio thap -> giam uu tien crawl sau

### 5. CleanPayloadBuilder

Responsibility:

- bien accepted candidate thanh payload sach cho labeling/theme

Functions:

- normalize whitespace
- strip duplicate lines
- strip UI chrome markers
- detect overly generic text
- dedupe by canonical url + normalized hash
- attach quality flags

### 6. AI Budget Guardrail

Responsibility:

- chi gui sang labeling/theme:
  - accepted records
  - hoac uncertain band neu config balance mode

Modes:

- `strict`
- `balanced`

---

## Retrieval Strategy Changes

### A. Query diversification

Thay vi 1 query:

- brand/entity query
- question query
- complaint query
- comparison query
- feature/use-case query

### B. Source diversification

Khong chi `SEARCH_POSTS`:

- `SEARCH_GROUPS` tim nguon
- `SEARCH_IN_GROUP` khi da co group relevance
- `CRAWL_FEED` trong groups duoc cham diem tot
- seed groups tu user / run history

### C. Source scoring

Moi source/group nen co score:

- da co accepted post truoc day chua
- private/public
- co accessible khong
- accepted ratio lich su

---

## Rule Design Notes

### Post scoring

Khong dung rule "phai chua tat ca mandatory keywords".
Dung rule:

- cham it nhat 1 anchor cluster
- dat tong score tren threshold
- negative terms co the reject som

### Comment scoring

Khong bat comment phai tu than chua full topic.

Dung rule:

- parent post validity la input
- comment co the ngan nhung van valid neu context manh
- generic comment van reject neu quality score qua thap

### Vietnamese normalization

Can support:

- co dau / khong dau
- slang
- typo nhe
- viet tat pho bien

Neu bo qua phan nay, exact keyword rules se qua mong manh.

---

## Data Model Direction

### Minimal-change path

Mo rong `crawled_posts`:

- `processing_stage`
- `pre_ai_status`
- `pre_ai_score`
- `pre_ai_reason`
- `quality_flags_json`
- `query_family`
- `source_type`

Pros:

- ship nhanh

Cons:

- raw candidates va accepted analysis set van tron lifecycle

### Cleaner path

Them `retrieval_candidates` va giu `crawled_posts` cho accepted records.

Pros:

- clean architecture
- de audit accepted/rejected/uncertain
- de thong ke cost

Cons:

- them schema va orchestration

Recommendation:

- Neu Phase 7 muon giai bai toan chat luong nghiem tuc, nen di theo cleaner path

---

## Suggested Delivery Order

### Slice 1 — Retrieval profile + audit metrics

- query families
- source tags
- acceptance metrics scaffold

### Slice 2 — Post relevance engine

- anchor/related/negative/quality scoring
- accepted/rejected/uncertain

### Slice 3 — Selective comment crawl

- chi crawl comments cho valid posts
- comment parent-aware scoring

### Slice 4 — Clean payload builder

- normalization
- dedupe
- quality flags

### Slice 5 — AI budget guardrail

- strict/balanced mode
- accepted-to-AI metrics

---

## Success Metrics

- `candidates_retrieved`
- `accepted_count`
- `rejected_count`
- `uncertain_count`
- `accepted_ratio`
- `comments_crawled_per_accepted_post`
- `ai_records_processed`
- `accepted_to_ai_ratio`
- `duplicate_rate`
- `noise_flag_rate`
- `accepted_ratio_by_query_family`
- `accepted_ratio_by_source`

---

## Recommendation

- Chot Phase 7 nhu mot bai toan retrieval-quality phase, khong phai chi la them keyword filter
- Implement theo huong:
  - multi-source retrieval
  - deterministic relevance engine
  - selective expansion
  - clean payload builder
  - AI chi cho accepted data
