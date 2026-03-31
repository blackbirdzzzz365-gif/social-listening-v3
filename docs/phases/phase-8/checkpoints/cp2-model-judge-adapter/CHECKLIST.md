# CP2 Validation Checklist — Model Judge Adapter

### CHECK-01: Co adapter interface cho model judge

```bash
rg -n "judge_result|model judge|validity_spec|relevance_score|confidence_score" backend/app
```

### CHECK-02: Co normalize output schema

```bash
rg -n "reason_codes|short_rationale|UNCERTAIN|ACCEPTED|REJECTED" backend/app
```

### CHECK-03: Co test cho parse va failure path

```bash
rg -n "judge adapter|malformed response|confidence_score|relevance_score" backend/tests
```
