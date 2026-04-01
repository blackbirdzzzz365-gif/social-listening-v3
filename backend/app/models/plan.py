from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.action_registry import plan_step_action_check_constraint_sql
from app.models.base import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("status IN ('draft','ready','archived')", name="ck_plans_status"),
    )

    plan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    context_id: Mapped[str] = mapped_column(
        ForeignKey("product_contexts.context_id"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    generation_meta_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
    )


class PlanStep(Base):
    __tablename__ = "plan_steps"
    __table_args__ = (
        CheckConstraint(
            plan_step_action_check_constraint_sql(),
            name="ck_plan_steps_action_type",
        ),
        CheckConstraint(
            "read_or_write IN ('READ','WRITE')",
            name="ck_plan_steps_read_or_write",
        ),
        CheckConstraint(
            "risk_level IN ('LOW','MEDIUM','HIGH')",
            name="ck_plan_steps_risk_level",
        ),
    )

    step_id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.plan_id"), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    read_or_write: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_count: Mapped[Optional[int]] = mapped_column(Integer)
    estimated_duration_sec: Mapped[Optional[int]] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    dependency_step_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
