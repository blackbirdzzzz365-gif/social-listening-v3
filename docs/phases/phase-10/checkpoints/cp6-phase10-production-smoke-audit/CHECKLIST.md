# CP6 Validation Checklist — Phase 9 Production Smoke + Audit

### CHECK-01: Co evidence cho safety va answer delivery

```bash
rg -n "busy|queued|INFRA_BROWSER|ANSWER_READY|theme_results|label_jobs" reports docs/phases/phase-9/checkpoints/cp6-phase9-production-smoke-audit
```

### CHECK-02: Co evidence cho routing / reformulation / vision

```bash
rg -n "rerank|route posture|used_reformulation|reason cluster|accepted_with_image|vision" reports docs/phases/phase-9/checkpoints/cp6-phase9-production-smoke-audit
```

### CHECK-03: Co closeout note cho phase tiep theo

```bash
rg -n "next phase|remaining gap|phase 10|phase tiep theo" docs/phases/phase-9/checkpoints/cp6-phase9-production-smoke-audit
```
