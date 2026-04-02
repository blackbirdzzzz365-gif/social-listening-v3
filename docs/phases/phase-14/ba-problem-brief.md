# BA Problem Brief - Phase 14

## Problem statement

The product already knows how to end a browser-backed run with `REAUTH_REQUIRED` once execution begins.  
It still does not stop the operator early enough.

When the browser runtime is not runnable:

- the operator can still start topic analysis
- the system can still spend planning cost
- the operator only learns the truth later in the flow

That creates wasted time, wasted model cost, and a misleading expectation that research is ready to start.

## User problem

As an operator, I need the product to tell me immediately whether research can actually run, before I invest effort in topic setup and planning.

## Business impact

- unnecessary planner spend when runtime is down
- slower time to useful insight
- lower trust in the product because the system appears to accept work it cannot execute

## Desired outcome

- readiness truth is visible before kickoff
- planner-heavy actions are blocked when runtime is not runnable
- user receives a clear action request such as `CONNECT_FACEBOOK` or `REAUTH_REQUIRED`

## Non-goals

- solving session refresh automatically
- changing the planner's semantic quality
- changing downstream labeling/theme logic
