# Phase 14 - Research Runtime Readiness And Kickoff Gate

## Metadata
- Delivery mode: `new-phase`
- Branch: `codex/phase-14`
- Worktree: `/Users/nguyenquocthong/project/social-listening-v3-worktrees/codex-phase-14`
- Upstream checkpoint verdict: `run-757ce848df` runtime truth on production at `2026-04-02 14:12 ICT`
- Primary layer: `app`
- Related layers: `shell`, `platform`

## User Problem
- Operators can still spend planning effort and planner cost even when browser runtime is already not runnable.

## Desired Outcome
- Browser readiness is surfaced before research kickoff and planner-heavy actions short-circuit when runtime is not runnable.

## Scope
### In Scope
- runtime readiness contract for planning surfaces
- early gate for topic analysis, clarification, plan generation, and refine
- keyword/plan UI readiness surface
- production rerun to prove earlier stop

### Out Of Scope
- fixing Facebook re-login automation
- retrieval strategy changes
- downstream answer/theme changes

## Technical Delta
- Existing behavior: runtime truth blocks at run start, after planner work has already happened
- Proposed behavior: runtime truth blocks before planner-heavy kickoff actions start
- Files/modules likely affected:
  - `backend/app/api/plans.py`
  - `backend/app/api/browser.py`
  - `backend/app/schemas/plans.py`
  - `backend/app/schemas/browser.py`
  - `backend/app/services/runtime_readiness.py`
  - `frontend/src/pages/KeywordPage.tsx`
  - `frontend/src/pages/PlanPage.tsx`

## Metrics And Exit Criteria
- Business: no planner cost spent on non-runnable runtime kickoff
- User: operator sees readiness truth before starting research
- Engineering: production rerun returns early block before context/plan generation

## Required Docs
- README: done
- BA brief: done
- Technical solution: done
- User stories: done
- Checkpoint README: done

## Stop Rules
- do not change planner semantics for valid runtime cases
- do not hide read-only inspect flows while runtime is blocked
