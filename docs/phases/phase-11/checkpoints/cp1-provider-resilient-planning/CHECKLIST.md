# CP1 Validation Checklist - Provider-Resilient Planning

### CHECK-01: Co planner resilience wrapper

```bash
rg -n "PlannerProviderUnavailable|_call_planner_with_resilience|planner retry" backend/app/services/planner.py
```

### CHECK-02: API map planner overload sang 503

```bash
rg -n "503|PlannerProviderUnavailable" backend/app/api/plans.py
```

### CHECK-03: Co test cho retry / graceful failure

```bash
rg -n "PlannerProviderUnavailable|planner resilience|retry" backend/tests
```
