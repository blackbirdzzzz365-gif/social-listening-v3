# CP4 Validation Checklist — Batch Routing V2

### CHECK-01: Batch routing co 3 trang thai

```bash
rg -n "reformulate|continue|stop|batch routing|batch health" backend/app/services
```

### CHECK-02: Co confidence-aware logic

```bash
rg -n "confidence|high_conf|accepted_ratio|uncertain_ratio" backend/app/services
```

### CHECK-03: Co test cho path routing

```bash
rg -n "reformulate|batch routing|weak path|uncertain path" backend/tests
```
