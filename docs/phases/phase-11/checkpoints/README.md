# Checkpoint System - AI Facebook Social Listening v3 / Phase 11: Provider-Resilient Planning And Image-Bearing Evidence Acquisition

## Checkpoints

| CP | Code | Ten | Noi dung | Depends On | Sprint | Effort |
|----|------|-----|----------|------------|--------|--------|
| CP0 | cp0-phase11-setup | Phase 11 Setup | Khoa scope docs, manifest, case pack, va checkpoint workspace cho Phase 11 | — | 11A | 0.5d |
| CP1 | cp1-provider-resilient-planning | Provider-Resilient Planning | `P0` retry/fallback wrapper, planner failure taxonomy, va graceful API behavior | CP0 | 11A | 1d |
| CP2 | cp2-planning-metadata-observability | Planning Metadata + Observability | `P0` persist/expose planner meta tren session/plan va monitor surface lien quan | CP1 | 11A | 1d |
| CP3 | cp3-image-first-retrieval-posture | Image-First Retrieval Posture | `P1` image-bearing query families, ordering, va reformulation posture | CP2 | 11B | 1d |
| CP4 | cp4-timeout-salvage-auditability | Timeout Salvage + Auditability | `P1` luu dau vet collected-but-unpersisted va timeout audit surface | CP3 | 11B | 1d |
| CP5 | cp5-phase11-audit-tooling | Phase 11 Audit Tooling | `P1` cap nhat case pack, monitor, va report schema cho planner/image salvage truth | CP2, CP4 | 11C | 0.5-1d |
| CP6 | cp6-phase11-production-revalidation | Production Revalidation | deploy, chay live planner/image case, viet verdict, va chot improvement packet | CP5 | 11D | 0.5-1d |

## Sprint Mapping

| Sprint | Checkpoints | Focus |
|--------|-------------|-------|
| Sprint 11A | CP0, CP1, CP2 | Planner resilience boundary |
| Sprint 11B | CP3, CP4 | Image-bearing evidence path |
| Sprint 11C | CP5 | Audit and case pack alignment |
| Sprint 11D | CP6 | Live proof and closeout |

## Setup

```bash
cp docs/phases/phase-11/checkpoints/config.example.json \
   docs/phases/phase-11/checkpoints/config.json
```

Mac dinh Phase 11 project slug:

- `ai-facebook-social-listening-engagement-v3-phase-11`
