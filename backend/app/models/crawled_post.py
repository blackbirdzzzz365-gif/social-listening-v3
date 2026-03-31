from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.label_taxonomy import LABEL_RECORD_STATUSES, sql_enum
from app.models.base import Base


class CrawledPost(Base):
    __tablename__ = "crawled_posts"
    __table_args__ = (
        CheckConstraint(
            "record_type IN ('POST','COMMENT')",
            name="ck_crawled_posts_record_type",
        ),
        CheckConstraint(
            f"label_status IN ({sql_enum(LABEL_RECORD_STATUSES)})",
            name="ck_crawled_posts_label_status",
        ),
    )

    post_id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("plan_runs.run_id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(
        ForeignKey("step_runs.step_run_id"),
        nullable=False,
    )
    group_id_hash: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_masked: Mapped[str] = mapped_column(Text, nullable=False)
    record_type: Mapped[str] = mapped_column(Text, nullable=False, default="POST", server_default="POST")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    parent_post_id: Mapped[Optional[str]] = mapped_column(Text)
    parent_post_url: Mapped[Optional[str]] = mapped_column(Text)
    posted_at: Mapped[Optional[str]] = mapped_column(Text)
    reaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_stage: Mapped[Optional[str]] = mapped_column(Text)
    pre_ai_status: Mapped[Optional[str]] = mapped_column(Text)
    pre_ai_score: Mapped[Optional[float]] = mapped_column(Float)
    pre_ai_reason: Mapped[Optional[str]] = mapped_column(Text)
    judge_decision: Mapped[Optional[str]] = mapped_column(Text)
    judge_relevance_score: Mapped[Optional[float]] = mapped_column(Float)
    judge_confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    judge_reason_codes_json: Mapped[Optional[str]] = mapped_column(Text)
    judge_rationale: Mapped[Optional[str]] = mapped_column(Text)
    judge_used_image_understanding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    judge_image_summary: Mapped[Optional[str]] = mapped_column(Text)
    judge_model_family: Mapped[Optional[str]] = mapped_column(Text)
    judge_model_version: Mapped[Optional[str]] = mapped_column(Text)
    judge_policy_version: Mapped[Optional[str]] = mapped_column(Text)
    judge_cache_key: Mapped[Optional[str]] = mapped_column(Text)
    score_breakdown_json: Mapped[Optional[str]] = mapped_column(Text)
    quality_flags_json: Mapped[Optional[str]] = mapped_column(Text)
    query_family: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[Optional[str]] = mapped_column(Text)
    source_batch_index: Mapped[Optional[int]] = mapped_column(Integer)
    batch_decision: Mapped[Optional[str]] = mapped_column(Text)
    provider_used: Mapped[Optional[str]] = mapped_column(Text)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    label_status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING", server_default="PENDING")
    current_label_id: Mapped[Optional[str]] = mapped_column(ForeignKey("content_labels.label_id"))
    is_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exclude_reason: Mapped[Optional[str]] = mapped_column(Text)
    crawled_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
    )
