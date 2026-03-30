# CP7 — Phase 7 Smoke + Audit Gate

**Code:** cp7-phase7-smoke-audit
**Order:** 7
**Depends On:** cp6-ai-provider-failover-telemetry
**Estimated Effort:** 0.5 ngay

## Muc tieu

Dong bang Phase 7 bang smoke tests, retrieval audit, provider telemetry audit, va closeout notes cho handoff sang implementation phase sau.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/tests/*` | modified | Smoke tests neu can de cover flow Phase 7 |
| `docs/phases/phase-7/checkpoints/cp7-phase7-smoke-audit/DEMO_LOG.md` | created | Log smoke/audit va ket qua closeout |
| `docs/phases/phase-7/*.md` | modified | Cap nhat notes neu can sau validate smoke |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co smoke gate cho retrieval scoring + batch gating + AI guardrail | ✓ |
| CHECK-02 | Co audit output cho query/source/provider metrics | ✓ |
| CHECK-03 | Co closeout log cho phase | ✓ |
