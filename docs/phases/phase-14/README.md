# Phase 14 - Research Runtime Readiness And Kickoff Gate

## Why this phase exists

Phase 13 fixed the old failure mode where a browser-backed run could reach `step-1` and then die with a generic auth error.

The new production truth exposed a different waste pattern:

- the system can still spend planner cost on topic analysis, clarification, and plan generation
- only after that does the run get blocked by `REAUTH_REQUIRED`
- when the browser runtime is already not runnable, the user still goes through too much workflow before learning the truth

This is not a retrieval-quality problem. It is a kickoff-contract problem.

## Locked direction

- Browser readiness must be checked before the product starts planner-heavy research work.
- Topic analysis and plan generation must short-circuit when browser runtime is not runnable.
- Operator UI must show readiness truth directly on the keyword and plan surfaces.
- Once browser runtime becomes runnable again, the existing Phase 13+ business flow must continue unchanged.

## Expected outcomes

- A non-runnable browser runtime blocks topic analysis before `analyze_topic` spends model cost.
- Clarification and plan generation are also blocked when runtime is not runnable.
- UI surfaces `session_status`, `health_status`, `action_required`, and concrete next steps before the user tries to continue.
- Production no longer creates a new context/plan just to immediately end in `REAUTH_REQUIRED`.

## Scope

### In scope

- shared runtime readiness contract for planning surfaces
- early gate on session kickoff, clarification submit, and plan generation/refinement
- readiness payload in session/plan/browser responses
- keyword and plan UI readiness surface
- Phase 14 case pack and production revalidation

### Out of scope

- fixing Facebook login automation itself
- new retrieval heuristics or new query families
- changes to downstream run execution once runtime is valid
- image-bearing acquisition work

## Success criteria

- Production returns an early explicit runtime-not-ready outcome before planner cost is spent.
- Browser readiness is visible to the operator on the main research kickoff screens.
- No regressions are introduced for valid runtime cases.
- The next rerun clearly proves whether the system now stops earlier than Phase 13.
