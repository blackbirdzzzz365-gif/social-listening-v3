# BA Problem Brief - Phase 11

## Problem statement

The product now controls execution better than before, but two failure patterns still block user value:

1. Planner instability before run start
2. Image-bearing retrieval that appears active in heartbeat but ends with zero persisted evidence

For the user, both problems look like "the system still did not answer my question", even when the runtime internally did meaningful work.

## Who is affected

- Operator running live production research cases
- End user waiting for a market answer
- Team auditing whether the latest phase actually improved production truth

## Business risk

- Provider overload can make onboarding a topic or clarifying it feel unreliable.
- Image-bearing use cases remain unproven, which weakens confidence in beauty, scam-proof, screenshot-heavy, and before-after research scenarios.
- Timeout without salvage hides whether budget was wasted or evidence was actually found but dropped.

## User need

The user does not need "more AI". The user needs:

- planning that survives transient provider trouble
- evidence acquisition that works for image-heavy topics
- auditability when the run stops before persistence

## Desired product behavior

- If provider overload is temporary, the planner should retry and recover automatically.
- If the planner still fails, the API should say the failure is planner/provider related, not a generic validation error.
- If an image-bearing search is collecting posts but times out, the operator should still see what was collected and what portion was persisted.
- If image-bearing evidence does not exist, the product should be able to conclude that clearly instead of only failing silently.

## Phase 11 business outcome

Phase 11 is successful when the product moves from:

- "text-led cases can answer, image-led cases are ambiguous"

to:

- "both planning and image-bearing retrieval have explicit resilience and auditability contracts"
