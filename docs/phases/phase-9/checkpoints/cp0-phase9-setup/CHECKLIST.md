# CP0 Validation Checklist — Phase 9 Setup

### CHECK-01: Docs Phase 9 da khoa huong giai quyet

```bash
rg -n "production safety|answer delivery|plan routing|reformulation|vision" docs/phases/phase-9
```

### CHECK-02: Co du bang checkpoint va CP folders

```bash
find docs/phases/phase-9/checkpoints -maxdepth 1 -type d | sort
```

### CHECK-03: Config Phase 9 dung project slug

```bash
rg -n '"project_slug": "ai-facebook-social-listening-engagement-v3-phase-9"' docs/phases/phase-9/checkpoints/config*.json
```
