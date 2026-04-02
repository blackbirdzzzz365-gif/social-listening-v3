# Detect / Brainstorm Solution - Phase 14

## Detected issue

The platform now tells the truth at run start, but not early enough in the research kickoff workflow.

## Candidate options considered

### Option A - Keep Phase 13 behavior

Wait until run start and then end as `REAUTH_REQUIRED`.

Why rejected:

- still burns planner cost
- still delays truth for the operator

### Option B - Gate only `/api/runs`

Block run creation but still allow session analysis and plan generation.

Why rejected:

- protects execution but not planning cost
- still misleads the user about readiness

### Option C - Gate planner-heavy kickoff actions

Block analysis, clarification, plan generation, and plan refinement when runtime is not runnable, while still allowing read-only inspection.

Why chosen:

- smallest change that fixes the waste pattern
- keeps operator visibility intact
- aligns with the actual production bottleneck
