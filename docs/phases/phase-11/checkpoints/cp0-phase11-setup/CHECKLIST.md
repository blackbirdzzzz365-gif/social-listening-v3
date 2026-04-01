# CP0 Validation Checklist - Phase 11 Setup

### CHECK-01: Co full docs package

```bash
find docs/phases/phase-11 -maxdepth 2 -type f | sort
```

### CHECK-02: `.phase.json` tro sang phase-11

```bash
rg -n '"current": "phase-11"|phase-11-core' .phase.json
```
