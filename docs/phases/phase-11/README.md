# Phase 11 - Provider-Resilient Planning And Image-Bearing Evidence Acquisition

## Why this phase exists

Phase 10 proved that the product can:

- keep runtime state and heartbeat trustworthy
- classify stuck-step failures clearly
- reach `ANSWER_READY` for a text-led case

Production still exposed two gaps:

- planner creation and clarification can fail on transient provider overload before the run even starts cleanly
- image-bearing topics can collect evidence inside a long-running browser step but still persist `0 records` if the step times out before candidate processing

Phase 11 closes those gaps so the system can survive provider turbulence and turn image-bearing retrieval into auditable evidence instead of a black hole.

## Locked direction

- Planner resilience is product scope, not just infra cleanup.
- Image-bearing topics need an explicit retrieval posture, not only generic search families.
- Timeout with live progress must leave an audit trail of what was collected, what was persisted, and what was lost.
- Phase 11 is only complete after a real image-bearing production case reaches one of:
  - `ANSWER_READY`
  - `NO_VISUAL_EVIDENCE`
  - `FAILED` with salvageable audit artifacts that explain exactly why

## Expected outcomes

- Session analysis, clarification submission, and plan generation degrade gracefully under transient provider overload.
- Planner APIs expose enough metadata to explain provider attempts, fallback, and final planner outcome.
- Image-bearing topics start with image-seeking query posture instead of generic product-term only posture.
- Long `SEARCH_POSTS` timeouts no longer erase collected-but-unpersisted evidence from the audit surface.
- Production audit can prove whether image fallback actually contributed to decisions.

## Scope

### In scope

- planner retry/fallback wrapper and failure taxonomy
- planner metadata persistence and API exposure
- image-first retrieval query families and planner hints
- timeout salvage and raw collection auditability for search steps
- Phase 11 production case pack and verdict workflow

### Out of scope

- reworking the full browser engine
- replacing deterministic gating with AI-first filtering
- broad UI redesign outside monitor and audit surfaces

## Success criteria

- Planner provider overload no longer appears to the user as a generic `400` or opaque `500`.
- At least one image-bearing production case leaves auditable evidence even if a search step times out.
- Production audit can answer:
  - did planning survive provider instability?
  - did image-bearing retrieval reach persistence and judging?
  - if not, exactly where evidence was lost
