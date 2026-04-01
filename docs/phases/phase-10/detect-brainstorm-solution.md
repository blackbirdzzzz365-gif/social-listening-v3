# Detect -> Brainstorm -> Proposed Direction

## Detect

Phase 9 production showed a misleading pattern:

- retrieval and judging were improving
- but the operator still could not trust runtime truth

The real blocker to the next learning loop was not planner quality first.
It was execution ambiguity.

## Options Considered

### Option A - Improve retrieval again first

Examples:

- more semantic query families
- richer source memory
- stronger image-first retrieval heuristics

Why not first:

- production truth was still corrupted by cancel leakage and silent steps
- better retrieval on top of weak runtime control only creates noisier audits

### Option B - Focus only on answer closeout

Why not alone:

- answer closeout cannot be measured reliably if the run is manually cancelled because the operator cannot tell whether the step is truly hung

### Option C - Execution control + observability first

This is the chosen direction because it unlocks cleaner truth for every later phase:

- safe stop semantics
- visible progress
- explicit timeout class
- aligned audit tooling
- then re-measure answer and vision on top of a more trustworthy runtime

## What Should Remain Unchanged

- Phase 8 validity-spec and judge model contract
- Phase 9 admission control for shared browser profile
- selective expansion and deterministic/model gating logic
- current deploy pipeline and production case-pack workflow

## Proposed Direction

Phase 10 should be a contained runtime-control phase:

1. add `CANCELLING`
2. wrap long browser actions with heartbeat and timeout control
3. stop persistence after stop requests
4. fix audit tooling and live monitor observability
5. rerun one answer-closeout case and one image-bearing case on production

## Why This Is The Right Phase Boundary

If Phase 10 passes:

- the team can trust production evidence again
- future retrieval or answer-quality phases can be evaluated with less operator noise

If Phase 10 fails:

- that failure will still be valuable because it isolates runtime-control debt directly instead of hiding it inside another retrieval iteration
