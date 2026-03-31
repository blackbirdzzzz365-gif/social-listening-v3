# Phase 8 Smoke / Audit Log

## Environment

- Timestamp: `2026-03-31T16:29:52+0700`
- DB: `.tmp_phase8/phase8_smoke.db`
- Browser mode: `mock`
- Browser profile: `.tmp_phase8/browser_profile`
- Model provider path: `mock`

## Validation Commands

```bash
PYTHONPATH=backend ./.venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py'
cd backend && SQLITE_DB_PATH=../.tmp_phase8/phase8_smoke.db ../.venv/bin/alembic upgrade head
```

## Smoke Result

- Final run id: `run-4abbf411bb`
- Run status: `DONE`
- Completion reason: `COMPLETED`
- Total persisted records: `36`
- `validity_spec` persisted on session/context:
  - `spec-phan-hoi-end-user-ve-mat-na-bot-dau-xanh-73eeb4944c`
  - `phase8-v1-73eeb4944c`

## Judge Coverage

- Judge fields present: `36/36`
- Accepted: `24`
- Uncertain: `9`
- Rejected: `3`
- `judge_used_image_understanding`: `0`

## Downstream Result

- Label job: `DONE`
- Eligible records labeled: `24`
- Label fallback count: `0`
- Theme filter result:
  - crawled: `36`
  - included: `22`
  - excluded: `14`
  - excluded breakdown: `pre_ai_rejected=12`, `low_relevance=2`

## Issues Found During Validation

1. First smoke failed because `browser_profile_dir` defaulted to an unwritable `/root/...` path in this environment.
Resolution: reran smoke with `BROWSER_PROFILE_DIR=.tmp_phase8/browser_profile`.

2. First smoke failed in `SEARCH_POSTS` with `name 'score' is not defined`.
Resolution: fixed stale runner reference and reran smoke successfully.

## Residual Gaps

- Image fallback path is implemented and unit-tested, but the final smoke did not exercise it because browser extraction does not yet attach image metadata.
- Planner mock still produces awkward long search targets for some sessions. This affects retrieval quality but does not block Phase 8 wiring or validation.
