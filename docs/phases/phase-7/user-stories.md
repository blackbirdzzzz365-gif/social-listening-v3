# User Stories - Phase 7
## Locked Backlog Feeding Phase 8

**Product:** AI-powered Facebook research and engagement assistant  
**Primary users:** Researcher, Marketer, Sales/BD  
**Language:** Vietnamese first, English supported  
**Updated:** 2026-03-31

---

## Cross-Cutting Rules

**R-70 - Retrieval precision must stay explainable**  
Every rejected or uncertain record must keep `reason`, `score_breakdown`, or both.

**R-71 - Rule-based first, AI later**  
AI must not be the first-pass filter for the full candidate pool.

**R-72 - Query-level gating and record-level gating both apply**  
One post can pass while the broader query path is still downgraded or stopped later.

**R-73 - Comments must be scored with parent context**  
Comments are not judged only by their standalone text.

**R-74 - Healthy batch continuation beats blind scrolling**  
The system should stop weak query/source paths early and move to a different path.

**R-75 - Accepted records are the main unit of AI cost**  
Metrics and budget policies must focus on accepted records, not only raw retrieved count.

**R-76 - All AI routing goes through one provider policy**  
`chiasegpu` is default. Claude is fallback only.

---

## User Stories

### US-70: Build A Retrieval Profile From One Topic

**As a** researcher  
**I want** the system to derive multiple query families from one topic  
**So that** retrieval does not depend on one Facebook search string

**Acceptance Criteria**

- Given a topic and keyword map
  When the retrieval profile is built
  Then the system outputs at least:
  `anchors`, `related_terms`, `negative_terms`, and `query_families`

- Given the profile is stored for one run
  When execution starts
  Then each query includes a `query_family` tag and an intended `source_type`

- Given one query is too generic or too long
  When it is normalized
  Then the main anchor phrase remains intact

### US-71: Evaluate One Query Path In 20-Post Batches

**As a** runtime owner  
**I want** each query/source path to be evaluated in small batches  
**So that** the system can stop weak retrieval paths early

**Acceptance Criteria**

- Given a query/source path is active
  When the system fetches the next batch
  Then it retrieves roughly the top `20` posts before deciding whether to continue

- Given the batch is scored
  When batch health is calculated
  Then the system stores metrics including:
  `accepted_ratio`, `uncertain_ratio`, and `strong_accept_count`

- Given `2` consecutive weak batches occur
  When the path is reevaluated
  Then the system stops that query/source path and moves to another path

### US-72: Score Posts With A Deterministic Relevance Engine

**As a** product/runtime owner  
**I want** each retrieved post candidate to be scored by deterministic rules  
**So that** only relevant posts move forward to deep crawl and AI

**Acceptance Criteria**

- Given a post candidate is retrieved
  When the relevance engine runs
  Then the score includes:
  `anchor_score`, `related_score`, `negative_penalty`, `quality_score`, and `source_score`

- Given a post contains strong negative or promo patterns
  When it is scored
  Then it may be rejected even if anchor words appear

- Given a post strongly matches topic context but not exact anchor wording
  When total score exceeds threshold
  Then it may still be accepted

- Given scoring completes
  When the record is persisted
  Then the record stores:
  `pre_ai_status`, `pre_ai_score`, and a reason or score breakdown

### US-73: Expand Only Accepted Posts

**As a** researcher  
**I want** comment crawl to happen only for posts that passed the gate  
**So that** the system does not waste crawl budget on weak threads

**Acceptance Criteria**

- Given a post is `REJECTED`
  When expansion is evaluated
  Then no comments are crawled for that post

- Given a post is `ACCEPTED`
  When expansion is evaluated
  Then comments may be crawled subject to run budget and per-post limits

- Given a post is `UNCERTAIN`
  When the run mode is strict
  Then comments are skipped for that post

### US-74: Score Comments With Parent Context

**As a** researcher  
**I want** comments to be scored with both comment text and parent-post context  
**So that** short but useful comments are not unfairly rejected

**Acceptance Criteria**

- Given a comment belongs to an accepted post
  When comment scoring runs
  Then parent context contributes to the decision

- Given a short comment such as `minh cung bi vay`
  When the parent post is strongly valid
  Then the comment may still be accepted

- Given a generic comment remains low-information
  When score stays below threshold
  Then it is rejected before AI

### US-75: Build A Clean Payload For Accepted Records

**As a** runtime engineer  
**I want** only accepted records to enter a dedicated cleaning stage  
**So that** downstream labeling/theme analysis receives cleaner text

**Acceptance Criteria**

- Given accepted content contains duplicate lines, UI labels, or noisy fragments
  When the cleaning stage runs
  Then those artifacts are stripped or flagged

- Given two records are near-duplicates by canonical URL or normalized content
  When payload cleaning runs
  Then only one proceeds unless the system explicitly preserves both

- Given a record remains too noisy after cleaning
  When quality flags are applied
  Then it can be downgraded or excluded before AI

### US-76: Apply AI Only To Allowed Records And Through One Provider Policy

**As a** product owner  
**I want** AI calls to happen only on quality-gated records and only through one central provider router  
**So that** cost and provider behavior stay controlled

**Acceptance Criteria**

- Given a run contains accepted, rejected, and uncertain records
  When AI labeling starts
  Then rejected records are excluded from the AI queue

- Given the run mode is `strict`
  When uncertain records exist
  Then only accepted records go to AI

- Given `chiasegpu` fails with a retryable provider/runtime failure
  When `AIClient` exhausts retry
  Then Claude may be used as fallback

- Given the failure is due to invalid payload, unsupported model, or deterministic schema bug
  When the AI call fails
  Then the system does not auto-fallback to Claude

### US-77: Audit Retrieval Quality, AI Cost, And Provider Usage

**As a** product/operator team  
**I want** quality and cost metrics by query, source, and provider  
**So that** we can improve the system without guessing

**Acceptance Criteria**

- Given a run uses multiple query families and source paths
  When run metrics are shown
  Then accepted/rejected/uncertain ratios are available by `query_family` and `source_type`

- Given one path produces repeated weak batches
  When the run is reviewed
  Then the stopped path is obvious in the audit output

- Given AI work completes
  When provider telemetry is reviewed
  Then we can see:
  `provider_used`, `fallback_used`, and fallback reason when applicable

---

## Out Of Scope

- full semantic retrieval outside Facebook
- automatic self-learning query loops
- human review UI for every rejected record
- replacing labeling/theme analysis with rules only
