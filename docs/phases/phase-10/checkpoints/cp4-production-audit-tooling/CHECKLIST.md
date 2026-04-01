# CP4 Validation Checklist — Reason-Aware Reformulation

### CHECK-01: Co reason cluster mapping

```bash
rg -n "reason cluster|reason_code|reformulate|dominant reject" backend
```

### CHECK-02: Co lineage cho reformulated query

```bash
rg -n "reformulated_from|used_reformulation|reason_cluster" backend
```

### CHECK-03: Co test cho reformulation mapping

```bash
rg -n "reformulation|reason code|reject cluster" backend/tests
```
