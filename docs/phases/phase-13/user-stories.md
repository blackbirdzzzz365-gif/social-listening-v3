# User Stories - Phase 13

## Epic

Truthful browser session state and explicit re-auth admission for production runs.

## Stories

### Story 1 - Block doomed runs before step-1

As an operator, I want browser-backed runs to be blocked before execution when the Facebook session is expired so that production does not waste time on doomed runs.

Acceptance criteria:

- Given the account session is expired, when a browser-backed run is started, then the run does not enter `step-1`.
- The run exposes a deterministic auth-required outcome instead of a generic step failure.

### Story 2 - Degrade health truth immediately on expiry

As a production system, I want session expiry to update health truth immediately so that monitor and admission use the same reality.

Acceptance criteria:

- Given a browser action detects session expiry, when the failure is raised, then health state is updated to a non-runnable auth-required state in the same incident window.
- `HEALTHY + EXPIRED` is not emitted afterward.

### Story 3 - Show operator what to do next

As an operator, I want the monitor to show that re-authentication is required so that I know the next action without reading logs.

Acceptance criteria:

- Browser status and run details show session truth, runnable status, and action required.
- The monitor uses a distinct presentation for auth-required outcomes.

### Story 4 - Preserve healthy control flows

As a product owner, I want valid-session runs to keep the same answer-ready and no-answer outcomes so that Phase 13 only fixes auth truthfulness without regressing Phase 12 behavior.

Acceptance criteria:

- A valid-session no-answer control case still reaches the Phase 12 no-answer payload path.
- A valid-session answer case still reaches its normal retrieval and closeout path.
