# Checkpoint System - AI Facebook Social Listening v3 / Phase 9: Production-Safe Answer Delivery

## Tong quan luong lam viec

```text
[Implementation Agent]     [User]        [Validator Agent]
        |                    |                   |
        |  implement CP-N    |                   |
        |------------------>|                   |
        |  write result.json |                   |
        |  run notify.py     |                   |
        |------------------>| notification      |
        |                    | trigger validator>|
        |                    |                   | run CHECKLIST
        |                    |                   | write validation.json
        |                    |<-- notification --|
        |  [PASS] trigger N+1|                   |
        |<------------------|                   |
```

## Checkpoints

| CP | Code | Ten | Noi dung | Depends On | Sprint | Effort |
|----|------|-----|----------|------------|--------|--------|
| CP0 | cp0-phase9-setup | Phase 9 Setup | Khoa scope docs, tao workspace checkpoint, config/scripts Phase 9 | — | 9A | 0.5d |
| CP1 | cp1-browser-run-safety | Browser Run Safety | `P0` Run admission control, browser lease, failure taxonomy, queued/busy states | CP0 | 9A | 1d |
| CP2 | cp2-answer-closeout-orchestration | Answer Closeout Orchestration | `P0` Tu label completion den theme/insight auto-run, answer-ready terminal state | CP1 | 9A | 1d |
| CP3 | cp3-yield-aware-plan-routing | Yield-Aware Plan Routing | `P1` Re-rank search posture theo expected yield va evidence tu production | CP2 | 9B | 1d |
| CP4 | cp4-reason-aware-reformulation | Reason-Aware Reformulation | `P1` Dung reject reason clusters de rewrite posture/query thay vi chi stop | CP3 | 9B | 1d |
| CP5 | cp5-vision-validation-harness | Vision Validation Harness | `P2` Validation scenarios, metrics, va audit cho OCR / vision fallback | CP2 | 9C | 1d |
| CP6 | cp6-phase9-production-smoke-audit | Production Smoke + Audit | Verify safety, answer delivery, routing, reformulation, vision evidence | CP4, CP5 | 9D | 0.5-1d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 9A | CP0, CP1, CP2 | Scope lock + production safety + answer closeout |
| Sprint 9B | CP3, CP4 | Earlier yield + real reformulation |
| Sprint 9C | CP5 | Vision validation |
| Sprint 9D | CP6 | Production smoke/audit closeout |

## Cau truc moi CP folder

```text
docs/phases/phase-9/checkpoints/cp{N}-{name}/
├── README.md
├── INSTRUCTIONS.md
├── CHECKLIST.md
├── result.json
└── validation.json
```

## Setup

```bash
cp docs/phases/phase-9/checkpoints/config.example.json \
   docs/phases/phase-9/checkpoints/config.json
# Sua ntfy_topic neu can; project_slug mac dinh cho Phase 9 la ai-facebook-social-listening-engagement-v3-phase-9
```
