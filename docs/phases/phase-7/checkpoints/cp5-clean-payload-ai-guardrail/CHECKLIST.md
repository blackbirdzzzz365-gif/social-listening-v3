# CP5 Validation Checklist — Clean Payload + AI Guardrail

### CHECK-01: Co clean payload builder

```bash
rg -n "clean payload|quality flags|dedupe|canonical url|normalized hash" backend/app/services
```

### CHECK-02: Co guardrail strict/balanced

```bash
rg -n "strict|balanced|ai queue|accepted|uncertain|rejected" backend/app/services
```

### CHECK-03: Tests pass

```bash
cd backend && pytest -q
```
