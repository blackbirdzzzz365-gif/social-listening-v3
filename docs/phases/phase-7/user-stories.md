# User Stories — Phase 7: Retrieval Quality Gating Before AI Cost
## AI Facebook Social Listening & Engagement v3

**Product:** AI-powered Facebook research and engagement assistant
**Primary users:** Researcher, Marketer, Sales/BD
**Language:** Vietnamese first, English supported
**Phase:** 7 — Retrieval Quality Gating Before AI Cost
**Updated:** 2026-03-30

---

## Tai sao can Phase 7

Phase 1 da prove duoc core crawl loop.
Phase 2 da prove duoc post-labeling va audience-aware theme filtering.
Phase 6 da cai thien UX.

Nhung truoc khi di xa hon, retrieval layer can duoc nang cap:

- neu retrieval khong tim thay dung content thi downstream se ngheo
- neu retrieval thu qua nhieu content sai thi downstream se ton AI cost
- neu extraction payload ban thi labeling/theme se giam do chinh xac

Phase 7 giai bai toan "garbage-in" o truoc AI.

---

## Cross-Cutting Rules

**R-70 — Retrieval precision phai co explainability**  
Moi record bi reject truoc AI phai co `rejection_reason` hoac `score_breakdown` de debug duoc.

**R-71 — Rule-based first, AI later**  
AI khong duoc dong vai tro bo loc dau tien cho toan bo candidate pool.

**R-72 — Comment phai duoc danh gia voi parent context**  
Comment khong duoc yeu cau exact-topic-keyword cung nhu post; parent-validity la 1 input cua scoring.

**R-73 — Chi valid post moi duoc selective expansion**  
`crawl_comments` hoac expansion tiep theo chi duoc chay tren posts qua relevance gate.

**R-74 — Query diversity hon query perfection**  
He thong nen thu nhieu query intent nho gon hon la dat ky vong 1 query duy nhat se bao phu toan bo topic.

**R-75 — Accepted record la don vi ton AI cost**  
Metrics cost phai tinh tren accepted records, khong tinh chung voi raw candidates.

---

## User Stories

### US-70: Generate Diverse Retrieval Queries From One Topic

**As a** researcher  
**I want** the system to produce multiple retrieval queries for one topic  
**So that** retrieval does not depend on a single Facebook search query

**Acceptance Criteria:**

- Given a topic and keyword map
  When the retrieval profile is built
  Then the system produces query variants for at least:
  `brand/entity`, `pain point`, `question`, `comparison`, and `complaint/experience`

- Given a generated query
  When it is stored for execution
  Then it includes a source tag or query intent so later metrics can show which query family worked

- Given a query is too generic or too long
  When the planner normalizes it
  Then it is trimmed safely without losing the main anchor phrase

### US-71: Score Posts With A Deterministic Relevance Engine Before AI

**As a** product/runtime owner  
**I want** each crawled post candidate to be scored by deterministic rules  
**So that** only relevant records move forward to downstream crawl and AI stages

**Acceptance Criteria:**

- Given a post candidate is retrieved
  When the relevance engine runs
  Then the score includes signals from:
  `anchor terms`, `related terms`, `negative patterns`, and `quality checks`

- Given a post contains strong negative/promo patterns
  When the relevance engine evaluates it
  Then the post can be rejected even if it contains anchor keywords

- Given a post lacks exact anchor wording but strongly matches related topic language
  When the score exceeds the threshold
  Then it may still be accepted

- Given the engine returns a decision
  When the record is persisted
  Then the status is one of:
  `ACCEPTED`, `REJECTED`, `UNCERTAIN`
  And the reason or score breakdown is stored

### US-72: Only Crawl Comments For Valid Posts

**As a** researcher  
**I want** comments to be crawled only from posts that already look relevant  
**So that** the system does not waste effort and AI cost on low-value threads

**Acceptance Criteria:**

- Given a post is `REJECTED`
  When the run reaches comment expansion
  Then comments for that post are not crawled

- Given a post is `ACCEPTED`
  When the run reaches comment expansion
  Then comments may be crawled according to budget and per-post limit

- Given a post is `UNCERTAIN`
  When configuration disables uncertain expansion
  Then comments are skipped for that post

### US-73: Score Comments With Parent-Aware Rules

**As a** researcher  
**I want** comments to be evaluated with both their own text and the parent post context  
**So that** short but meaningful comments are not lost just because they omit the main keyword

**Acceptance Criteria:**

- Given a comment belongs to an accepted post
  When the comment scoring runs
  Then parent topic context contributes to the score

- Given a short comment such as `minh cung bi vay`
  When the parent post is strongly valid
  Then the comment may still be accepted

- Given a comment is generic or low-information
  When the score stays below threshold
  Then it is rejected before AI

### US-74: Build A Clean Payload For Accepted Records

**As a** runtime engineer  
**I want** accepted records to go through a payload cleaning stage  
**So that** downstream labeling/theme analysis sees cleaner text and fewer UI artifacts

**Acceptance Criteria:**

- Given a candidate contains duplicated lines, UI labels, or noisy chrome text
  When the cleaning stage runs
  Then the accepted payload strips or flags that noise

- Given two records are near-duplicates by URL or normalized content
  When the cleaning stage runs
  Then only one is kept in the accepted analysis set unless both are intentionally distinguished

- Given a payload fails quality checks
  When the system prepares accepted records
  Then the record is marked with quality flags and may be rejected or downgraded

### US-75: Apply AI Only To Accepted Or Explicitly Uncertain Records

**As a** product owner  
**I want** AI cost to be spent only on records that pass retrieval quality gates  
**So that** labeling and theme analysis are both cheaper and more trustworthy

**Acceptance Criteria:**

- Given a run contains accepted, rejected, and uncertain records
  When AI labeling starts
  Then rejected records are excluded from the labeling queue

- Given the system is configured in strict mode
  When uncertain records exist
  Then only accepted records go to AI

- Given the system is configured in balanced mode
  When uncertain records exist
  Then uncertain records may be sent to AI as a second-priority band

- Given a run completes
  When metrics are shown
  Then the user can see:
  `candidates_retrieved`, `accepted_count`, `rejected_count`, `uncertain_count`, and `ai_records_processed`

### US-76: Audit Retrieval Quality And Cost By Source

**As a** product/operator team  
**I want** visibility into which query/source combinations produce good records  
**So that** we can improve retrieval strategy over time instead of guessing

**Acceptance Criteria:**

- Given a run executes retrieval from multiple query families or sources
  When summary metrics are shown
  Then we can see accepted/rejected ratios by query family and source

- Given one retrieval path produces many rejects
  When the run is reviewed
  Then that path is obvious in the audit output

- Given a run completes
  When the quality summary is generated
  Then it includes cost-oriented metrics such as `accepted_to_ai_ratio`

---

## Out of Scope

- Full semantic embedding search outside Facebook
- Human review UI for every rejected record
- Automatic query self-learning loop in the same phase
- Replacing audience labeling/theming with rules only
