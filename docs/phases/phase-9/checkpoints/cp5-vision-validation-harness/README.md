# CP5 — Vision Validation Harness

**Code:** cp5-vision-validation-harness
**Order:** 5
**Depends On:** cp2-answer-closeout-orchestration
**Estimated Effort:** 1 ngay

## Muc tieu

Tao validation track rieng cho image-bearing records de chung minh OCR / vision fallback co gia tri that, thay vi chi ton tai tren code.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/tests/*` | modified | Fixture/scenario cho image-bearing records |
| `backend/app/services/research_gating.py` | modified | Metrics, audit hooks, trigger conditions neu can |
| `docs/phases/phase-9/*` | modified | Validation scenarios va expected signals |
| `reports/*` | created | Validation artifacts khi smoke chay |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co bo validation scenarios cho image-bearing cases | ✓ |
| CHECK-02 | Co metric cho trigger va outcome cua image understanding | ✓ |
| CHECK-03 | Co it nhat 1 case chung minh image understanding thay doi hoac xac nhan decision | ✓ |
