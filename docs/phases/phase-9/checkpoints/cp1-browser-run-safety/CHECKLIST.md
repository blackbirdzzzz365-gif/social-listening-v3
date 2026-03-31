# CP1 Validation Checklist — Browser Run Safety

### CHECK-01: Co lease hoac admission control

```bash
rg -n "lease|busy|queued|admission|browser slot" backend
```

### CHECK-02: Co failure class ro cho browser infra

```bash
rg -n "INFRA_BROWSER|browser boot|failure class|completion_reason" backend
```

### CHECK-03: Co test cho concurrent protection

```bash
rg -n "lease|busy|concurrent|admission" backend/tests
```
