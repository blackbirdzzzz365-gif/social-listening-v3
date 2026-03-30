# CP2 Validation Checklist — Post Candidate Scoring

### CHECK-01: Model va migration da co pre-AI fields

```bash
rg -n "pre_ai_|score_breakdown|query_family|source_type|processing_stage" backend/app backend/alembic
```

### CHECK-02: Co deterministic relevance engine cho post

```bash
rg -n "ACCEPTED|REJECTED|UNCERTAIN|anchor_score|related_score|negative_penalty|quality_score|source_score" backend/app
```

### CHECK-03: Test scoring pass

```bash
cd backend && pytest -q
```
