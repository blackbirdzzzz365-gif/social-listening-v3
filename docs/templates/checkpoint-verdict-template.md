# Checkpoint Verdict Template

Dung template nay sau buoc production audit, truoc khi branch hoac code.

```markdown
# Checkpoint Verdict - <phase-or-fix-name>

## Context
- Current phase:
- Branch under review:
- Case pack:
- Run ids:
- Report root:

## Expectation vs Actual
- Expected:
- Actual:
- Delta:

## Per-Case Summary
| Case | Run ID | Result | Key Evidence | Gap |
|------|--------|--------|--------------|-----|
| ...  | ...    | ...    | ...          | ... |

## User Problem Solved Or Not
- Verdict:
- Why:

## Root Cause And Assumptions
- Root cause:
- Hidden assumptions:
- Measurement gaps:

## What Should Remain Unchanged
- ...

## Route Decision
- `evidence-weak` | `contained-fix` | `new-phase`
- Why:

## Recommended Next Action
- Suggested scope:
- Suggested owner flow:
- Suggested docs to create/update:
```
