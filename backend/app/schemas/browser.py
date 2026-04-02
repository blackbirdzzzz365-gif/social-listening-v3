from __future__ import annotations

from pydantic import BaseModel


class BrowserStatus(BaseModel):
    session_status: str
    account_id_hash: str | None
    health_status: str
    cooldown_until: str | None
    last_checked: str | None = None
    runnable: bool
    action_required: str | None = None
    block_reason: str | None = None


class BrowserSetupResponse(BaseModel):
    ok: bool
