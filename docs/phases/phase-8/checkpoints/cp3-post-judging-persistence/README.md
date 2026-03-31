# CP3 — Post Judging + Persistence

**Code:** cp3-post-judging-persistence
**Order:** 3
**Depends On:** cp2-model-judge-adapter
**Estimated Effort:** 1 ngay

## Muc tieu

Dua `judge_result` vao flow post candidate, persist decision/score/confidence/reasons, va giu hard filter layer lam fast reject.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/runner.py` | modified | Tich hop post hard filter + model judge |
| `backend/app/models/*.py` | modified | Persist judge fields neu can |
| `backend/tests/*` | modified | Test cho flow post-level gating |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Post candidate qua hard filter roi moi den model judge | ✓ |
| CHECK-02 | Judge fields duoc persist va audit duoc | ✓ |
| CHECK-03 | Hard reject obvious garbage van ton tai | ✓ |
