# Checkpoint System - AI Facebook Social Listening v3 / Phase 10: Execution Control And Production Observability

## Checkpoints

| CP | Code | Ten | Noi dung | Depends On | Sprint | Effort |
|----|------|-----|----------|------------|--------|--------|
| CP0 | cp0-phase10-setup | Phase 10 Setup | Khoa scope docs, manifest, case pack, va checkpoint workspace cho Phase 10 | — | 10A | 0.5d |
| CP1 | cp1-cancel-safe-step-control | Cancel-Safe Step Control | `P0` them `CANCELLING`, stop convergence that, va chan post-cancel writes | CP0 | 10A | 1d |
| CP2 | cp2-step-heartbeat-live-counter | Step Heartbeat + Live Counter | `P0` heartbeat/progress payload va sync `plan_runs.total_records` trong luc step dang chay | CP1 | 10A | 1d |
| CP3 | cp3-stuck-step-timeout-taxonomy | Stuck-Step Timeout + Taxonomy | `P1` timed browser action wrapper, timeout class rieng, va failure clarity | CP2 | 10B | 1d |
| CP4 | cp4-production-audit-tooling | Production Audit Tooling | `P1` canh script/monitor theo schema hien tai va progress signal moi | CP2 | 10B | 0.5-1d |
| CP5 | cp5-answer-vision-revalidation | Answer + Vision Revalidation | `P1` chot Phase 10 case pack, answer-closeout recheck, va image-bearing validation plan | CP3, CP4 | 10C | 0.5-1d |
| CP6 | cp6-phase10-production-smoke-audit | Production Smoke + Audit | deploy, chay live 1-2 case, viet checkpoint verdict, va chot improvement packet | CP5 | 10D | 0.5-1d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 10A | CP0, CP1, CP2 | Runtime control boundary |
| Sprint 10B | CP3, CP4 | Timeout clarity + operator tooling |
| Sprint 10C | CP5 | Production revalidation package |
| Sprint 10D | CP6 | Live audit closeout |

## Setup

```bash
cp docs/phases/phase-10/checkpoints/config.example.json \
   docs/phases/phase-10/checkpoints/config.json
```

Mac dinh Phase 10 project slug:

- `ai-facebook-social-listening-engagement-v3-phase-10`
