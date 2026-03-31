# CP4 — Reason-Aware Reformulation

**Code:** cp4-reason-aware-reformulation
**Order:** 4
**Depends On:** cp3-yield-aware-plan-routing
**Estimated Effort:** 1 ngay

## Muc tieu

Chuyen reformulation tu ratio-only sang reason-code-driven, de batch yeu co the de xuat posture/query tiep theo co y nghia.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/research_gating.py` | modified | Reason clusters + reformulation policy |
| `backend/app/services/runner.py` | modified | Persist reformulation reason va query lineage |
| `backend/tests/*` | modified | Test mapping tu reject reasons sang reformulation |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co cluster dominant reject reasons | ✓ |
| CHECK-02 | Cluster map sang query posture/query rewrite | ✓ |
| CHECK-03 | Query attempt co `used_reformulation` va ly do reformulation | ✓ |
