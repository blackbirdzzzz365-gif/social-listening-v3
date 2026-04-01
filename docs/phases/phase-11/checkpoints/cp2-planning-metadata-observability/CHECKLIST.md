# CP2 Validation Checklist - Planning Metadata And Observability

### CHECK-01: Model co planning meta field

```bash
rg -n "planning_meta|generation_meta" backend/app/models backend/alembic/versions
```

### CHECK-02: Session/Plan schema expose planning meta

```bash
rg -n "planning_meta|generation_meta" backend/app/schemas/plans.py backend/app/api/plans.py
```
