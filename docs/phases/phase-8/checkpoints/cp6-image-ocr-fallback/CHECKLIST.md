# CP6 Validation Checklist — Image OCR / Vision Fallback

### CHECK-01: OCR/vision co trigger policy co dieu kien

```bash
rg -n "OCR|vision|used_image_understanding|image fallback|uncertain.*image" backend/app
```

### CHECK-02: Co final aggregation cho judge result

```bash
rg -n "image summary|aggregate.*judge|re-judge" backend/app/services
```

### CHECK-03: Co test cho image-bearing records

```bash
rg -n "OCR|vision|image fallback|used_image_understanding" backend/tests
```
