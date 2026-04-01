# Phase 12 - No-Answer Closeout And Goal-Aware Exhaustion

## Metadata
- Delivery mode: `new-phase`
- Branch: `codex/phase-12`
- Worktree: `/Users/nguyenquocthong/project/social-listening-v3-worktrees/codex-phase-12`
- Upstream checkpoint verdict: `docs/phases/phase-11/analysis/checkpoint-verdict-20260402-0125.md`
- Primary layer: `app`
- Related layers: `platform`, `shell`

## User Problem
- Runs that end with `NO_ELIGIBLE_RECORDS` still do not produce a final user-facing outcome.

## Desired Outcome
- Every terminal run has an explainable final outcome, including no-answer states.

## Scope
### In Scope
- no-answer outcome payload
- deterministic no-answer closeout
- goal-aware exhaustion
- API/UI exposure

### Out Of Scope
- broad planner redesign
- visual-evidence acquisition redesign

## Technical Delta
- Existing behavior: run ends at `NO_ELIGIBLE_RECORDS` with status only.
- Proposed behavior: run persists a no-answer payload and can stop exhausted tails earlier.
- Files/modules likely affected:
  - `backend/app/models/run.py`
  - `backend/app/services/label_job_service.py`
  - `backend/app/services/run_closeout.py`
  - `backend/app/services/runner.py`
  - `backend/app/schemas/runs.py`
  - `frontend/src/pages/MonitorPage.tsx`
  - `backend/alembic/versions/*`

## Metrics And Exit Criteria
- Business:
  - no-answer runs still end with a visible final explanation
- User:
  - operator can explain the outcome without opening logs
- Engineering:
  - weak tail steps are skipped earlier under deterministic exhaustion rules

## Required Docs
- README: done
- BA brief: done
- Technical solution: done
- User stories: done
- Checkpoint README: done

## Stop Rules
- Do not lower acceptance thresholds just to force output.
- Do not regress existing `ANSWER_READY` closeout.
