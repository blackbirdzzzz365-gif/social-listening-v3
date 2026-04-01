# CP2 Validation Checklist — Answer Closeout Orchestration

### CHECK-01: Label completion co hook closeout

```bash
rg -n "theme|insight|closeout|answer_ready|ANSWER_READY" backend/app/services
```

### CHECK-02: Co retry/idempotent guard

```bash
rg -n "idempotent|existing job|already done|upsert" backend/app/services
```

### CHECK-03: Co test cho answer delivery

```bash
rg -n "label.*theme|closeout|answer ready" backend/tests
```
