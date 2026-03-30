# CP0 Validation Checklist — Phase 6 Setup

### CHECK-01: Phase 6 docs da bo assisted login khoi scope

```bash
if rg -n "Assisted login is in scope|credential automation in scope" docs/phases/phase-6; then exit 1; else echo OK; fi
```

### CHECK-02: Co du 6 checkpoint folders

```bash
find docs/phases/phase-6/checkpoints -maxdepth 1 -type d -name 'cp*' | wc -l | tr -d ' '
```

### CHECK-03: project_slug dung cho Phase 6

```bash
python3 - <<'PY'
import json
from pathlib import Path
config = json.loads(Path('docs/phases/phase-6/checkpoints/config.json').read_text())
assert config["project_slug"] == "ai-facebook-social-listening-engagement-v3-phase-6"
print("OK")
PY
```
