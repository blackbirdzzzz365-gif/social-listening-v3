# Checkpoint Verdict - phase-11

## Context
- Current phase: `phase-11`
- Branch under review: `main` at deployed SHA `5192868`
- Case pack: [phase-11-core.json](/Users/nguyenquocthong/project/social-listening-v3/docs/production/case-packs/phase-11-core.json)
- Run ids:
  - `run-a1c111f7a5`
  - `run-0b5516a1d6`
- Report root: [reports/production](/Users/nguyenquocthong/project/social-listening-v3/reports/production)

## Expectation vs Actual
- Expected:
  - Planner/session/clarification/plan generation should survive provider turbulence and expose planner metadata in production.
  - Image-bearing retrieval should start from a more visual posture and either persist candidates or at least fail with auditable salvage truth.
  - Phase 9 answer closeout should still work after the new planner and retrieval changes.
- Actual:
  - `run-a1c111f7a5` finished `DONE / ANSWER_READY`, persisted `174` records, produced `13 ACCEPTED`, completed label job `13/13`, and wrote `3` theme results.
  - `run-a1c111f7a5` also showed reason-aware reformulation in production, including a jump from weak brand-generic retrieval to stronger trust/fraud postures like `FE Credit bi lua`.
  - `run-0b5516a1d6` finished `FAILED / STEP_STUCK_TIMEOUT`; `step-1 SEARCH_POSTS` collected `54` raw posts, saw `53` image candidates, and preserved timeout salvage with `lost_before_persist_count=54`.
  - `run-0b5516a1d6` still persisted `0` candidates and never reached deterministic judging, image-understanding usage, or answer closeout.

## Per-Case Summary
| Case | Run ID | Result | Key Evidence | Gap |
|------|--------|--------|--------------|-----|
| `phase11-planner-resilience-fe-credit` | `run-a1c111f7a5` | Success | `DONE`, `completion_reason=ANSWER_READY`, `answer_status=ANSWER_READY`, `13 ACCEPTED`, `label_jobs DONE`, `theme_results=3`, planner metadata present, reformulation observed | late `SEARCH_IN_GROUP` and comparison paths still spent budget after the answer was already recoverable |
| `phase11-image-bearing-ngu-hoa` | `run-0b5516a1d6` | Failed but informative | `FAILED / STEP_STUCK_TIMEOUT`, salvage captured `collected_count=54`, `image_candidate_count=53`, `persisted_count=0`, planner metadata present | image-bearing evidence acquisition is still not business-viable because nothing persisted or reached image-aware judging |

## User Problem Solved Or Not
- Verdict:
  - `Partially solved`
- Why:
  - For text-led research and provider-resilient planning, Phase 11 materially improved the product and proved end-to-end answer delivery.
  - For a user asking for visual before/after proof or image-backed product review truth, the product still fails before it can produce a usable answer.

## Root Cause And Assumptions
- Root cause:
  - Image-bearing retrieval still starts too broad and spends the full `300s` timeout budget collecting visually related but semantically weak raw posts.
  - The product has no intermediate persistence layer before full batch scoring, so timeout happens before any collected image-bearing candidates become auditable records.
  - Clarification for image-bearing topics still collapses to generic answers, which keeps the planner under-specified on exact product variant, platform, effect, and user type.
- Hidden assumptions:
  - A visually-oriented topic can succeed by only changing query families without also narrowing semantic intent and source strategy.
  - Timeout salvage alone is enough to claim image-bearing evidence acquisition is production-ready.
  - Once provider resilience is fixed, image-bearing retrieval will naturally converge without a more goal-aware execution policy.
- Measurement gaps:
  - We still do not measure `image-bearing hit quality`, only raw `image_candidate_count`.
  - We do not distinguish “visual candidate found but not persisted” from “no visual candidate found”.
  - We do not yet stop the plan once a text-led run already has enough high-confidence evidence to answer.

## What Should Remain Unchanged
- Keep planner resilience metadata and HTTP `503` mapping for provider-classified failures.
- Keep the single-flight browser admission contract from earlier phases.
- Keep timeout taxonomy and salvage payloads; `run-0b5516a1d6` proved they add real operator truth.
- Keep answer closeout from accepted records to labels/themes; `run-a1c111f7a5` proved that path still works after Phase 11 changes.
- Keep reason-aware reformulation and query-family routing for trust/fraud/complaint use cases; the FE Credit run showed real uplift from it.

## Route Decision
- `new-phase`
- Why:
  - The remaining gap is not a contained bug.
  - It crosses retrieval strategy, intermediate persistence, and goal-aware stopping for visual-review topics.
  - Phase 11 made the failure observable; the next phase must make the image-bearing user problem actually solvable.

## Recommended Next Action
- Suggested scope:
  - `Phase 12 - Goal-Aware Visual Evidence Acquisition`
- Suggested owner flow:
  - Route back into `social-listening-v3-product-loop`, lock `Chot huong: new-phase.`, then open `social-listening-v3-phase-executor` for Phase 12.
- Suggested docs to create/update:
  - `docs/phases/phase-12/README.md`
  - `docs/phases/phase-12/ba-problem-brief.md`
  - `docs/phases/phase-12/technical-solution.md`
  - `docs/phases/phase-12/user-stories.md`
  - `docs/phases/phase-12/checkpoints/README.md`
  - `docs/production/case-packs/phase-12-core.json`
