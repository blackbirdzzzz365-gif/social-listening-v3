# CP1 — Retrieval Profile Builder

**Code:** cp1-retrieval-profile-builder
**Order:** 1
**Depends On:** cp0-phase7-setup
**Estimated Effort:** 1 ngay

## Muc tieu

Tao `retrieval_profile` lam foundation cho Phase 7, gom anchor clusters, related terms, negative patterns, query families, va source hints de retrieval khong phu thuoc vao 1 query don le.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/planner.py` | modified | Them output retrieval profile / query family metadata |
| `backend/app/schemas/*.py` | modified | Schema cho retrieval profile neu can |
| `backend/tests/*` | modified | Test cho retrieval profile shape va query-family generation |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co shape ro rang cho `anchors`, `related_terms`, `negative_terms`, `query_families`, `source_hints` | ✓ |
| CHECK-02 | Query families gom it nhat brand, pain_point, question, comparison, complaint | ✓ |
| CHECK-03 | Co test hoac smoke check cho retrieval profile generation | ✓ |
