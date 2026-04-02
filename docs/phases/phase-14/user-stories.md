# User Stories - Phase 14

## Epic

Protect research kickoff from non-runnable browser runtime and surface readiness truth early.

## Stories

### Story 1 - Operator sees readiness before analysis

As an operator, I want to see whether browser runtime is ready on the keyword screen so I do not waste time starting research that cannot run.

Acceptance criteria:

- keyword screen shows current runtime readiness
- the view includes action required and next steps
- when runtime is not runnable, the operator is warned before analysis starts

### Story 2 - Planner-heavy actions short-circuit when runtime is down

As the system, I want to block topic analysis, clarification submission, and plan generation when runtime is not runnable so I do not spend planner cost unnecessarily.

Acceptance criteria:

- create session is blocked before planner execution
- submit clarifications is blocked before planner execution
- create/refine plan is blocked before planner execution
- block response is explicit and deterministic

### Story 3 - Operator can still inspect existing artifacts

As an operator, I want to load existing session and plan data while runtime is down so I can review context without unblocking execution first.

Acceptance criteria:

- read-only session fetch still works
- read-only plan fetch still works
- readiness truth is still visible in the payload/UI

### Story 4 - Production proves earlier stop

As a product owner, I want a live rerun to prove the system stops before planner cost when runtime is not runnable so the phase can be considered effective.

Acceptance criteria:

- a live production case produces an early readiness block
- production artifact clearly shows earlier stop than Phase 13
- checkpoint verdict records expectation vs actual
