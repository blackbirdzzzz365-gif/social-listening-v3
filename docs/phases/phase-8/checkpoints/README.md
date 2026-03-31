# Checkpoint System - AI Facebook Social Listening v3 / Phase 8: Research-Aware Model Gating In Production Workflow

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
| CP0 | cp0-phase8-setup | Phase 8 Setup | Khoa scope docs, tao workspace checkpoint, config/scripts Phase 8 | — | 8A | 0.5d |
| CP1 | cp1-validity-spec-builder | Validity Spec Builder | Compile research context thanh `validity_spec` versioned cho tung run | CP0 | 8A | 1d |
| CP2 | cp2-model-judge-adapter | Model Judge Adapter | Tao adapter goi model API, schema parse, retry/failure normalization | CP1 | 8A | 1d |
| CP3 | cp3-post-judging-persistence | Post Judging + Persistence | Dua judge result vao flow post candidate, persist decision/score/confidence/reasons | CP2 | 8B | 1d |
| CP4 | cp4-batch-routing-v2 | Batch Routing V2 | Batch health dua tren judge output, support continue/reformulate/stop | CP3 | 8B | 1d |
| CP5 | cp5-comment-policy-gating | Comment Policy Gating | Comment-specific judging, parent context co dieu kien, chan transactional-only comments | CP4 | 8C | 1d |
| CP6 | cp6-image-ocr-fallback | Image OCR / Vision Fallback | Chi goi OCR/vision khi can, hop nhat lai final judge result | CP5 | 8C | 1-1.5d |
| CP7 | cp7-phase8-smoke-audit | Smoke + Audit Gate | E2E smoke, audit valid set quality, phase closeout | CP6 | 8D | 0.5-1d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 8A | CP0, CP1, CP2 | Scope lock + `validity_spec` + model judge adapter |
| Sprint 8B | CP3, CP4 | Post-level integration + batch routing V2 |
| Sprint 8C | CP5, CP6 | Comment policy + conditional image fallback |
| Sprint 8D | CP7 | Smoke, audit, closeout |

## Cau truc moi CP folder

```text
docs/phases/phase-8/checkpoints/cp{N}-{name}/
├── README.md
├── INSTRUCTIONS.md
├── CHECKLIST.md
├── result.json
└── validation.json
```

## Setup

```bash
cp docs/phases/phase-8/checkpoints/config.example.json \
   docs/phases/phase-8/checkpoints/config.json
# Sua ntfy_topic neu can; project_slug mac dinh cho Phase 8 la ai-facebook-social-listening-engagement-v3-phase-8
```

