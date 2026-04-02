# Phase 15 Improvement Handoff - 2026-04-02

## Current repo truth

- `main` is now aligned to `origin/main` on top of Phase 14 runtime-readiness work.
- `.phase.json` currently points to `phase-14` as the active phase.
- The latest merged production hardening after Phase 14 includes:
  - xAI as the default provider for text-model interactions
  - fixed monitor log containers so streaming panels stay inside a bounded frame
  - numeric step ordering in the monitor/API so `step-10` no longer renders under `step-1`
  - retrieval reformulation that keeps product context instead of collapsing to generic brand-only anchors
  - early source prefiltering for obvious broker groups and official brand pages before model judging

## Production findings worth carrying forward

### Confirmed wins

- `run-4d39fe2818` proved the no-answer closeout path now reaches a real terminal user-facing outcome instead of only a badge.
- The monitor sorting bug was a presentation issue, not an execution-order issue, and is already fixed in `main`.
- Streaming-heavy monitor sections are now usable because they scroll inside fixed containers.

### Remaining retrieval gap

- `run-09553668ed` showed that the system can still collect a large amount of noise while missing the user voice that actually answers the research goal.
- The main failure pattern was not raw crawler failure. It was intent drift:
  - the user wanted comparison signals about Shinhan versus other banks
  - the run opened with broad brand/product queries
  - reformulation drift and source drift pulled the run toward broker groups, official pages, Shinhan Life, and transactional CTA content
  - accepted evidence stayed at zero even while records accumulated

### Important execution observation

- `step-2` and `step-10` were absent from the approval grant for the problematic run.
- That matters because this case needs both:
  - comment crawling on initial post hits
  - search-in-group expansion for community discussion pockets
- The approval UI defaults to all selected, so the missing steps look like operator selection drift rather than a planner/executor bug.

## Why early filtering is the right strategy

Early filtering is the correct direction for this product, but only when it stays conservative and goal-aware.

### Why it helps

- The dominant waste pattern here starts at the source layer, not at the final judge layer.
- If a source is obviously a broker lead-gen group or an official brand page for a consumer-comparison objective, spending browser time and model tokens on it is low-value.
- Filtering early preserves budget for the harder part: finding real user experience, comparisons, objections, and comment-level nuance.

### Why it must stay narrow

- Over-filtering too early would hide edge cases where a useful comparison signal appears in an unexpected place.
- The filter should be driven by the active `validity_spec` and research goal, not by hard-coded global bans.
- Filtered records should remain auditable so operators can see what was skipped and why.

## Recommended Phase 15 direction

The next phase should focus on retrieval intent alignment, not another generic platform hardening pass.

### Proposed goal

Improve the probability that a run finds the right posts and comments for the user need before the plan budget is exhausted.

### Proposed scope

- Query ordering that prioritizes comparison-intent queries before broad brand queries when the user asks for bank-vs-bank evaluation.
- Planner guidance that preserves product and comparison context across reformulations.
- Spec-aware source ranking:
  - boost review/community/discussion sources
  - demote broker lead-gen groups and official brand pages for end-user comparison jobs
- Approval safety on high-value retrieval branches:
  - make omitted `CRAWL_COMMENTS` and `SEARCH_IN_GROUP` more visible
  - consider guardrails or warnings when a comparative case is approved without those steps
- Success telemetry focused on accepted user-voice evidence, not only total collected records

## Suggested success criteria for the next phase

- Comparative banking cases surface accepted posts or comments from real users earlier in the run.
- Runs spend less budget on broker/CTA noise before the first accepted evidence appears.
- Comment crawl and in-group search are not silently lost on comparison-oriented plans.
- Operators can explain why evidence was skipped at the source-prefilter layer.

## Next restart point

When work resumes, start from this order:

1. Review this handoff and the recent noisy-case reports.
2. Lock a Phase 15 brief around retrieval intent alignment.
3. Implement planner/query-order changes before widening model heuristics again.
