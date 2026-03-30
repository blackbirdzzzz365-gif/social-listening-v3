# CP0 Validation Checklist — Phase 7 Setup

### CHECK-01: Docs Phase 7 da khoa solution flow V2

```bash
rg -n "Solution Flow V2|top `20` posts|chiasegpu|Claude|Phase 8" docs/phases/phase-7
```

### CHECK-02: Co du bang checkpoint va CP folders

```bash
find docs/phases/phase-7/checkpoints -maxdepth 1 -type d | sort
```

### CHECK-03: Config Phase 7 dung project slug

```bash
rg -n '"project_slug": "ai-facebook-social-listening-engagement-v3-phase-7"' docs/phases/phase-7/checkpoints/config*.json
```
