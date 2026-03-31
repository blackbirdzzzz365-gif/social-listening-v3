# CP2 — Answer Closeout Orchestration

**Code:** cp2-answer-closeout-orchestration
**Order:** 2
**Depends On:** cp1-browser-run-safety
**Estimated Effort:** 1 ngay

## Muc tieu

Sau khi label job xong va co accepted evidence, he thong phai tu dong di tiep sang theme/insight synthesis de run ket thuc bang answer-ready outcome thay vi dung lai o labels.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/label_job_service.py` | modified | Trigger closeout khi label xong |
| `backend/app/services/insight.py` | modified | Idempotent theme/insight synthesis |
| `backend/app/services/*` | created | Run closeout orchestrator neu can |
| `backend/app/models/*` | modified | Answer status / timestamps neu can |
| `backend/tests/*` | modified | Test tu accepted evidence -> label -> theme/answer |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Label job xong co the auto trigger theme/insight | ✓ |
| CHECK-02 | Closeout idempotent va retry duoc | ✓ |
| CHECK-03 | Run co answer-level terminal outcome hoac equivalent state | ✓ |
