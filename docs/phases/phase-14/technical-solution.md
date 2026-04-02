# Technical Solution - Phase 14

## Solution summary

Phase 14 adds a lightweight readiness gate in front of the planning workflow:

1. `runtime readiness contract`
2. `kickoff and planning admission gate`
3. `operator readiness surface`

The system should stop before planner/model work when the browser runtime is already known to be non-runnable.

## Track A - Runtime readiness contract

Create one shared payload shape derived from browser runtime truth:

- `runnable`
- `session_status`
- `health_status`
- `action_required`
- `block_reason`
- `last_checked`
- `summary`
- `next_steps`

This contract should be reusable across:

- `/api/browser/status`
- `/api/sessions`
- `/api/plans`

## Track B - Kickoff gate

### B1. Block planner-heavy actions

Before these actions call planner/model logic:

- create session
- submit clarifications
- create plan
- refine plan

check runtime readiness first.

If runtime is not runnable:

- do not call planner/model logic
- return a deterministic blocking response
- tell the operator to reconnect browser runtime first

### B2. Keep read-only actions available

Do not block:

- browser status reads
- loading existing session/plan data
- other read-only monitoring actions

The operator still needs visibility while the runtime is down.

## Track C - Operator surface

### C1. Keyword screen

Show readiness truth before the user starts topic analysis:

- current browser state
- summary of why research can or cannot start
- direct next-step guidance

### C2. Plan screen

Show the same readiness truth before plan generation/refinement so the operator understands why the system blocks.

## Exit criteria

- planner actions short-circuit when runtime is not runnable
- the UI shows readiness truth before research kickoff
- production rerun proves the system stops earlier than the Phase 13 flow
