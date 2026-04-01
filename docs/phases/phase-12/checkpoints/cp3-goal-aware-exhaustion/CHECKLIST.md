# CP3 Validation Checklist - Goal-Aware Exhaustion

### CHECK-01: Co rule exhaustion/skip tail step

```bash
rg -n "exhaust|skip.*tail|goal-aware|NO_ELIGIBLE_RECORDS" backend/app/services/runner.py
```
