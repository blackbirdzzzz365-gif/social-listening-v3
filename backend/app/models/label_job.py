from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.label_taxonomy import LABEL_JOB_STATUSES, sql_enum
from app.models.base import Base


class LabelJob(Base):
    __tablename__ = "label_jobs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_enum(LABEL_JOB_STATUSES)})",
            name="ck_label_jobs_status",
        ),
        UniqueConstraint("run_id", "taxonomy_version", name="uq_label_jobs_run_taxonomy_version"),
    )

    label_job_id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("plan_runs.run_id"), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING", server_default="PENDING")
    records_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_labeled: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_fallback: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[Optional[str]] = mapped_column(Text)
    ended_at: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default="CURRENT_TIMESTAMP")
