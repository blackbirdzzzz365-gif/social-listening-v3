# CP7 — Smoke + Audit Gate

**Code:** cp7-phase8-smoke-audit
**Order:** 7
**Depends On:** cp6-image-ocr-fallback
**Estimated Effort:** 0.5-1 ngay

## Muc tieu

Chay smoke va audit cho Phase 8 de xac nhan valid set da sach hon, transactional comments da bi chan tot hon, va observability du cho production learning.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `docs/phases/phase-8/checkpoints/cp7-phase8-smoke-audit/DEMO_LOG.md` | created/updated | Log smoke va ket qua audit |
| `backend/tests/*` | modified | Smoke check neu co |
| runtime artifacts | generated | Run snapshots, judge audit, valid set sample |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co smoke run cho flow Phase 8 | ✓ |
| CHECK-02 | Co audit mau accepted / rejected / uncertain set sau model gating | ✓ |
| CHECK-03 | Co nhan xet ro ve improvement va residual gap | ✓ |
