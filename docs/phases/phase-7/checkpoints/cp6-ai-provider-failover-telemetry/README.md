# CP6 — AI Provider Failover + Telemetry

**Code:** cp6-ai-provider-failover-telemetry
**Order:** 6
**Depends On:** cp5-clean-payload-ai-guardrail
**Estimated Effort:** 0.5-1 ngay

## Muc tieu

Khoa provider routing trong `AIClient`: `chiasegpu` la primary, Claude chi la fallback, co retry/failover predicate ro rang va telemetry de audit.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/infra/ai_client.py` | modified | Retry/failover policy, exception typing, provider metadata |
| `backend/app/infrastructure/config.py` | modified | Config neu can cho provider routing / telemetry |
| `backend/tests/*` | modified | Tests cho fallback allowed vs not allowed |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | `chiasegpu` la duong goi dau tien cho moi AI touchpoint | ✓ |
| CHECK-02 | Claude chi fallback cho retryable provider/runtime failures | ✓ |
| CHECK-03 | Co provider telemetry toi thieu: provider_used, fallback_used, failure_reason | ✓ |
