# CP7 Validation Checklist — Smoke + Audit Gate

### CHECK-01: Co demo log hoac smoke notes

```bash
test -f docs/phases/phase-8/checkpoints/cp7-phase8-smoke-audit/DEMO_LOG.md && echo ok
```

### CHECK-02: Co evidence accepted/rejected/uncertain audit

```bash
rg -n "accepted|rejected|uncertain|transactional|brand_official|seller_affiliate" docs/phases/phase-8/checkpoints/cp7-phase8-smoke-audit/DEMO_LOG.md
```

### CHECK-03: Co ket luan ve improvement va residual gap

```bash
rg -n "improvement|residual|follow-up|gap" docs/phases/phase-8/checkpoints/cp7-phase8-smoke-audit/DEMO_LOG.md
```
