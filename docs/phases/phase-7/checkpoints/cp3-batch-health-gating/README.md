# CP3 — Batch Health Gating

**Code:** cp3-batch-health-gating
**Order:** 3
**Depends On:** cp2-post-candidate-scoring
**Estimated Effort:** 1 ngay

## Muc tieu

Implement query-level gating theo batch 20 posts de stop som query/source path yeu va chi tiep tuc crawl nhung path co accepted ratio hop ly.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/runner.py` | modified | Loop batch 20 posts va continue/stop path logic |
| `backend/app/services/*` | modified | Batch health evaluator va retrieval path state |
| `backend/tests/*` | modified | Tests cho weak-batch stop va healthy-batch continue |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co logic fetch/scored/evaluate theo batch ~20 posts | ✓ |
| CHECK-02 | Co metrics toi thieu `accepted_ratio`, `uncertain_ratio`, `strong_accept_count` | ✓ |
| CHECK-03 | Co stop rule cho 2 consecutive weak batches hoac equivalent config | ✓ |
