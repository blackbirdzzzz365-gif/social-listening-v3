from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.browser import BrowserSetupResponse, BrowserStatus
from app.services.runtime_readiness import build_runtime_readiness_payload

router = APIRouter(prefix="/api/browser", tags=["browser"])


class BrowserSetupHub:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[tuple[str, dict[str, Any]]]] = []

    def subscribe(self) -> asyncio.Queue[tuple[str, dict[str, Any]]]:
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[tuple[str, dict[str, Any]]]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            await queue.put((event, payload))


@router.get("/status", response_model=BrowserStatus)
async def browser_status(request: Request) -> BrowserStatus:
    state = request.app.state.health_monitor.get_browser_runtime_state()
    payload = build_runtime_readiness_payload(state)
    payload["account_id_hash"] = state.account_id_hash
    payload["cooldown_until"] = state.cooldown_until
    return BrowserStatus(**payload)


@router.post("/setup", response_model=BrowserSetupResponse)
async def browser_setup(request: Request) -> BrowserSetupResponse:
    app = request.app
    task = getattr(app.state, "browser_setup_task", None)
    if task is not None and not task.done():
        return BrowserSetupResponse(ok=True)

    async def run_setup() -> None:
        try:
            await app.state.browser_setup_hub.publish("browser_opened", {})
            await app.state.browser_agent.start()
            account_id_hash = await app.state.browser_agent.wait_for_login()
            app.state.health_monitor.mark_session_valid(account_id_hash)
            await app.state.browser_setup_hub.publish(
                "login_detected",
                {"account_id_hash": account_id_hash},
            )
            await app.state.browser_setup_hub.publish(
                "setup_complete",
                {"session_status": "VALID"},
            )
        except Exception as exc:
            await app.state.browser_setup_hub.publish(
                "setup_failed",
                {"reason": str(exc)},
            )
            raise

    app.state.browser_setup_task = asyncio.create_task(run_setup())
    return BrowserSetupResponse(ok=True)


@router.get("/setup/stream")
async def browser_setup_stream(request: Request) -> StreamingResponse:
    queue = request.app.state.browser_setup_hub.subscribe()

    async def event_stream():
        try:
            while True:
                event, payload = await queue.get()
                yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
        finally:
            request.app.state.browser_setup_hub.unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
