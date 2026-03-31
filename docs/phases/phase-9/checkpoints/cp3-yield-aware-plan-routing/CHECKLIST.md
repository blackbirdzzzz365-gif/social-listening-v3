# CP3 Validation Checklist — Yield-Aware Plan Routing

### CHECK-01: Co metadata cho route posture

```bash
rg -n "route_posture|priority_score|trust|fraud|complaint" backend
```

### CHECK-02: Planner/runner co rerank logic

```bash
rg -n "rerank|reprioritize|reorder|yield-aware" backend/app/services
```

### CHECK-03: Co test cho routing order

```bash
rg -n "route.*order|rerank|priority score" backend/tests
```
