# CP4 Validation Checklist — Selective Expansion + Comment Scoring

### CHECK-01: Co selective expansion policy

```bash
rg -n "crawl_comments|selective expansion|UNCERTAIN|ACCEPTED|REJECTED" backend/app/services
```

### CHECK-02: Co parent-aware comment scoring

```bash
rg -n "parent context|parent_post|comment scoring|parent-aware" backend/app/services
```

### CHECK-03: Tests pass

```bash
cd backend && pytest -q
```
