# CP1 Validation Checklist — Validity Spec Builder

### CHECK-01: Co contract `validity_spec`

```bash
rg -n "validity_spec|target_signal|hard_reject|comment_policy|batch_policy" backend
```

### CHECK-02: Planner/context compile duoc spec

```bash
rg -n "compile.*validity_spec|build.*validity_spec|validity spec" backend/app/services
```

### CHECK-03: Co test cho spec generation

```bash
rg -n "validity spec|research context|comment policy|batch policy" backend/tests
```
