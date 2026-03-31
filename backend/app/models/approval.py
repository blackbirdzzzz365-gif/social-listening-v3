from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApprovalGrant(Base):
    __tablename__ = "approval_grants"

    grant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.plan_id"), nullable=False)
    plan_version: Mapped[int] = mapped_column(nullable=False)
    approved_step_ids: Mapped[str] = mapped_column(Text, nullable=False)
    approver_id: Mapped[str] = mapped_column(Text, nullable=False, default="local_user")
    approved_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
    )
    expires_at: Mapped[Optional[str]] = mapped_column(Text)
    invalidated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invalidated_at: Mapped[Optional[str]] = mapped_column(Text)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(Text)
