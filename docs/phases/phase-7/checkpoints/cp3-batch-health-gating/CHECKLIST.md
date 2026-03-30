# CP3 Validation Checklist — Batch Health Gating

### CHECK-01: Co loop batch 20 posts

```bash
rg -n "20|batch|accepted_ratio|uncertain_ratio|strong_accept_count|consecutive_weak" backend/app/services
```

### CHECK-02: Runner hoac service co stop/continue path logic

```bash
rg -n "stop path|continue path|batch health|weak batch|query path" backend/app/services
```

### CHECK-03: Tests cho batch gating

```bash
cd backend && pytest -q
```
