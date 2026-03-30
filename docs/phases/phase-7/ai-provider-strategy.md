# AI Provider Strategy - Phase 7
## Locked AI Routing Policy Feeding Phase 8

**Status:** Locked cross-cutting strategy  
**Updated:** 2026-03-31

---

## 1. Purpose

This document is part of the same Phase 7 cost-control story as retrieval gating.

Phase 7 reduces bad records before AI.  
This AI provider strategy governs how the smaller, better record set should use AI:

- `chiasegpu` is the default provider for all AI touchpoints
- Claude is fallback only
- provider selection lives inside `AIClient`, not inside business services

This keeps provider routing separate from retrieval, labeling, and theme logic.

---

## 2. Current-State Fit With The Codebase

The current backend already has the right structural direction:

- `AIClient` is the central call path
- config already points the OpenAI-compatible base URL to `https://llm.chiasegpu.vn/v1`
- Anthropic is already present as a fallback-capable client

What still needs to be locked for Phase 8:

- broader and explicit fallback rules
- explicit provider telemetry
- no accidental fallback for deterministic system bugs

---

## 3. Locked Direction

### D-80 - Primary provider

All AI interactions should use `chiasegpu` first.

Applies to:

- keyword analysis
- clarification flow
- plan generation
- plan refinement
- step explanation
- content labeling
- theme analysis
- JSON repair

### D-81 - Fallback provider

Claude is fallback only. It is not a peer primary provider.

### D-82 - Central routing only

Business services must not choose providers directly.

Services pass only:

- `model`
- `system_prompt`
- `user_input`
- `thinking`
- `stream`

`AIClient` decides:

- which provider to call
- whether to retry
- whether fallback is allowed

### D-83 - No blind fallback for deterministic bugs

The system must not auto-fallback to Claude for:

- invalid payload shape
- unsupported model configuration
- prompt/schema contract bugs
- deterministic validation failures after a valid provider response

The reason is simple:

- fallback would hide product bugs
- fallback would double cost without improving correctness

---

## 4. Allowed Fallback Triggers

Fallback is allowed only after a primary attempt and retryable failure handling.

Allowed failure classes:

- timeout
- network or transport failure
- HTTP 429
- HTTP 5xx
- empty response body
- invalid provider envelope such as missing `choices`, `message`, or text content
- JSON repair failure caused by the same provider/runtime failure class

Not allowed:

- HTTP 4xx except `429`
- invalid request payload
- prompt design or schema design defects
- business validation failure after a syntactically valid response

---

## 5. Routing Flow

```text
service call
   |
   v
AIClient
   |
   +--> primary attempt: chiasegpu
   |
   +--> retry once if retryable provider/runtime failure
   |
   +--> fallback attempt: Claude if retryable failure persists
   |
   +--> hard failure if fallback also fails
```

---

## 6. Required Telemetry

Every AI interaction should make provider usage auditable.

Minimum fields:

- `provider_used`
- `fallback_used`
- `primary_model`
- `fallback_model`
- `attempt_count`
- `failure_reason`
- `service_name`

This metadata may initially live in internal logs/metrics instead of public API response contracts.

---

## 7. Phase 8 Implementation Guidance

### AIClient changes

Phase 8 should introduce:

- explicit exception classes for retry/fallback decisions
- a single predicate that determines retryable provider failure
- provider metadata logging on every call

### Config expectations

Config should continue to treat:

- `openai_compatible_base_url` as the primary provider endpoint
- `anthropic_fallback_model` as fallback-only configuration

### Service-layer expectations

No service should branch on provider name.  
No service should instantiate provider SDKs directly.

---

## 8. Relation To Retrieval Quality Gating

Phase 7 has two cost-control layers:

### Layer 1 - Do not send weak records to AI

This is enforced by:

- deterministic relevance scoring
- batch gating
- selective expansion
- clean payload builder

### Layer 2 - Use AI through one explicit provider policy

This is enforced by:

- `chiasegpu` primary routing
- Claude fallback only for allowed failure classes
- provider telemetry for audit and tuning

These two layers belong to the same system design and should ship together in Phase 8.

---

## 9. Final Policy Summary

The product should behave as follows:

- retrieve broadly
- reject weak records before AI
- send only gated records to AI
- call `chiasegpu` first
- fallback to Claude only when provider/runtime failure makes that necessary
- record enough metadata to explain cost and reliability later
