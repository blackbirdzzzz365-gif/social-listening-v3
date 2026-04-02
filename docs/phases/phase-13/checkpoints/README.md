# Checkpoint System - AI Facebook Social Listening v3 / Phase 13: Session Truthfulness And Re-Auth Admission

## Checkpoints

| CP | Code | Ten | Noi dung | Depends On | Sprint | Effort |
|----|------|-----|----------|------------|--------|--------|
| CP0 | cp0-phase13-setup | Phase 13 Setup | Khoa scope docs, manifest, case pack, va checkpoint workspace cho Phase 13 | — | 13A | 0.5d |
| CP1 | cp1-session-truth-contract | Session Truth Contract | Khoa invariant giua `session_status`, `health_status`, va `runnable` | CP0 | 13A | 0.5-1d |
| CP2 | cp2-reauth-admission-gate | Re-Auth Admission Gate | Chan browser-backed run truoc `step-1` khi session khong runnable | CP1 | 13A | 1d |
| CP3 | cp3-expiry-propagation-and-terminal-outcome | Expiry Propagation And Terminal Outcome | Dua browser expiry thanh health truth va outcome `REAUTH_REQUIRED` ro nghia | CP1, CP2 | 13B | 1d |
| CP4 | cp4-operator-surface-and-monitor | Operator Surface And Monitor | Expose session truth, action required, va run block reason tren API/UI | CP2, CP3 | 13B | 0.5-1d |
| CP5 | cp5-phase13-production-revalidation | Production Revalidation | Deploy, rerun expired-session case + valid-session control, viet verdict | CP3, CP4 | 13C | 0.5-1d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 13A | CP0, CP1, CP2 | Truth contract and preflight gate |
| Sprint 13B | CP3, CP4 | Runtime propagation and operator visibility |
| Sprint 13C | CP5 | Live proof and checkpoint verdict |
