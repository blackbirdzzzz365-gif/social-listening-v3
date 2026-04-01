# CP3 — Yield-Aware Plan Routing

**Code:** cp3-yield-aware-plan-routing
**Order:** 3
**Depends On:** cp2-answer-closeout-orchestration
**Estimated Effort:** 1 ngay

## Muc tieu

Nang planner/runtime de query posture yield cao duoc uu tien som hon, thay vi de trust/fraud/complaint path xuat hien qua muon trong plan.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/planner.py` | modified | Them posture hints / plan rerank input |
| `backend/app/services/runner.py` | modified | Re-rank hoac reorder path truoc khi execute |
| `backend/app/services/*` | created | Route ranking helper neu can |
| `backend/tests/*` | modified | Test high-yield posture duoc dua som |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co route posture metadata hoac priority score | ✓ |
| CHECK-02 | High-yield postures co the duoc dua len truoc generic path | ✓ |
| CHECK-03 | Routing decision duoc audit duoc | ✓ |
