# CP6 Validation Checklist — AI Provider Failover + Telemetry

### CHECK-01: AIClient co retry/failover policy ro rang

```bash
rg -n "retry|failover|fallback|chiasegpu|anthropic|provider" backend/app/infra/ai_client.py
```

### CHECK-02: Co metadata provider

```bash
rg -n "provider_used|fallback_used|failure_reason|attempt_count" backend/app
```

### CHECK-03: Tests pass

```bash
cd backend && pytest -q
```
