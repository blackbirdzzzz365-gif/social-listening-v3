# Production Run Analysis - `run-c973315b04`
## Phase 7 Retrieval Quality Gating Audit

**Environment:** production VM on `e1.chiasegpu.vn`  
**Observed at:** 2026-03-31  
**Run ID:** `run-c973315b04`  
**Status:** `DONE / COMPLETED`

---

## 1. Why This Document Exists

This document captures one real production run after the Phase 7 retrieval-quality work landed.

The goal is not just to confirm that the run finished. The goal is to answer four operational questions with production evidence:

1. Did pre-AI gating actually reduce noisy crawl and AI cost?
2. Did batch gating stop weak query paths early?
3. Did accepted records become meaningful end-user insight?
4. If not, where exactly is the failure mode now?

Source evidence used for this document:

- production `GET /api/runs/{run_id}`
- production `GET /api/runs/{run_id}/labels/summary`
- production `GET /api/runs/{run_id}/records`
- production `GET /api/runs/{run_id}/themes?audience_filter=end_user_only`
- production SQLite data from `plan_runs`, `step_runs`, `crawled_posts`, `label_jobs`, `theme_results`, `content_labels`

---

## 2. Executive Verdict

Phase 7 is working in one important sense and still failing in another.

What is clearly working:

- the system is rejecting most records before AI
- weak query paths are being stopped early
- comment crawl is no longer expanding the whole candidate set blindly
- label job volume is much smaller than total crawl volume

What is still not solving the end-user problem:

- the accepted set is still dominated by commercial or promotional content
- the only end-user theme output is effectively transactional noise: `Xin gia` and `Ib`
- parent-aware comment scoring is currently too permissive and lets low-value commerce comments survive if the parent post was accepted

Net result:

- Phase 7 reduced waste
- Phase 7 did not yet produce trustworthy end-user insight for this run

---

## 3. Run Snapshot

### 3.1 Top-level run

| Field | Value |
| --- | --- |
| `run_id` | `run-c973315b04` |
| `plan_id` | `plan-ef0b3ab3` |
| `status` | `DONE` |
| `completion_reason` | `COMPLETED` |
| `started_at` | `2026-03-31T07:03:01.997162+00:00` |
| `ended_at` | `2026-03-31T07:24:12.538374+00:00` |
| `duration` | about 21m 10s |
| `total_records` | `193` |

### 3.2 Pre-AI status breakdown

| `pre_ai_status` | Count | Share |
| --- | ---: | ---: |
| `REJECTED` | 161 | 83.42% |
| `UNCERTAIN` | 24 | 12.44% |
| `ACCEPTED` | 8 | 4.15% |

### 3.3 Record-type breakdown

| Record type | Count |
| --- | ---: |
| `POST` | 186 |
| `COMMENT` | 7 |

### 3.4 Source breakdown

| Source type | Count |
| --- | ---: |
| `SEARCH_POSTS` | 100 |
| `SEARCH_IN_GROUP` | 86 |
| `CRAWL_COMMENTS` | 7 |

### 3.5 Query-family breakdown

| Query family | Count |
| --- | ---: |
| `brand` | 80 |
| `generic` | 67 |
| `pain_point` | 40 |
| `comparison` | 6 |

### 3.6 Batch-decision breakdown

| Batch decision | Count |
| --- | ---: |
| `continue` | 113 |
| `stop` | 80 |

### 3.7 Top rejection reasons

| Reason | Count |
| --- | ---: |
| `weak_signal` | 124 |
| `negative_hits=1` | 31 |
| `related_hits=1` | 5 |
| `anchor_hits=1, negative_hits=1` | 1 |

---

## 4. Step-by-Step Behavior

One important detail: `checkpoint_json` on production did not preserve the expanded query text in a clean field for every step. For readability, the step target from the run plan is used as the human-readable query context below.

### Step 1 - `SEARCH_POSTS`

Target: `mặt nạ bột đậu xanh`

Observed behavior:

- `actual_count = 81`
- first search path produced zero accepted posts
- second attempt was reformulated, but still produced zero useful output
- path stopped because `zero_accepted_batches_exceeded`

Batch summaries:

| Batch | Accepted | Uncertain | Rejected | Accepted ratio | Uncertain ratio | Decision | Batch decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 0 | 2 | 18 | 0.00 | 0.10 | `weak` | `continue` |
| 2 | 0 | 6 | 14 | 0.00 | 0.30 | `continue` | `stop` |

Assessment:

- this is exactly the kind of weak path that Phase 7 is supposed to terminate early
- the stop behavior looks correct

### Step 2 - `CRAWL_COMMENTS`

Target: `comments from posts in step-1`

Observed behavior:

- `actual_count = 0`

Assessment:

- correct behavior, because step 1 produced no accepted posts

### Step 3 - `JOIN_GROUP`

Target: `private-groups discovered from step-1`

Observed behavior:

- `actual_count = 0`

### Step 4 - `CHECK_JOIN_STATUS`

Target: `join-requests from step-3`

Observed behavior:

- `actual_count = 0`

Assessment for steps 3 and 4:

- no evidence of unnecessary group-join expansion from the weak first path

### Step 5 - `SEARCH_IN_GROUP`

Target: `keyword:da mụn in groups from step-1`

Observed behavior:

- `actual_count = 80`
- zero accepted posts
- path stopped because `zero_accepted_batches_exceeded`

Batch summaries:

| Batch | Accepted | Uncertain | Rejected | Accepted ratio | Uncertain ratio | Decision | Batch decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 0 | 1 | 19 | 0.00 | 0.05 | `weak` | `continue` |
| 2 | 0 | 0 | 20 | 0.00 | 0.00 | `weak` | `stop` |

Assessment:

- good cost-control behavior
- no sign that the system kept spending on a dead path

### Step 6 - `SEARCH_POSTS`

Target: `mặt nạ tự nhiên`

Observed behavior:

- `actual_count = 89`
- this was the only step that produced accepted posts
- total accepted posts from this path: `2`
- path stopped because `min_accepts_not_reached`
- accepted group IDs discovered: `353540636213177`

Batch summaries:

| Batch | Accepted | Uncertain | Rejected | Accepted ratio | Uncertain ratio | Decision | Batch decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 1 | 2 | 17 | 0.05 | 0.10 | `weak` | `continue` |
| 2 | 1 | 6 | 13 | 0.05 | 0.30 | `continue` | `continue` |
| 3 | 0 | 5 | 15 | 0.00 | 0.25 | `continue` | `stop` |

Assessment:

- the system found a narrow path that looked somewhat viable
- it did not over-commit to it
- but the quality of the accepted posts from this path is the core problem of the whole run

### Step 7 - `CRAWL_COMMENTS`

Target: `comments from posts in step-6`

Observed behavior:

- `actual_count = 12`
- comment acceptance was extremely high once the parent posts were accepted

Batch summaries:

| Batch | Accepted | Uncertain | Rejected | Accepted ratio | Uncertain ratio | Decision | Batch decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 4 | 0 | 0 | 1.00 | 0.00 | `continue` | `continue` |
| 2 | 6 | 2 | 0 | 0.75 | 0.25 | `continue` | `continue` |

Assessment:

- this is too permissive
- once a commercial parent post got accepted, comment gating became almost non-existent in practice
- this is the most important concrete failure mode observed in this run

### Step 8 - `SEARCH_IN_GROUP`

Target: `keyword:mặt nạ organic vs hóa học in groups from step-6`

Observed behavior:

- `actual_count = 60`
- zero accepted posts across the in-group expansion path
- path stopped quickly after weak batches and one reformulation

Batch summaries:

| Batch | Accepted | Uncertain | Rejected | Accepted ratio | Uncertain ratio | Decision | Batch decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 0 | 0 | 20 | 0.00 | 0.00 | `weak` | `continue` |
| 2 | 0 | 1 | 19 | 0.00 | 0.05 | `weak` | `stop` |
| reformulated batch 1 | 0 | 0 | 16 | 0.00 | 0.00 | `weak` | `continue` |

Assessment:

- stop behavior looks correct
- retrieval coverage is still weak for this topic/account context

---

## 5. Label and Theme State

### 5.1 Label job

| Field | Value |
| --- | --- |
| `label_job_id` | `label-job-41be54cd2d` |
| `status` | `DONE` |
| `model_name` | `claude-haiku-4-5` |
| `records_total` | `8` |
| `records_labeled` | `8` |
| `records_fallback` | `0` |
| `records_failed` | `0` |

Counts by author role:

| Author role | Count |
| --- | ---: |
| `brand_official` | 4 |
| `seller_affiliate` | 2 |
| `end_user` | 2 |

### 5.2 Theme output for `audience_filter=end_user_only`

| Field | Value |
| --- | --- |
| `posts_crawled` | `193` |
| `posts_included` | `2` |
| `posts_excluded` | `191` |
| `excluded_breakdown.pre_ai_rejected` | `185` |
| `excluded_breakdown.low_relevance` | `6` |

Produced themes:

| Theme | Sentiment | Post count | Sample quote |
| --- | --- | ---: | --- |
| `question` | `neutral` | 1 | `Xin giá` |
| `other` | `neutral` | 1 | `Ib` |

Assessment:

- the theme pipeline itself is behaving consistently with the accepted and labeled set
- the problem is upstream dataset quality, not theme rendering logic

---

## 6. Detailed Content Audit

This section captures the actual production records that explain the outcome.

### 6.1 Accepted records with the highest downstream impact

#### Accepted post A

- `post_id`: `fb-post-97402a30fd41839cbe580df6`
- `source_type`: `SEARCH_POSTS`
- `query_family`: `generic`
- `pre_ai_status`: `ACCEPTED`
- `pre_ai_score`: `0.49`
- `pre_ai_reason`: `anchor_hits=1, related_hits=1`

Excerpt:

> `Mặt Nạ Thiên Nhiên ... mặt nạ thiên nhiên ... collagen ... công dụng ...`

Downstream label:

- `author_role = brand_official`
- `content_intent = promotion`
- `commerciality_level = high`
- `user_feedback_relevance = low`

Interpretation:

- this should not be in the accepted set if the target is end-user insight
- lexical topicality was enough to pass it

#### Accepted post B

- `post_id`: `fb-post-1279427066957858`
- `source_type`: `SEARCH_POSTS`
- `query_family`: `generic`
- `pre_ai_status`: `ACCEPTED`
- `pre_ai_score`: `0.55`
- `pre_ai_reason`: `anchor_hits=1, related_hits=2`

Excerpt:

> `HẠT NGŨ HOA – MẶT NẠ THẢO MỘC TRỊ MỤN, LÀM MỊN DA ... công dụng nổi bật ... cách dùng ... giao hàng toàn quốc ...`

Downstream label:

- `author_role = seller_affiliate`
- `content_intent = promotion`
- `commerciality_level = high`
- `user_feedback_relevance = low`

Interpretation:

- same failure mode as accepted post A
- the deterministic gate is still allowing commercial promotional posts to masquerade as relevant topical posts

### 6.2 Accepted comments that explain the final theme outcome

#### Accepted comment C

- `post_id`: `fb-comment-b5a8dadd51c94b82aa310f29`
- `parent_post_id`: `fb-post-1279427066957858`
- `pre_ai_status`: `ACCEPTED`
- `pre_ai_score`: `0.41`
- `pre_ai_reason`: `parent_context`

Content:

> `Hoa Xuong Rong Xin giá 34 tuần Trả lời`

Downstream label:

- `author_role = end_user`
- `content_intent = question`
- `commerciality_level = low`
- `user_feedback_relevance = high`

Interpretation:

- this is the strongest evidence that current logic is not aligned with the product goal
- the system treated a price inquiry as high-value user feedback
- this record later surfaced directly into the end-user theme output as `Xin giá`

#### Accepted comment D

- `post_id`: `fb-comment-ef7003ed68ee990df720e8bc`
- `parent_post_id`: `fb-post-1279427066957858`
- `pre_ai_status`: `ACCEPTED`
- `pre_ai_score`: `0.41`
- `pre_ai_reason`: `parent_context`

Content:

> `Hoa Xuong Rong 34 tuần Trả lời`

Downstream label:

- `author_role = end_user`
- `content_intent = experience`
- `commerciality_level = low`
- `user_feedback_relevance = medium`

Interpretation:

- this is not useful insight
- the text is too short and too context-thin to deserve accepted status
- parent context alone is currently carrying too much weight

### 6.3 Accepted comments that were actually duplicate promotion

Three accepted comments under accepted post A were not real customer feedback. They were effectively duplicated promotional payload:

- `fb-comment-92eafc220aa27df262f90c15`
- `fb-comment-174e145bb43e49103d05c842`
- `fb-comment-f70e0a9ab281e99ccb3b2b70`

All three were accepted with reasons built around:

- `anchor_hits`
- `related_hits`
- `parent_context`

But downstream labels show:

- `author_role = brand_official`
- `content_intent = promotion`
- `commerciality_level = high`
- `user_feedback_relevance = low`

Interpretation:

- comment expansion currently inherits too much trust from an accepted parent
- duplication and seller-side thread noise are not being penalized strongly enough at comment level

### 6.4 Representative uncertain records

Representative uncertain records were mostly repetitive seller/product posts such as:

- `fb-post-2224e9de5ecd2ad5c80e40c4`
- `fb-post-bf45ed24cd47eae3231fa7f1`
- `fb-post-36a5d34a4f6c3e5d43424bcc`
- `fb-post-0d8b8db8da318c1677852c54`

Typical characteristics:

- page/shop-like source
- repeated product promise language
- phrases such as `da dầu`, `mụn`, `cứu tinh`, `gửi tin nhắn`
- `pre_ai_reason = related_hits=2`

Interpretation:

- current uncertainty band still contains many commercial posts that are obviously low-value for end-user research
- this suggests `source_score` and commercial penalties are still too weak

### 6.5 Representative rejected records

Representative rejected records show the filter is already doing some useful work:

- raw agricultural `bột đậu xanh` posts were rejected as `weak_signal`
- explicit sales/order posts were rejected as `negative_hits=1`
- skincare shop posts with obvious sales patterns were also rejected

Examples:

- `fb-post-5f2397f185d121af5c1d6d51--c973315b04`
- `fb-post-25684625574460542`
- `fb-post-c224d99764796fb2c7a65023`
- `fb-post-1564327271001484`

Interpretation:

- the system is already blocking a meaningful amount of garbage
- the current problem is not "no filtering"
- the current problem is "the last 4 to 8 records that survive are still often the wrong records"

---

## 7. What Phase 7 Solved

### Solved well enough in this run

- dead search paths were stopped instead of being exhausted indefinitely
- comment crawl did not happen for step-1 and step-5 because those paths produced no accepted parents
- only `8` accepted records went to labeling instead of all `193`

### Evidence

- `161 / 193` records were rejected pre-AI
- step-1, step-5, and step-8 all stopped with clear weak-path reasons
- label job processed only `8` records

---

## 8. What Phase 7 Did Not Solve

### 8.1 Commercial topicality still passes as relevance

The accepted set still included:

- a brand page promotion
- a seller/affiliate post

This means the current deterministic gate still overweights topical lexical similarity and underweights commercial-source penalties.

### 8.2 Parent-aware comment scoring is too permissive

Comments like `Xin giá` and near-empty transactional replies were accepted because:

- the parent was already accepted
- short text did not get penalized enough
- transactional commerce intent was not blocked explicitly

### 8.3 Theme output can still look structurally correct while being product-useless

The theme pipeline returned exactly what the accepted and labeled set contained.

That is operationally correct, but product-wise wrong:

- the system returned `Xin giá` and `Ib`
- the end user wanted experiential pain points, objections, comparisons, or real reactions

### 8.4 Provider telemetry is still incomplete

The `crawled_posts` records for this run showed:

- `provider_used = null`
- `fallback_used = 0`

for all `193` records.

But label job data clearly shows a model was used:

- `model_name = claude-haiku-4-5`

Interpretation:

- provider/model execution is not yet persisted at the record level in a way that supports run-level forensic analysis

---

## 9. Root-Cause Analysis

### Root cause A - post scoring still treats commercial posts as valid topical evidence

Current accepted posts survived on combinations like:

- `anchor_hits=1, related_hits=1`
- `anchor_hits=1, related_hits=2`

That is not enough if the post also contains:

- product-claim language
- sales or CTA language
- usage instructions
- shipping or message-to-buy cues
- obvious page/store identity

### Root cause B - comment scoring is inheriting too much from the parent

`parent_context` is currently strong enough to let very weak comments pass:

- price inquiries
- `ib`
- nearly content-free thread fragments
- duplicated seller-side promotional replies

### Root cause C - the product goal and the acceptance logic are still misaligned

The product goal is to extract useful end-user signal.

The accepted set in this run still tolerated:

- buyer-intent signals
- promotional surface text
- duplicated commercial thread content

Those are not the same thing as end-user insight.

---

## 10. Concrete Improvement Directions For The Next Phase

### 10.1 Strengthen commercial-source penalties at post level

Add stronger negative weighting or direct rejection rules for signals such as:

- page/store identity
- `gửi tin nhắn`
- `giao hàng toàn quốc`
- price/stock/order phrasing
- usage instructions plus CTA
- heavy benefit-claim copywriting

Expected effect:

- prevent posts like the two accepted parents in this run from entering the accepted set

### 10.2 Split "buyer intent" from "user experience"

Do not treat the following as end-user insight by default:

- `xin giá`
- `ib`
- `check inbox`
- bare purchase interest

Expected effect:

- comments can still be preserved for commerce analytics if needed
- but they should not feed the end-user theme pipeline

### 10.3 Make parent-aware comment scoring conditional, not dominant

Suggested rule direction:

- parent acceptance can help a comment
- parent acceptance cannot rescue a comment that is too short, too transactional, duplicated, or commerce-only

Expected effect:

- comments like `Xin giá` stop polluting the accepted set

### 10.4 Add thread-role awareness in comment crawl

At comment level, separate:

- seller reply
- buyer inquiry
- real user experience
- duplicated thread summary

Expected effect:

- comments copied from the parent post or posted by the seller side get downgraded early

### 10.5 Add a "useful for end-user insight" gate before theme generation

Today, `end_user` plus medium or high relevance is still not enough.

Add a final insight-quality gate for theme generation that prefers:

- experience
- complaint
- comparison
- concrete outcome
- real question with user problem context

and excludes:

- pure buying intent
- pure pricing inquiry
- pure inbox handoff

Expected effect:

- end-user themes become materially closer to the product goal

---

## 11. Final Conclusion

`run-c973315b04` proves that Phase 7 is already reducing waste and enforcing real pre-AI gating.

It does not yet prove that the system can surface useful end-user insight on production traffic.

The strongest production evidence is simple:

- most records were rejected correctly
- the surviving accepted parents were still promotional
- comment expansion then elevated `Xin giá` and `Ib` into end-user themes

That is the next bar.

The next phase should not focus on more generic filtering volume. It should focus on one narrower question:

**How do we stop commercial topicality and transactional buyer intent from surviving as end-user insight?**

