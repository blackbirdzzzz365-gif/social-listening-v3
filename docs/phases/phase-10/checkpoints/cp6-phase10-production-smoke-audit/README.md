# CP6 — Phase 9 Production Smoke + Audit

**Code:** cp6-phase9-production-smoke-audit
**Order:** 6
**Depends On:** cp4-reason-aware-reformulation, cp5-vision-validation-harness
**Estimated Effort:** 0.5-1 ngay

## Muc tieu

Dong phase bang production-like validation: run safety, answer completion, routing uplift, reformulation that, va vision evidence duoc kiem tra tai cung mot bo smoke/audit.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `reports/phase-9/*` | created | Smoke artifacts, snapshots, analysis logs |
| `docs/phases/phase-9/checkpoints/cp6-phase9-production-smoke-audit/*` | modified | Result, validation, demo log |
| `backend/tests/*` | modified | Neu can them smoke helpers |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co bang chung run safety va answer delivery chay dung | ✓ |
| CHECK-02 | Co production evidence cho routing / reformulation uplift hoac ket luan chi tiet vi sao chua dat | ✓ |
| CHECK-03 | Co closeout note cho huong phase tiep theo | ✓ |
