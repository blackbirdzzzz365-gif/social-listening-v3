VALIDITY_SPEC_BUILDER

You compile one research-aware `validity_spec` for a social listening run.

Return strict JSON only. No markdown. No prose outside JSON.

Output schema:
{
  "research_objective": "string",
  "target_signal_types": ["string"],
  "target_author_types": ["string"],
  "non_target_author_types": ["string"],
  "must_have_signals": ["string"],
  "nice_to_have_signals": ["string"],
  "hard_reject_signals": ["string"],
  "comment_policy": {
    "allow_parent_context": true,
    "reject_transactional_only_comments": true,
    "minimum_comment_text_length": 8
  },
  "valid_examples": ["string"],
  "invalid_examples": ["string"],
  "batch_policy": {
    "min_accept_ratio": 0.15,
    "min_high_conf_accept_ratio": 0.05,
    "max_consecutive_weak_batches": 2,
    "uncertain_reformulation_floor": 0.25
  }
}

Rules:
- Use the full research context, clarification history, keywords, and retrieval profile.
- Optimize for real end-user research value, not broad topic match.
- Keep arrays concise and specific.
- Prefer concrete reject signals such as pure promotion, seller CTA, price-only inquiry, inbox-only request, duplicate thread noise.
- For comment_policy, reject short transactional-only comments when the run is insight-oriented.
- Do not include fields outside the schema above.
