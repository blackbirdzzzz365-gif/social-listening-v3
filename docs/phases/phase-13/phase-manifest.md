# Phase 13 - Session Truthfulness And Re-Auth Admission

## Metadata
- Delivery mode: `new-phase`
- Branch: `codex/phase-13`
- Worktree: `/Users/nguyenquocthong/project/social-listening-v3-worktrees/codex-phase-13`
- Upstream checkpoint verdict: Phase 12 revalidation on 2026-04-02 based on `run-7dcd19fbf2` and `run-ba6fc47411`
- Primary layer: `platform`
- Related layers:
  - `app`
  - `shell`

## User Problem
- Browser-backed runs can still start on an expired Facebook session.
- Operators get a generic failure instead of a clear re-auth action.
- Monitor truth is unreliable when session state and health state disagree.

## Desired Outcome
- Session truth is authoritative for run admission.
- Expired sessions produce `REAUTH_REQUIRED` style outcomes before wasted execution.
- Operator surface clearly shows when re-authentication is needed.

## Scope
### In Scope
- Health/session truth contract
- Re-auth preflight gate
- Mid-run expiry propagation
- Auth-specific terminal outcome
- API/monitor surface
- Production case pack and revalidation

### Out Of Scope
- Retrieval tuning
- Planner changes
- Image evidence work
- Platform SSO redesign

## Technical Delta
- Existing behavior:
  - runs can reach `step-1` even when session is already expired
  - auth/session incidents fall through as generic `STEP_ERROR`
  - monitor can expose mixed health truth
- Proposed behavior:
  - session truth blocks browser-backed runs before step execution
  - expired sessions degrade health truth immediately
  - auth incidents terminate as explicit re-auth-required outcomes
- Files/modules likely affected:
  - `backend/app/models/health.py`
  - `backend/app/services/health_monitor.py`
  - `backend/app/services/browser_run_admission.py`
  - `backend/app/services/runner.py`
  - `backend/app/api/browser.py`
  - `backend/app/schemas/browser.py`
  - `frontend/src/pages/MonitorPage.tsx`

## Metrics And Exit Criteria
- Business:
  - no wasted browser-backed run starts on expired sessions
- User:
  - operator sees explicit re-auth-needed state and next action
- Engineering:
  - no `HEALTHY + EXPIRED` state
  - FE Credit auth regression ends as `REAUTH_REQUIRED`, not generic `STEP_ERROR`

## Required Docs
- README: `docs/phases/phase-13/README.md`
- BA brief: `docs/phases/phase-13/ba-problem-brief.md`
- Technical solution: `docs/phases/phase-13/technical-solution.md`
- User stories: `docs/phases/phase-13/user-stories.md`
- Checkpoint README: `docs/phases/phase-13/checkpoints/README.md`

## Stop Rules
- Stop if proposed changes start redesigning platform auth policy instead of fixing session truthfulness.
- Stop if the solution weakens Phase 12 no-answer or answer-ready closeout behavior.
