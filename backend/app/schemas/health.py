from __future__ import annotations

from pydantic import BaseModel


class HealthStatusResponse(BaseModel):
    status: str
    cooldown_until: str | None
    last_signal: dict[str, str] | None


class HealthResetResponse(BaseModel):
    status: str
