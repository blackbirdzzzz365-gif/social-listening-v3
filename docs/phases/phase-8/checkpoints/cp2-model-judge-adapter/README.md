# CP2 — Model Judge Adapter

**Code:** cp2-model-judge-adapter
**Order:** 2
**Depends On:** cp1-validity-spec-builder
**Estimated Effort:** 1 ngay

## Muc tieu

Tao adapter goi model API de judge post/comment theo `validity_spec`, co output contract on dinh va kha nang doi provider/model sau nay.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/infra/*` | modified | Judge adapter, response normalization, retry/failure path |
| `backend/app/services/*` | modified | Runtime entrypoint cho model judge |
| `backend/tests/*` | modified | Test cho parsing, schema, error handling |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co adapter interface tach biet khoi business service | ✓ |
| CHECK-02 | Output co decision, relevance_score, confidence_score, reason_codes | ✓ |
| CHECK-03 | Co normalize loi/request schema failure va khong lam vo runner | ✓ |
