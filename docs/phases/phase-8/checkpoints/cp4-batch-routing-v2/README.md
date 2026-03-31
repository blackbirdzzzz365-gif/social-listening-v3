# CP4 — Batch Routing V2

**Code:** cp4-batch-routing-v2
**Order:** 4
**Depends On:** cp3-post-judging-persistence
**Estimated Effort:** 1 ngay

## Muc tieu

Nang batch-level path control tu accepted-count lexical sang model-aware routing co `continue / reformulate / stop`.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/runner.py` | modified | Batch health V2 dua tren judge output |
| `backend/app/services/*` | modified | Confidence-aware metrics neu can |
| `backend/tests/*` | modified | Test cho continue / reformulate / stop |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Batch decision co `continue`, `reformulate`, `stop` | ✓ |
| CHECK-02 | Decision co the dung confidence-aware metric | ✓ |
| CHECK-03 | Co persist hoac audit duoc batch routing reason | ✓ |
