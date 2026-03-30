# Checkpoint System - AI Facebook Social Listening v3 / Phase 7: Retrieval Quality Gating Before AI Cost

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
| CP0 | cp0-phase7-setup | Phase 7 Setup | Khoa scope docs, tao workspace checkpoint, config/scripts Phase 7 | — | 7A | 0.5d |
| CP1 | cp1-retrieval-profile-builder | Retrieval Profile Builder | Build retrieval profile, query families, source hints, config shape | CP0 | 7A | 1d |
| CP2 | cp2-post-candidate-scoring | Post Candidate Scoring | Extend persistence path + deterministic scoring for posts | CP1 | 7B | 1d |
| CP3 | cp3-batch-health-gating | Batch Health Gating | Top-20 batch loop, accepted ratio rules, stop/continue path logic | CP2 | 7B | 1d |
| CP4 | cp4-selective-expansion-comments | Selective Expansion + Comment Scoring | Crawl comments only for allowed posts, score comments with parent context | CP3 | 7C | 1d |
| CP5 | cp5-clean-payload-ai-guardrail | Clean Payload + AI Guardrail | Normalize payload, dedupe, quality flags, strict/balanced AI gate | CP4 | 7C | 1d |
| CP6 | cp6-ai-provider-failover-telemetry | AI Provider Failover + Telemetry | `chiasegpu` primary, Claude fallback policy, retry and provider telemetry | CP5 | 7D | 0.5-1d |
| CP7 | cp7-phase7-smoke-audit | Smoke + Audit Gate | E2E smoke, retrieval metrics, provider audit, phase closeout | CP6 | 7D | 0.5d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 7A | CP0, CP1 | Scope lock + retrieval profile foundation |
| Sprint 7B | CP2, CP3 | Post scoring + batch-level gating |
| Sprint 7C | CP4, CP5 | Selective expansion + clean payload + AI guardrail |
| Sprint 7D | CP6, CP7 | Provider failover policy + smoke/audit closeout |

## Cau truc moi CP folder

```text
docs/phases/phase-7/checkpoints/cp{N}-{name}/
├── README.md
├── INSTRUCTIONS.md
├── CHECKLIST.md
├── result.json
└── validation.json
```

## Setup

```bash
cp docs/phases/phase-7/checkpoints/config.example.json \
   docs/phases/phase-7/checkpoints/config.json
# Sua ntfy_topic neu can; project_slug mac dinh cho Phase 7 la ai-facebook-social-listening-engagement-v3-phase-7
```
