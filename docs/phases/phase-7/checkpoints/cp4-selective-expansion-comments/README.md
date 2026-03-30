# CP4 — Selective Expansion + Comment Scoring

**Code:** cp4-selective-expansion-comments
**Order:** 4
**Depends On:** cp3-batch-health-gating
**Estimated Effort:** 1 ngay

## Muc tieu

Chi crawl comments cho posts duoc phep va score comments bang parent context de ngan chi phi crawl/AI tren cac thread yeu.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/runner.py` | modified | Selective expansion policy truoc crawl comments |
| `backend/app/services/*` | modified | Comment scorer co parent context |
| `backend/tests/*` | modified | Tests cho accepted/uncertain/rejected expansion va comment scoring |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | `REJECTED` post khong crawl comments | ✓ |
| CHECK-02 | `ACCEPTED` post duoc crawl comments theo budget/policy | ✓ |
| CHECK-03 | Comment scoring dung parent context va co test cho case ngan nhu "minh cung bi vay" | ✓ |
