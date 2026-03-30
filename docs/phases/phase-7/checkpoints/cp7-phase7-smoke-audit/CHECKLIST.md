# CP7 Validation Checklist — Phase 7 Smoke + Audit Gate

### CHECK-01: Smoke gate chay thanh cong

```bash
cd backend && pytest -q
```

### CHECK-02: Co DEMO_LOG va audit output

```bash
test -f docs/phases/phase-7/checkpoints/cp7-phase7-smoke-audit/DEMO_LOG.md && echo ok
```

### CHECK-03: Co references den retrieval/provider metrics

```bash
rg -n "accepted_ratio|query_family|source_type|provider_used|fallback_used|failure_reason" docs/phases/phase-7 backend
```
