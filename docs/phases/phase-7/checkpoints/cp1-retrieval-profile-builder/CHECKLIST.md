# CP1 Validation Checklist — Retrieval Profile Builder

### CHECK-01: Retrieval profile co du cac thanh phan chinh

```bash
rg -n "retrieval_profile|anchors|related_terms|negative_terms|query_families|source_hints" backend
```

### CHECK-02: Query families bao gom cac intent da khoa

```bash
rg -n "brand|pain_point|question|comparison|complaint" backend
```

### CHECK-03: Co test cho retrieval profile

```bash
rg -n "retrieval profile|query family|source hints" backend/tests
```
