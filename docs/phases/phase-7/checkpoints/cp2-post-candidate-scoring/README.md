# CP2 — Post Candidate Scoring

**Code:** cp2-post-candidate-scoring
**Order:** 2
**Depends On:** cp1-retrieval-profile-builder
**Estimated Effort:** 1 ngay

## Muc tieu

Mo rong persistence path tren `crawled_posts` de luu pre-AI state va implement deterministic relevance scoring cho post candidates.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/alembic/versions/*` | created | Migration them pre-AI fields cho `crawled_posts` |
| `backend/app/models/crawled_post.py` | modified | Model fields cho `pre_ai_status`, score, reason, query/source metadata |
| `backend/app/services/*` | modified | Relevance engine cho post candidates |
| `backend/tests/*` | modified | Tests cho scoring va persistence |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | `crawled_posts` co pre-AI fields toi thieu cho scoring va query/source context | ✓ |
| CHECK-02 | Engine tra ve `ACCEPTED`, `REJECTED`, `UNCERTAIN` voi score/reason | ✓ |
| CHECK-03 | Co test hoac smoke check cho post scoring logic | ✓ |
