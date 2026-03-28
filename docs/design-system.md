# Design System Guideline
# AI Facebook Social Listening & Engagement

**Version:** 1.0.0
**Updated:** 2026-03-28
**Status:** Living document — cập nhật theo từng sprint

---

## Table of Contents

1. [Principles](#1-principles)
2. [Architecture Overview](#2-architecture-overview)
3. [ProductContext System — AI Memory Layer](#3-productcontext-system--ai-memory-layer)
4. [Skill.md Specification](#4-skillmd-specification)
5. [Service Catalog](#5-service-catalog)
6. [API Design Conventions](#6-api-design-conventions)
7. [Event System](#7-event-system)
8. [Data Models](#8-data-models)
9. [Technology Stack](#9-technology-stack)
10. [Security & Compliance](#10-security--compliance)

---

## 1. Principles

### P1 — AI Assistant, Not Bot
Mọi write action lên Facebook đều phải có **human approval** trước khi execute.
Hệ thống draft, đề xuất, cảnh báo rủi ro — con người quyết định cuối cùng.
Không có auto-post, auto-comment, auto-DM.

> Rationale: Giảm rủi ro bị Facebook ban account. Phù hợp với PDP Law VN 2026.
> Nguồn: market-research.md — "AI assistant, not bot là kiến trúc an toàn nhất"

### P2 — Context Is Product-Scoped
Mọi AI interaction đều được enrich bởi **ProductContext** — bộ nhớ sống theo từng sản phẩm đang research.
Không có stateless AI call. Không có generic output.

### P3 — Skills Are Contracts
Mỗi service tương tác với AI model phải có `skill.md` định nghĩa đầy đủ:
role, context sections cần đọc/ghi, input schema, output schema.
Thay đổi AI behavior = thay đổi skill.md, không phải thay đổi code.

### P4 — Safety Gates Are Non-Negotiable
Ba điều không được bypass dù bất kỳ lý do gì:
- Human approval trước mọi write action
- Dừng toàn bộ write khi phát hiện CAPTCHA
- Không exceed rate limit đã cấu hình per action type

### P5 — Progressive Enrichment
ProductContext lớn dần theo thời gian. Mỗi AI call không chỉ trả kết quả
mà còn cập nhật context để call tiếp theo chính xác hơn.
Càng dùng nhiều → output càng personalized.

---

## 2. Architecture Overview

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│              Web App (React) / CLI / Desktop App                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                       API GATEWAY                               │
│         FastAPI · JWT Auth · Rate Limit · Request Routing       │
└────┬──────────┬──────────┬──────────┬──────────┬───────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
[Planner]  [Executor]  [Crawler]  [Content]  [Analytics]
 Service    Service     Service   Generator   Service
     │          │          │       Service       │
     └──────────┴──────────┴──────────┴──────────┘
                           │
              ┌────────────▼────────────┐
              │        EVENT BUS        │
              │    Redis Pub/Sub         │
              └────────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    [FB Session]    [Insight Engine]   [Lead Tracker]
     Manager         Service            Service
          │                │
          └────────────────┘
                    │
          ┌─────────▼─────────┐
          │  Context Assembler │   ← AI Memory Layer
          │  + Updater         │
          └─────────┬─────────┘
                    │
              Claude API
```

### Request Flow

```
User action
    ↓
API Gateway (auth + rate limit check)
    ↓
Service receives request
    ↓
Context Assembler loads ProductContext + renders skill prompt
    ↓
Claude API call
    ↓
Context Updater applies context_writes rules
    ↓
Service executes business logic
    ↓ (nếu là write action)
Engagement Service (human approval gate)
    ↓
FB Session Manager executes action on Facebook
    ↓
Audit Log emitted
    ↓
Notification Service broadcasts status via WebSocket
```

---

## 3. ProductContext System — AI Memory Layer

### Khái niệm

ProductContext là một **living document** gắn với một sản phẩm đang research
(ví dụ: "TPBank EVO"). Nó tích lũy knowledge qua từng AI interaction và được
inject vào system prompt của mọi Claude API call liên quan.

### Vòng đời

```
US-01: User nhập topic
    → Planner skill tạo product_profile + keyword_taxonomy (Layer 1)

US-04: Crawl + analyze posts
    → Insight skill populate insight_corpus + audience_personas (Layer 2)

US-06/07: Generate content, user approve
    → Content skill học brand_voice từ approved samples (Layer 3)

US-08b: Lead follow-up
    → Lead skill update lead_patterns từ interaction history (Layer 3)
```

### Schema

```json
{
  "product_id": "string (slug: tpbank-evo-2026-03)",
  "created_at": "ISO8601",
  "last_updated": "ISO8601",
  "sections": {

    "product_profile": {
      "name": "string",
      "category": "string",
      "target_audience": "string",
      "key_differentiators": ["string"],
      "competitors": ["string"],
      "research_intent": "string"
    },

    "keyword_taxonomy": {
      "brand": ["string"],
      "pain_points": ["string"],
      "sentiment_signals": ["string"],
      "vietnamese_variants": ["string"],
      "confirmed_at": "ISO8601",
      "user_edited": "boolean"
    },

    "group_intelligence": [
      {
        "group_id": "string",
        "name": "string",
        "member_count": "number",
        "dominant_tone": "string",
        "top_themes": ["string"],
        "posting_rules": "string",
        "best_content_angle": "personal_story | open_question | solution_framing",
        "avg_engagement_rate": "number"
      }
    ],

    "insight_corpus": {
      "total_posts_analyzed": "number",
      "last_updated": "ISO8601",
      "top_pain_points": [
        {
          "theme": "string",
          "frequency": "number (0-1)",
          "sample_quote": "string"
        }
      ],
      "sentiment_distribution": {
        "positive": "number",
        "negative": "number",
        "neutral": "number"
      },
      "emerging_themes": ["string"],
      "excluded_spam_count": "number"
    },

    "audience_personas": [
      {
        "label": "string",
        "description": "string",
        "trigger_phrases": ["string"],
        "approach": "string"
      }
    ],

    "brand_voice": {
      "tone": "string",
      "style": "string",
      "approved_patterns": ["string"],
      "forbidden_patterns": ["string"],
      "derived_from_approved_samples": "number"
    },

    "lead_patterns": {
      "high_intent_signals": ["string"],
      "cold_signals": ["string"],
      "follow_up_history_summary": "string"
    }
  }
}
```

### Section Priority (token budget)

Khi context vượt token budget, Context Assembler trim theo thứ tự ưu tiên:

| Priority | Section | Trimming Strategy |
|----------|---------|-------------------|
| 1 (luôn giữ) | `product_profile` | Không trim |
| 2 | `keyword_taxonomy` | Không trim |
| 3 | `brand_voice` | Giữ patterns, trim examples |
| 4 | `insight_corpus` | Chỉ giữ top 3 pain points + sentiment |
| 5 | `group_intelligence` | Chỉ giữ group đang target trong request |
| 6 | `audience_personas` | Chỉ giữ persona match với request |
| 7 (trim first) | `lead_patterns` | Giữ summary, bỏ full list |

**Max context tokens per AI call: 4,000 tokens** (giữ room cho input + output)

### Storage

```
PostgreSQL: product_contexts table
  - id, product_id, sections (JSONB), version, created_at, updated_at

Redis cache: context:{product_id}
  - TTL: 5 phút
  - Invalidate on write
```

---

## 4. Skill.md Specification

### File Location

```
services/
├── planner/
│   └── skill.md
├── insight-engine/
│   └── skill.md
├── content-generator/
│   └── skill.md
├── engagement/
│   └── skill.md
└── lead-tracker/
    └── skill.md
```

### Frontmatter Schema

```yaml
---
skill: string                    # unique skill identifier
version: semver                  # e.g. 1.0.0
model: claude-model-id           # default model cho skill này
context_reads:                   # ProductContext sections cần inject
  - section_name
context_writes:                  # sections skill này sẽ update sau response
  - section_name
---
```

### Body Sections (bắt buộc theo thứ tự)

```markdown
# [Skill Name]

## Role
[1 đoạn — Claude là ai trong context này, nhiệm vụ gì]
[Dùng {{product_profile.name}} để personalize nếu cần]

## System Prompt Template
[Jinja2 template — dùng {{section.field}} để inject context]
[Sections được inject theo context_reads trong frontmatter]

## Input Schema
[JSON schema của user message gửi vào Claude]

## Output Schema
[JSON schema của response mong đợi từ Claude]
[Luôn là valid JSON — không có free-form text response]

## Context Update Rules
[Mô tả cụ thể: khi nào update section nào, với data gì]
[Điều kiện trigger update, không phải update vô điều kiện]

## Fallback Behavior
[Xử lý khi context sections trống hoặc thiếu data]
```

### Quy ước đặt tên context variables

```
{{product_profile.name}}               → scalar field
{{keyword_taxonomy.brand | join(", ")}} → array → string
{{insight_corpus.top_pain_points | top(3)}} → filter/limit
{{group_intelligence | filter(group_id)}}   → filter by key
```

### Model Selection Guide

| Task Type | Model | Lý do |
|-----------|-------|-------|
| Research planning, content generation | `claude-sonnet-4-6` | Cần reasoning + creativity |
| Sentiment/theme classification | `claude-haiku-4-5` | High volume, cost-sensitive |
| Lead intent classification | `claude-haiku-4-5` | Real-time, latency-sensitive |
| Complex sales copy với nhiều constraints | `claude-sonnet-4-6` | Nhiều context sections |

### Versioning Rules

- **Patch (1.0.x):** Sửa wording, thêm ví dụ, tune output schema nhỏ
- **Minor (1.x.0):** Thêm/bỏ context_reads, thay đổi output schema có backwards compat
- **Major (x.0.0):** Thay đổi role, thay đổi context_writes behavior, breaking schema change

---

## 5. Service Catalog

### 5.1 AI Planner Service

**Mục đích:** US-01, US-02 — Topic → keyword taxonomy → research plan

**Skill:** `planner/skill.md`
**Context reads:** _(none — skill này khởi tạo context)_
**Context writes:** `product_profile`, `keyword_taxonomy`

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/planner/analyze` | Nhận topic → trả keywords hoặc clarifying questions |
| POST | `/planner/research-plan` | Nhận confirmed keywords → tạo research plan |
| PATCH | `/planner/research-plan/:id` | User chỉnh sửa plan steps |
| GET | `/planner/research-plan/:id` | Lấy plan hiện tại |

**State machine của Plan:**

```
DRAFT → PENDING_APPROVAL → APPROVED → EXECUTING → PAUSED → COMPLETED
                                                         ↘ FAILED
```

---

### 5.2 Plan Executor Service

**Mục đích:** US-03a, US-03b — Approve plan → execute → monitor

**Không có skill.md** — service này là orchestrator, không gọi AI trực tiếp

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/executor/:id/approve` | User approve steps đã chọn |
| POST | `/executor/:id/start` | Bắt đầu execution |
| POST | `/executor/:id/pause` | Pause sau step hiện tại |
| POST | `/executor/:id/resume` | Resume từ step dở |
| GET | `/executor/:id/status` | Poll status (fallback cho WebSocket) |
| WS | `/ws/executor/:id` | Realtime step updates |

**Step execution pattern:**

```
Executor dispatches step task → Redis Queue (Celery)
Worker picks up task → calls appropriate service
Service reports result → emits STEP_DONE/FAILED event
Executor receives event → updates step state → broadcasts via WS
```

**Step state machine:**

```
PENDING → RUNNING → DONE
                 ↘ FAILED → [Retry | Skip | Stop]
                 ↘ SKIPPED
```

**Recovery on restart:**
- Checkpoint cuối của mỗi step được lưu vào DB với timestamp
- Khi app restart và phát hiện plan EXECUTING → load checkpoint → hỏi user resume/cancel

---

### 5.3 Facebook Session Manager

**Mục đích:** Cross-cutting — quản lý Playwright browser session, serialize tất cả FB actions

**Không có skill.md** — service infrastructure, không gọi AI

**Singleton pattern:** Chỉ 1 browser instance active tại một thời điểm

**Action Types và Rate Limits (defaults, configurable per user):**

| Action Type | Default Limit | Window |
|-------------|--------------|--------|
| `READ_POST` | 30 | per minute |
| `READ_COMMENT` | 20 | per minute |
| `SEARCH_KEYWORD` | 10 | per minute |
| `JOIN_GROUP` | 5 | per day |
| `WRITE_POST` | 3 | per day per group |
| `WRITE_COMMENT` | 20 | per day |
| `WRITE_FOLLOW_UP` | 1 | per lead per day |

**CAPTCHA Detection Protocol:**
1. Phát hiện CAPTCHA → emit `CAPTCHA_DETECTED` event ngay lập tức
2. Set `session:captcha_flag = true` trong Redis
3. Reject tất cả pending write actions với HTTP 503
4. Alert user qua WebSocket: "Phát hiện CAPTCHA — toàn bộ write action đã bị dừng"
5. Không tự động retry — chờ user xử lý thủ công

**Delay Injection:**

```python
# Inject trước mỗi action để mô phỏng hành vi người thật
READ_ACTION:  random.uniform(0.5, 2.0)   # seconds
WRITE_ACTION: random.uniform(30, 120)    # seconds
FOLLOW_UP:    random.uniform(45, 90)     # seconds
```

---

### 5.4 Crawler Service

**Mục đích:** US-04, US-05 — Crawl posts từ group feed, search by keyword, crawl comments

**Không có skill.md** — service này thu thập data, không phân tích

**Refactor từ:** `fb_crawler.py`, `fb_search.py`, `fb_search_batch.py`, `fb_join_groups.py`

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/crawler/search` | Search posts by keyword |
| POST | `/crawler/groups/:id/posts` | Crawl post feed của group |
| POST | `/crawler/posts/:id/comments` | Crawl comments + nested replies |
| GET | `/crawler/jobs/:job_id` | Progress của crawl job |

**Resumable crawl:** Lưu cursor (last seen `post_id` hoặc `comment_id`) vào DB.
Nếu job bị interrupt → resume từ cursor, không crawl lại từ đầu.

**PII Masking (US-05 requirement):**
Áp dụng trước khi lưu vào DB:

```python
PII_PATTERNS = {
    "phone":  r"(\+84|0)[0-9]{9,10}",
    "cccd":   r"\b\d{9}\b|\b\d{12}\b",
    "email":  r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
}
# Replace matched patterns với "***"
```

**Comment Volume Warning (US-05):**
Nếu post có hơn 500 comments → trước khi crawl, hỏi user:
`{ "warning": "...", "estimated_time": "~15 phút", "options": ["crawl_all", "limit_500", "cancel"] }`

---

### 5.5 Insight Engine Service

**Mục đích:** US-04, US-05 — Phân tích sentiment, theme, spam cho posts/comments

**Skill:** `insight-engine/skill.md`
**Model:** `claude-haiku-4-5` (cost optimization)
**Context reads:** `product_profile`, `keyword_taxonomy`, `insight_corpus`
**Context writes:** `insight_corpus`, `audience_personas`

**Refactor từ:** `extract_customer_feedback.py`

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/insights/analyze/posts` | Batch analyze posts (async job) |
| POST | `/insights/analyze/comments` | Analyze comment thread |
| GET | `/insights/summary/:crawl_id` | Top themes + sentiment + key quotes |
| GET | `/insights/jobs/:job_id` | Progress của analyze job |
| GET | `/insights/export/:crawl_id` | Download CSV |

**Batch Processing:**
- Chunk size: 20 posts per Claude API call (balance latency vs cost)
- Process async via Celery — notify qua WebSocket khi xong
- Emit `INSIGHT_BATCH_DONE` event sau mỗi chunk → Executor có thể hiển thị progress

**CSV Export Schema:**

```
post_url, author_id, theme, sentiment, relevance_score,
key_quote, date, is_spam, group_id, product_id
```

---

### 5.6 Content Generator Service

**Mục đích:** US-06, US-07, US-08a — Generate posts, comments, sales content

**Skill:** `content-generator/skill.md`
**Model:** `claude-sonnet-4-6`
**Context reads:** `product_profile`, `insight_corpus`, `group_intelligence`, `brand_voice`, `audience_personas`
**Context writes:** `brand_voice` (khi user approve một variant)

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/content/posts/generate` | Tạo 3 variants post |
| POST | `/content/comments/suggest` | Đề xuất 2-3 comment variants |
| POST | `/content/sales-posts/generate` | Tạo soft-sell post với 3 angles |
| POST | `/content/:id/approve` | User approve variant → update brand_voice |

**Content Angles (US-08a):**

| Angle | Mô tả | Khi dùng |
|-------|--------|----------|
| `personal_story` | Chia sẻ trải nghiệm cá nhân | Group có dominant_tone: conversational |
| `open_question` | Câu hỏi kéo thảo luận | Group muốn engagement |
| `solution_framing` | Tư vấn giải pháp cho pain point | Group có nhiều frustrated users |

**Sales Post Hard Limits:**
- Không quá 300 từ per variant
- Phải reference ít nhất 1 pain point từ `insight_corpus`
- Nếu group có `posting_rules: no_direct_ads` → auto-chọn angle ít sales-y + thêm warning

**Brand Voice Learning:**
Mỗi khi user approve một variant:
1. Extract tone patterns từ approved content
2. Append vào `brand_voice.approved_patterns`
3. Update `derived_from_approved_samples` counter
4. Sau 5+ approved samples → brand_voice đủ tin cậy để dùng làm primary reference

---

### 5.7 Engagement Service

**Mục đích:** US-06, US-07, US-08b — Execute write actions lên Facebook với human approval gate

**Không có skill.md** — service này không gọi AI, chỉ execute approved actions

**Hard Rules — không được thay đổi:**

1. Mọi request phải có `human_approved: true` trong body
2. `human_approved` phải được set bởi explicit user action (button click) — không set programmatically
3. Delay inject bắt buộc theo loại action (xem FB Session Manager)
4. Kiểm tra `session:captcha_flag` trước mỗi write — nếu `true` → reject 503
5. Rate limit check trước mỗi write — nếu vượt → reject 429 với thời gian wait

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/engage/posts` | Đăng bài lên group |
| POST | `/engage/comments` | Đăng comment |
| POST | `/engage/follow-up/:lead_id` | Đăng follow-up reply |

**Request Schema (tất cả write endpoints):**

```json
{
  "content": "string",
  "target_id": "string (group_id hoặc post_id)",
  "human_approved": true,
  "approved_at": "ISO8601",
  "approved_variant_id": "string"
}
```

**Audit Log Entry (emitted sau mỗi action):**

```json
{
  "action_type": "WRITE_POST | WRITE_COMMENT | WRITE_FOLLOW_UP",
  "target_id": "string",
  "content_hash": "string (SHA256, không lưu full content nếu sensitive)",
  "result": "SUCCESS | FAILED | RATE_LIMITED | CAPTCHA",
  "error_message": "string | null",
  "timestamp": "ISO8601",
  "delay_applied_ms": "number"
}
```

---

### 5.8 Lead Tracker Service

**Mục đích:** US-08b — Classify lead intent, manage follow-up queue

**Skill:** `lead-tracker/skill.md`
**Model:** `claude-haiku-4-5`
**Context reads:** `product_profile`, `lead_patterns`, `audience_personas`
**Context writes:** `lead_patterns`

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/leads` | List leads với filter (Hot/Warm/Cold) |
| GET | `/leads/:id/timeline` | Full interaction history |
| POST | `/leads/:id/classify` | Classify new comment từ lead |
| POST | `/leads/:id/mark-cold` | Manual override |

**Lead Status Machine:**

```
NEW_COMMENT
    ↓ classify
INTERESTED (Hot) → follow-up suggested → approved → replied
NEUTRAL    (Warm) → monitor only
NEGATIVE   → no action

After 3 follow-ups without positive response:
    → Cold Lead → suppress 14 days
```

**Rate Limits (per lead):**
- Maximum 1 follow-up reply per lead per day
- Maximum 3 follow-up attempts total before auto-cold
- Cold leads: suppress for 14 days, không suggest follow-up

---

### 5.9 Analytics Service

**Mục đích:** US-08c — Sales tracking dashboard, read-only reporting

**Không có skill.md** — service này aggregate data, không gọi AI

**Endpoints:**

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/analytics/dashboard` | Aggregate metrics (5-min cache) |
| GET | `/analytics/by-group` | Group ranking by engagement |
| GET | `/analytics/by-content-type` | Compare 3 content angles |
| GET | `/analytics/export` | CSV export |

**Dashboard Metrics:**

```json
{
  "total_posts": "number",
  "total_reactions": "number",
  "total_comments": "number",
  "leads_identified": "number",
  "leads_followed_up": "number",
  "reply_rate": "number (0-1)",
  "by_group": [...],
  "by_content_type": [...],
  "last_refreshed": "ISO8601"
}
```

**Refresh Strategy:** Materialized view trong PostgreSQL, refresh mỗi 5 phút via cron.
Không có real-time streaming ở MVP.

---

### 5.10 Notification Service

**Mục đích:** Cross-cutting — Realtime alerts và status updates

**Không có skill.md**

**WebSocket Topics:**

| Topic | Payload | Trigger |
|-------|---------|---------|
| `plan.step.updated` | `{step_id, status, actual_count}` | Mỗi step thay đổi trạng thái |
| `plan.completed` | `{summary}` | Plan execution xong |
| `alert.captcha` | `{timestamp}` | CAPTCHA phát hiện |
| `alert.rate_limit` | `{action_type, resume_at}` | Rate limit reached |
| `alert.step_failed` | `{step_id, error, options}` | Step thất bại |
| `lead.new_interested` | `{lead_id, commenter_name}` | New Interested comment detected |

**Persistence:** Notifications lưu vào DB với `is_read` flag.
Khi user mở app → load unread notifications → mark as read.

---

## 6. API Design Conventions

### Request Format

```
Base URL: /api/v1
Auth:     Authorization: Bearer {jwt_token}
Content:  Content-Type: application/json
```

### Response Envelope

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "product_id": "string | null"
  }
}
```

### Error Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RATE_LIMITED | CAPTCHA_DETECTED | APPROVAL_REQUIRED | ...",
    "message": "Human-readable message",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP | Mô tả |
|------|------|--------|
| `APPROVAL_REQUIRED` | 403 | Write action không có `human_approved: true` |
| `CAPTCHA_DETECTED` | 503 | Session bị CAPTCHA, mọi write bị block |
| `RATE_LIMITED` | 429 | Vượt rate limit, include `retry_after` trong details |
| `CONTEXT_EMPTY` | 422 | ProductContext chưa có đủ data để thực hiện skill |
| `SESSION_EXPIRED` | 401 | Facebook session hết hạn, cần re-login |
| `PLAN_NOT_FOUND` | 404 | Plan ID không tồn tại |
| `STEP_DEPENDENCY` | 422 | Bỏ step này sẽ break dependency (include warning) |

### Async Jobs

Các operation dài (crawl, analyze batch) trả về job reference ngay:

```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "status": "QUEUED",
    "estimated_duration_seconds": 120,
    "websocket_topic": "plan.step.updated"
  }
}
```

Client poll `GET /jobs/:id` hoặc subscribe WebSocket để nhận updates.

---

## 7. Event System

### Event Bus: Redis Pub/Sub

**Topic naming:** `{domain}.{entity}.{action}`

```
plan.step.started
plan.step.completed
plan.step.failed
plan.execution.paused
plan.execution.completed

crawl.batch.completed
insight.batch.analyzed
content.variant.approved

lead.comment.detected
lead.status.changed

session.captcha.detected
session.rate_limit.reached
```

### Event Payload Schema

```json
{
  "event_id": "uuid",
  "topic": "string",
  "product_id": "string",
  "timestamp": "ISO8601",
  "payload": {}
}
```

### Event Consumers

| Topic | Consumer Service |
|-------|-----------------|
| `plan.step.*` | Notification Service → WebSocket |
| `crawl.batch.completed` | Insight Engine (trigger analyze) |
| `insight.batch.analyzed` | Context Updater (update insight_corpus) |
| `content.variant.approved` | Context Updater (update brand_voice) |
| `lead.comment.detected` | Lead Tracker (trigger classify) |
| `session.captcha.detected` | Engagement Service (block writes) + Notification |

---

## 8. Data Models

### Core Tables (PostgreSQL)

```sql
-- Sản phẩm đang research
CREATE TABLE products (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         VARCHAR(100) UNIQUE NOT NULL,  -- "tpbank-evo-2026-03"
  name         VARCHAR(200) NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ProductContext document
CREATE TABLE product_contexts (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id   UUID REFERENCES products(id),
  sections     JSONB NOT NULL DEFAULT '{}',
  version      INTEGER NOT NULL DEFAULT 1,
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Research plans
CREATE TABLE plans (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id   UUID REFERENCES products(id),
  topic        TEXT NOT NULL,
  steps        JSONB NOT NULL DEFAULT '[]',  -- array of step objects
  status       VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Crawled posts
CREATE TABLE posts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID REFERENCES products(id),
  fb_post_id      VARCHAR(100) NOT NULL,
  group_id        VARCHAR(100),
  content         TEXT,
  author_id       VARCHAR(100),
  theme           VARCHAR(100),
  sentiment       VARCHAR(20),
  relevance_score DECIMAL(3,2),
  is_spam         BOOLEAN DEFAULT FALSE,
  key_quote       TEXT,
  post_url        TEXT,
  fb_timestamp    TIMESTAMPTZ,
  crawled_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Leads và interaction history
CREATE TABLE leads (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID REFERENCES products(id),
  fb_user_id      VARCHAR(100) NOT NULL,
  commenter_name  VARCHAR(200),
  status          VARCHAR(20) NOT NULL DEFAULT 'NEW',  -- Hot/Warm/Cold/New
  follow_up_count INTEGER DEFAULT 0,
  last_interaction TIMESTAMPTZ,
  cold_until      TIMESTAMPTZ,
  source_post_id  UUID REFERENCES posts(id)
);

-- Audit log (append-only)
CREATE TABLE audit_logs (
  id           BIGSERIAL PRIMARY KEY,  -- sequential, không dùng UUID
  product_id   UUID,
  service      VARCHAR(50) NOT NULL,
  action_type  VARCHAR(100) NOT NULL,
  target_id    VARCHAR(200),
  result       VARCHAR(50) NOT NULL,
  error_msg    TEXT,
  payload      JSONB,
  timestamp    TIMESTAMPTZ DEFAULT NOW()
);
-- Không có UPDATE/DELETE trên bảng này
```

---

## 9. Technology Stack

### Core Stack

| Layer | Technology | Lý do |
|-------|-----------|-------|
| Language | Python 3.11+ | Giữ nguyên stack hiện tại |
| Web Framework | FastAPI | Async native, WebSocket support, auto OpenAPI docs |
| Task Queue | Celery + Redis | Async jobs, retry logic, scheduling |
| Browser Automation | Playwright | Giữ nguyên, battle-tested với FB |
| Database | PostgreSQL 15+ | JSONB cho ProductContext, mature ecosystem |
| Cache / Event Bus | Redis 7+ | Pub/Sub + token bucket rate limiting + job queue |
| AI SDK | `anthropic` Python SDK | Official SDK, streaming support |
| Template Engine | Jinja2 | Render skill.md system prompt templates |

### Service Framework Pattern

Mỗi service follow pattern:

```
service-name/
├── skill.md              # AI contract (nếu service gọi AI)
├── main.py               # FastAPI app
├── router.py             # Endpoints
├── service.py            # Business logic
├── context.py            # Context assembly/update logic
├── schemas.py            # Pydantic input/output schemas
├── worker.py             # Celery tasks (nếu có async jobs)
└── tests/
    ├── test_service.py
    └── test_context.py
```

### Context Assembler — Shared Library

```
libs/
└── context_assembler/
    ├── assembler.py      # Build system prompt từ skill.md + ProductContext
    ├── updater.py        # Apply context_writes rules sau AI response
    ├── token_budget.py   # Section trimming/prioritization
    └── skill_loader.py   # Parse skill.md frontmatter + template
```

Import vào bất kỳ service nào cần gọi AI:

```python
from libs.context_assembler import ContextAssembler, ContextUpdater

assembler = ContextAssembler(skill_path="./skill.md")
request = assembler.build(product_id=product_id, user_input=input_data)
response = claude_client.messages.create(**request)
ContextUpdater(skill_path="./skill.md").apply(product_id, response)
```

### Development Setup

```
docker-compose.yml
├── postgres:15
├── redis:7
├── api-gateway      (port 8000)
├── planner          (port 8001)
├── executor         (port 8002)
├── fb-session       (port 8003) — Playwright cần non-headless trong dev
├── crawler          (port 8004)
├── insight-engine   (port 8005)
├── content-gen      (port 8006)
├── engagement       (port 8007)
├── lead-tracker     (port 8008)
├── analytics        (port 8009)
└── notification     (port 8010)
```

---

## 10. Security & Compliance

### PDP Law VN 2026 Compliance

- **Không lưu tên thật** của Facebook users — chỉ lưu `fb_user_id` (opaque ID)
- **PII masking bắt buộc** trước khi lưu: phone, CCCD, email (xem Crawler Service)
- **Data retention:** Crawled data xóa sau 90 ngày mặc định (configurable)
- **Export:** CSV export không bao gồm `author_id` nếu user không explicitly opt-in

### Facebook Session Security

- Session files (`fb-session/`) không được commit vào git (đã có trong `.gitignore`)
- Session files mã hóa at rest bằng AES-256 với key từ environment variable
- Không log session cookies vào stdout hoặc file log

### API Security

- JWT authentication với expiry 24h
- Rate limiting tại API Gateway: 100 requests/minute per token
- Input validation với Pydantic trên tất cả endpoints
- SQL injection: sử dụng parameterized queries, không string interpolation

### Audit Trail

- Mọi write action lên Facebook có audit log entry
- Audit log là append-only — không có UPDATE/DELETE
- Log retention: 1 năm
- Log export available để debug và compliance review

### Secrets Management

```bash
# .env (không commit)
ANTHROPIC_API_KEY=sk-ant-...
FB_SESSION_ENCRYPTION_KEY=...
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=...
```

---

## Appendix: Migration Path từ Scripts Hiện Tại

| File hiện tại | → Service | Sprint |
|---------------|-----------|--------|
| `fb_login.py` | FB Session Manager (session init) | Sprint 1 |
| `fb_search.py` | Crawler Service (search crawl) | Sprint 2 |
| `fb_crawler.py` | Crawler Service (group feed crawl) | Sprint 2 |
| `fb_search_batch.py` | Plan Executor (batch orchestration) | Sprint 1 |
| `fb_join_groups.py` | Crawler Service (join group action) | Sprint 2 |
| `extract_customer_feedback.py` | Insight Engine (spam filter + classification) | Sprint 2 |

**Migration strategy:** Wrap scripts hiện tại trong FastAPI endpoints trước
(tạo thin service layer), sau đó refactor internal logic sang clean architecture.
Không rewrite toàn bộ trong một lần.
