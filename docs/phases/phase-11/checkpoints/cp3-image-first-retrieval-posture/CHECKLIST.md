# CP3 Validation Checklist - Image-First Retrieval Posture

### CHECK-01: Co image-bearing query family

```bash
rg -n "image|visual|before after|screenshot" backend/app/services/retrieval_quality.py
```
