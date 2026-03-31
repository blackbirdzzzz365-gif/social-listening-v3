# CP5 — Comment Policy Gating

**Code:** cp5-comment-policy-gating
**Order:** 5
**Depends On:** cp4-batch-routing-v2
**Estimated Effort:** 1 ngay

## Muc tieu

Sua comment gating de parent context khong con cuu nhung comment ngan, transactional-only, hoac seller-side noise trong end-user insight runs.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/comment_*` | modified/created | Comment-specific policy/judge helper |
| `backend/app/services/runner.py` | modified | Tich hop comment judge flow |
| `backend/tests/*` | modified | Test cho transactional comments va parent-context rules |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Comment policy tach rieng khoi post policy | ✓ |
| CHECK-02 | `Xin giá`, `ib`, va transactional-only comments co the bi chan | ✓ |
| CHECK-03 | Parent context khong duoc phep cuu comment qua yeu mot cach mac dinh | ✓ |
