from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AccountHealthLog(Base):
    __tablename__ = "account_health_log"
    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('CAPTCHA','ACTION_BLOCKED','RATE_LIMIT','REDUCED_REACH','SESSION_EXPIRED','MANUAL_RESET')",
            name="ck_account_health_log_signal_type",
        ),
    )

    log_id: Mapped[str] = mapped_column(Text, primary_key=True)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    status_before: Mapped[str] = mapped_column(Text, nullable=False)
    status_after: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
    )
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    cooldown_until: Mapped[Optional[str]] = mapped_column(Text)
    raw_signal: Mapped[Optional[str]] = mapped_column(Text)


class AccountHealthState(Base):
    __tablename__ = "account_health_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_account_health_state_singleton"),
        CheckConstraint(
            "status IN ('HEALTHY','CAUTION','BLOCKED')",
            name="ck_account_health_state_status",
        ),
        CheckConstraint(
            "session_status IN ('NOT_SETUP','VALID','EXPIRED')",
            name="ck_account_health_state_session_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="HEALTHY")
    session_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="NOT_SETUP",
    )
    account_id_hash: Mapped[Optional[str]] = mapped_column(Text)
    last_checked: Mapped[Optional[str]] = mapped_column(Text)
    cooldown_until: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
    )
