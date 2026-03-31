from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.label_taxonomy import (
    AUTHOR_ROLES,
    COMMERCIALITY_LEVELS,
    CONTENT_INTENTS,
    LABEL_SOURCES,
    USER_FEEDBACK_RELEVANCE_LEVELS,
    sql_enum,
)
from app.models.base import Base


class ContentLabel(Base):
    __tablename__ = "content_labels"
    __table_args__ = (
        CheckConstraint(
            f"author_role IN ({sql_enum(AUTHOR_ROLES)})",
            name="ck_content_labels_author_role",
        ),
        CheckConstraint(
            f"content_intent IN ({sql_enum(CONTENT_INTENTS)})",
            name="ck_content_labels_content_intent",
        ),
        CheckConstraint(
            f"commerciality_level IN ({sql_enum(COMMERCIALITY_LEVELS)})",
            name="ck_content_labels_commerciality_level",
        ),
        CheckConstraint(
            f"user_feedback_relevance IN ({sql_enum(USER_FEEDBACK_RELEVANCE_LEVELS)})",
            name="ck_content_labels_user_feedback_relevance",
        ),
        CheckConstraint(
            f"label_source IN ({sql_enum(LABEL_SOURCES)})",
            name="ck_content_labels_label_source",
        ),
    )

    label_id: Mapped[str] = mapped_column(Text, primary_key=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("crawled_posts.post_id"), nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("plan_runs.run_id"), nullable=False)
    label_job_id: Mapped[str] = mapped_column(ForeignKey("label_jobs.label_job_id"), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(Text, nullable=False)
    author_role: Mapped[str] = mapped_column(Text, nullable=False)
    content_intent: Mapped[str] = mapped_column(Text, nullable=False)
    commerciality_level: Mapped[str] = mapped_column(Text, nullable=False)
    user_feedback_relevance: Mapped[str] = mapped_column(Text, nullable=False)
    label_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    label_reason: Mapped[str] = mapped_column(Text, nullable=False)
    label_source: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(Text)
    model_version: Mapped[Optional[str]] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default="CURRENT_TIMESTAMP")
