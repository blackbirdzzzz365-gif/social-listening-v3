from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunStartRequest(BaseModel):
    plan_id: str
    grant_id: str


class StepRunSchema(BaseModel):
    step_run_id: str
    step_id: str
    action_type: str
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    read_or_write: str
    target: str
    actual_count: int | None
    error_message: str | None
    checkpoint: dict[str, Any] | None = None


class RunResponse(BaseModel):
    run_id: str
    plan_id: str
    grant_id: str
    plan_version: int
    status: str
    completion_reason: str | None = None
    failure_class: str | None = None
    answer_status: str | None = None
    answer_generated_at: str | None = None
    started_at: str
    ended_at: str | None
    total_records: int
    steps: list[StepRunSchema] = Field(default_factory=list)
