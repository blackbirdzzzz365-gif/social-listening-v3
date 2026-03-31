from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


JudgeDecision = Literal["ACCEPTED", "REJECTED", "UNCERTAIN"]


class CommentPolicy(BaseModel):
    allow_parent_context: bool = True
    reject_transactional_only_comments: bool = True
    minimum_comment_text_length: int = 8


class BatchPolicy(BaseModel):
    min_accept_ratio: float = 0.15
    min_high_conf_accept_ratio: float = 0.05
    max_consecutive_weak_batches: int = 2
    uncertain_reformulation_floor: float = 0.25


class ValiditySpec(BaseModel):
    spec_id: str
    spec_version: str
    research_objective: str
    target_signal_types: list[str] = Field(default_factory=list)
    target_author_types: list[str] = Field(default_factory=list)
    non_target_author_types: list[str] = Field(default_factory=list)
    must_have_signals: list[str] = Field(default_factory=list)
    nice_to_have_signals: list[str] = Field(default_factory=list)
    hard_reject_signals: list[str] = Field(default_factory=list)
    comment_policy: CommentPolicy = Field(default_factory=CommentPolicy)
    valid_examples: list[str] = Field(default_factory=list)
    invalid_examples: list[str] = Field(default_factory=list)
    batch_policy: BatchPolicy = Field(default_factory=BatchPolicy)


class JudgeResult(BaseModel):
    spec_id: str
    content_id: str
    decision: JudgeDecision
    relevance_score: float = 0.0
    confidence_score: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)
    short_rationale: str = ""
    used_image_understanding: bool = False
    image_summary: str = ""
    model_family: str = ""
    model_version: str = ""
    policy_version: str = ""
    cache_key: str = ""
    provider_used: str | None = None
    fallback_used: bool = False
    batch_signal: str | None = None
    raw_response: dict[str, Any] | None = None

    @field_validator("relevance_score", "confidence_score", mode="before")
    @classmethod
    def clamp_score(cls, value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return max(0.0, min(1.0, numeric))
