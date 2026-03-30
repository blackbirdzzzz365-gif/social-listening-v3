# Checkpoint System — AI Facebook Social Listening v3 / Phase 6: Responsive Mobile Web

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
| CP0 | cp0-phase6-setup | Phase 6 Setup | Rewrite scope docs, tao workspace checkpoint, config dashboard | — | 6A | 0.5d |
| CP1 | cp1-responsive-primitives | Responsive Primitives | Responsive rules, shell primitives, shared layout behavior | CP0 | 6A | 1d |
| CP2 | cp2-main-app-mobile-pass | Main App Mobile Pass | Responsive pass cho app frontend pages | CP1 | 6B | 1.5d |
| CP3 | cp3-browser-entry-web | Browser Entry Web | Browser root landing page, help surfaces, routing | CP2 | 6B | 1d |
| CP4 | cp4-mobile-novnc-customization | Mobile noVNC Customization | Custom mobile VNC web surface + fallback paths | CP3 | 6C | 1.5d |
| CP5 | cp5-build-gate-smoke | Build Gate + Smoke | Build, viewport smoke, browser smoke, deploy notes | CP4 | 6C | 0.5d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 6A | CP0, CP1 | Scope lock + responsive foundation |
| Sprint 6B | CP2, CP3 | Main app mobile pass + browser entry web |
| Sprint 6C | CP4, CP5 | noVNC customization + smoke/build gate |

## Cau truc moi CP folder

```text
docs/phases/phase-6/checkpoints/cp{N}-{name}/
├── README.md
├── INSTRUCTIONS.md
├── CHECKLIST.md
├── result.json
└── validation.json
```

## Setup

```bash
cp docs/phases/phase-6/checkpoints/config.example.json \
   docs/phases/phase-6/checkpoints/config.json
# Sua ntfy_topic neu can; project_slug mac dinh cho Phase 6 la ai-facebook-social-listening-engagement-v3-phase-6
```
