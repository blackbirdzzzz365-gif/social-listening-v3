# CP5 Validation Checklist — Vision Validation Harness

### CHECK-01: Co scenario image-bearing

```bash
rg -n "image|ocr|vision|screenshot|bao bi|hop dong" backend/tests docs/phases/phase-9
```

### CHECK-02: Co metrics va audit hook

```bash
rg -n "judge_used_image_understanding|ocr|vision.*metric|image understanding" backend
```

### CHECK-03: Co evidence case

```bash
rg -n "accepted_with_image|vision validation|ocr evidence" reports docs/phases/phase-9
```
