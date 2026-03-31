# CP1 — Validity Spec Builder

**Code:** cp1-validity-spec-builder
**Order:** 1
**Depends On:** cp0-phase8-setup
**Estimated Effort:** 1 ngay

## Muc tieu

Build `validity_spec` tu full research context de thay vai tro source-of-truth cua lexical gate cu.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/planner.py` | modified | Compile research context thanh `validity_spec` |
| `backend/app/schemas/*.py` | modified | Schema cho `validity_spec` neu can |
| `backend/tests/*` | modified | Test cho shape va versioning cua spec |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co `validity_spec` shape ro rang, versioned | ✓ |
| CHECK-02 | Spec gom objective, target signals, hard reject signals, comment policy, batch policy | ✓ |
| CHECK-03 | Co persist hoac trace duoc spec theo run/context | ✓ |
