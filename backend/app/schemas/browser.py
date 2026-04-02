from __future__ import annotations

from pydantic import BaseModel, Field


class BrowserStatus(BaseModel):
    runnable: bool
    session_status: str
    account_id_hash: str | None
    health_status: str
    cooldown_until: str | None
    last_checked: str | None = None
    action_required: str | None = None
    block_reason: str | None = None
    summary: str
    next_steps: list[str] = Field(default_factory=list)


class BrowserSetupResponse(BaseModel):
    ok: bool
