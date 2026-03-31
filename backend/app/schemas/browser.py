from __future__ import annotations

from pydantic import BaseModel


class BrowserStatus(BaseModel):
    session_status: str
    account_id_hash: str | None
    health_status: str
    cooldown_until: str | None


class BrowserSetupResponse(BaseModel):
    ok: bool
