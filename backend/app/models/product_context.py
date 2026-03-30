from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProductContext(Base):
    __tablename__ = "product_contexts"

    context_id: Mapped[str] = mapped_column(Text, primary_key=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    keyword_json: Mapped[str | None] = mapped_column(Text)
    retrieval_profile_json: Mapped[str | None] = mapped_column(Text)
    clarifying_question_json: Mapped[str | None] = mapped_column(Text)
    clarification_history_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
