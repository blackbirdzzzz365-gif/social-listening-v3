from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.event_bus import EventBus, HealthChangedEvent, HealthSignal
from app.infrastructure.database import SessionLocal
from app.models.health import AccountHealthLog, AccountHealthState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass
class BrowserRuntimeState:
    session_status: str
    account_id_hash: str | None
    health_status: str
    cooldown_until: str | None
    last_checked: str | None
    runnable: bool
    action_required: str | None
    block_reason: str | None


def _normalize_health_state(state: AccountHealthState) -> bool:
    changed = False
    if state.session_status == "EXPIRED" and state.status == "HEALTHY":
        state.status = "CAUTION"
        changed = True
    return changed


def _derive_browser_runtime_state(state: AccountHealthState) -> BrowserRuntimeState:
    session_status = state.session_status or "NOT_SETUP"
    health_status = state.status or "HEALTHY"
    runnable = True
    action_required: str | None = None
    block_reason: str | None = None

    if session_status == "NOT_SETUP":
        runnable = False
        action_required = "CONNECT_FACEBOOK"
        block_reason = "session_not_setup"
    elif session_status == "EXPIRED":
        runnable = False
        action_required = "REAUTH_REQUIRED"
        block_reason = "session_expired"
    elif health_status == "BLOCKED":
        runnable = False
        action_required = "WAIT_COOLDOWN" if state.cooldown_until else "MANUAL_RESET_REQUIRED"
        block_reason = "account_blocked"

    return BrowserRuntimeState(
        session_status=session_status,
        account_id_hash=state.account_id_hash,
        health_status=health_status,
        cooldown_until=state.cooldown_until,
        last_checked=state.last_checked,
        runnable=runnable,
        action_required=action_required,
        block_reason=block_reason,
    )


def ensure_health_state(session: Session) -> AccountHealthState:
    state = session.get(AccountHealthState, 1)
    if state is None:
        state = AccountHealthState(
            id=1,
            status="HEALTHY",
            session_status="NOT_SETUP",
            updated_at=utc_now_iso(),
        )
        session.add(state)
        session.commit()
        session.refresh(state)
    elif _normalize_health_state(state):
        state.updated_at = utc_now_iso()
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


class HealthMonitorService:
    def __init__(self, event_queue: asyncio.Queue[HealthSignal], event_bus: EventBus) -> None:
        self._event_queue = event_queue
        self._event_bus = event_bus
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._monitor_loop())

        with SessionLocal() as session:
            ensure_health_state(session)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _monitor_loop(self) -> None:
        while True:
            signal = await self._event_queue.get()
            try:
                await self.process_signal(signal)
            finally:
                self._event_queue.task_done()

    async def process_signal(self, signal: HealthSignal) -> AccountHealthState:
        with SessionLocal() as session:
            state = ensure_health_state(session)
            status_before = state.status
            now = signal.detected_at or utc_now()
            cooldown_until: datetime | None = None

            if signal.signal_type == "CAPTCHA":
                state.status = "BLOCKED"
                cooldown_until = now + timedelta(hours=24)
            elif signal.signal_type in {"ACTION_BLOCKED", "RATE_LIMIT", "REDUCED_REACH"}:
                state.status = "CAUTION"
                cooldown_until = now + timedelta(hours=1)
            elif signal.signal_type == "SESSION_EXPIRED":
                state.session_status = "EXPIRED"
                if state.status == "HEALTHY":
                    state.status = "CAUTION"
            elif signal.signal_type == "MANUAL_RESET":
                state.status = "HEALTHY"
                cooldown_until = None

            if signal.signal_type != "SESSION_EXPIRED":
                state.cooldown_until = cooldown_until.isoformat() if cooldown_until else None

            state.last_checked = now.isoformat()
            state.updated_at = now.isoformat()

            log = AccountHealthLog(
                log_id=str(uuid4()),
                signal_type=signal.signal_type,
                status_before=status_before,
                status_after=state.status,
                detected_at=now.isoformat(),
                action_taken="state_transition",
                cooldown_until=state.cooldown_until,
                raw_signal=json.dumps(signal.raw_signal or {}),
            )
            session.add(log)
            session.add(state)
            session.commit()
            session.refresh(state)

        await self._event_bus.emit(
            HealthChangedEvent(
                new_status=state.status,
                signal_type=signal.signal_type,
                cooldown_until=parse_dt(state.cooldown_until),
            )
        )
        return state

    def get_status_snapshot(self) -> tuple[AccountHealthState, AccountHealthLog | None]:
        with SessionLocal() as session:
            state = ensure_health_state(session)
            log = session.execute(
                select(AccountHealthLog).order_by(AccountHealthLog.detected_at.desc())
            ).scalars().first()
            session.expunge(state)
            if log is not None:
                session.expunge(log)
            return state, log

    def get_browser_runtime_state(self) -> BrowserRuntimeState:
        with SessionLocal() as session:
            state = ensure_health_state(session)
            runtime_state = _derive_browser_runtime_state(state)
            session.expunge(state)
            return runtime_state

    def is_browser_runnable(self) -> bool:
        return self.get_browser_runtime_state().runnable

    def is_write_allowed(self) -> bool:
        state, _ = self.get_status_snapshot()
        cooldown_until = parse_dt(state.cooldown_until)
        if cooldown_until and cooldown_until <= utc_now():
            return True
        return state.status == "HEALTHY"

    def mark_session_valid(self, account_id_hash: str) -> AccountHealthState:
        with SessionLocal() as session:
            state = ensure_health_state(session)
            state.session_status = "VALID"
            state.status = "HEALTHY"
            state.account_id_hash = account_id_hash
            state.cooldown_until = None
            state.last_checked = utc_now_iso()
            state.updated_at = utc_now_iso()
            session.add(state)
            session.commit()
            session.refresh(state)
            session.expunge(state)
            return state

    async def mark_session_expired(self, raw_signal: dict | None = None) -> BrowserRuntimeState:
        await self.process_signal(HealthSignal(signal_type="SESSION_EXPIRED", raw_signal=raw_signal or {}))
        return self.get_browser_runtime_state()

    async def reset(self, confirm: bool) -> AccountHealthState:
        if not confirm:
            raise ValueError("confirm must be true")

        with SessionLocal() as session:
            state = ensure_health_state(session)
            cooldown_until = parse_dt(state.cooldown_until)
            if state.status == "BLOCKED" and cooldown_until and cooldown_until > utc_now():
                raise ValueError("cooldown not expired")

        return await self.process_signal(HealthSignal(signal_type="MANUAL_RESET"))

    def acknowledge(self, signal_log_id: str) -> None:
        with SessionLocal() as session:
            log = session.get(AccountHealthLog, signal_log_id)
            if log is None:
                return
            log.action_taken = "acknowledged"
            session.add(log)
            session.commit()
