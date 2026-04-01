from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlanRun(Base):
    __tablename__ = "plan_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','PAUSED','CANCELLING','DONE','FAILED','CANCELLED')",
            name="ck_plan_runs_status",
        ),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.plan_id"), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    grant_id: Mapped[str] = mapped_column(
        ForeignKey("approval_grants.grant_id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    completion_reason: Mapped[Optional[str]] = mapped_column(Text)
    failure_class: Mapped[Optional[str]] = mapped_column(Text)
    answer_status: Mapped[Optional[str]] = mapped_column(Text)
    answer_generated_at: Mapped[Optional[str]] = mapped_column(Text)
    answer_payload_json: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
    )
    ended_at: Mapped[Optional[str]] = mapped_column(Text)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StepRun(Base):
    __tablename__ = "step_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','RUNNING','DONE','FAILED','SKIPPED')",
            name="ck_step_runs_status",
        ),
    )

    step_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("plan_runs.run_id"), nullable=False)
    step_id: Mapped[str] = mapped_column(ForeignKey("plan_steps.step_id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[Optional[str]] = mapped_column(Text)
    ended_at: Mapped[Optional[str]] = mapped_column(Text)
    actual_count: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    checkpoint: Mapped[Optional[str]] = mapped_column(Text)
    checkpoint_json: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
