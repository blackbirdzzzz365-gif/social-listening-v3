# CP3 Validation Checklist — Post Judging + Persistence

### CHECK-01: Hard filter van ton tai truoc model call

```bash
rg -n "duplicate|ui noise|hard filter|too_short|empty content" backend/app/services
```

### CHECK-02: Judge result duoc persist

```bash
rg -n "judge_decision|judge_relevance|judge_confidence|reason_codes|used_image" backend/app
```

### CHECK-03: Co test cho post-level integration

```bash
rg -n "post judge|hard filter|judge result persistence" backend/tests
```
