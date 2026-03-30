from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.action_registry import get_action_spec


class KeywordMap(BaseModel):
    brand: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    sentiment: list[str] = Field(default_factory=list)
    behavior: list[str] = Field(default_factory=list)
    comparison: list[str] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    topic: str


class ClarificationTurn(BaseModel):
    question: str
    answer: str


class ClarificationAnswerRequest(BaseModel):
    answers: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    context_id: str
    topic: str
    status: str
    clarifying_questions: list[str] | None
    keywords: KeywordMap | None
    retrieval_profile: dict[str, Any] | None = None
    clarification_history: list[ClarificationTurn] = Field(default_factory=list)


class KeywordUpdateRequest(BaseModel):
    keywords: KeywordMap


class PlanCreateRequest(BaseModel):
    context_id: str


class PlanRefineRequest(BaseModel):
    instruction: str


class PlanStepSchema(BaseModel):
    step_id: str
    step_order: int
    action_type: str
    read_or_write: str
    target: str
    estimated_count: int | None
    estimated_duration_sec: int | None
    risk_level: str
    dependency_step_ids: list[str] = Field(default_factory=list)
    explain: str = ""

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        spec = get_action_spec(value)
        if spec is None:
            raise ValueError(f"unsupported action_type: {value}")
        return spec.action_type


class PlanResponse(BaseModel):
    plan_id: str
    context_id: str
    version: int
    status: str
    steps: list[PlanStepSchema]
    estimated_total_duration_sec: int
    warnings: list[str] = Field(default_factory=list)
    diff_summary: str | None = None


class ApprovalRequest(BaseModel):
    step_ids: list[str]


class ApprovalGrantResponse(BaseModel):
    grant_id: str
    approved_step_ids: list[str]
    plan_version: int
    approver_id: str
    approved_at: str
