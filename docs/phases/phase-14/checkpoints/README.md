# Checkpoint System - AI Facebook Social Listening v3 / Phase 14: Research Runtime Readiness And Kickoff Gate

## Checkpoints

| CP | Code | Ten | Noi dung | Depends On | Sprint | Effort |
|----|------|-----|----------|------------|--------|--------|
| CP0 | cp0-phase14-setup | Phase 14 Setup | Khoa scope docs, manifest, case pack, va checkpoint workspace cho Phase 14 | — | 14A | 0.5d |
| CP1 | cp1-runtime-readiness-contract | Runtime Readiness Contract | Tao payload readiness dung chung cho browser, session, va plan surfaces | CP0 | 14A | 0.5d |
| CP2 | cp2-kickoff-and-planning-gate | Kickoff And Planning Gate | Chan planner-heavy actions truoc khi runtime runnable | CP1 | 14A | 1d |
| CP3 | cp3-operator-readiness-surface | Operator Readiness Surface | Hien readiness truth tren keyword va plan UI, giu read-only inspect flow | CP1, CP2 | 14B | 0.5-1d |
| CP4 | cp4-phase14-production-revalidation | Production Revalidation | Deploy, rerun live kickoff case, viet verdict ve earlier-stop behavior | CP2, CP3 | 14B | 0.5-1d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 14A | CP0, CP1, CP2 | Runtime readiness contract and early gate |
| Sprint 14B | CP3, CP4 | Operator visibility and live proof |
