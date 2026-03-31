from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass


class BrowserRunAdmissionCancelled(RuntimeError):
    pass


class BrowserRunAdmissionPaused(RuntimeError):
    pass


@dataclass
class BrowserRunAdmissionSnapshot:
    owner_run_id: str | None
    queued_run_ids: list[str]


class BrowserRunAdmissionService:
    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._owner_run_id: str | None = None
        self._queue: deque[str] = deque()

    async def register(self, run_id: str) -> str:
        async with self._condition:
            if run_id != self._owner_run_id and run_id not in self._queue:
                self._queue.append(run_id)
            return "RUNNING" if self._owner_run_id is None and self._queue and self._queue[0] == run_id else "QUEUED"

    async def acquire(
        self,
        run_id: str,
        *,
        is_paused=None,
        should_cancel=None,
    ) -> None:
        async with self._condition:
            while True:
                if callable(should_cancel) and should_cancel():
                    self._discard(run_id)
                    self._condition.notify_all()
                    raise BrowserRunAdmissionCancelled(run_id)
                if callable(is_paused) and is_paused():
                    raise BrowserRunAdmissionPaused(run_id)
                if self._owner_run_id is None and self._queue and self._queue[0] == run_id:
                    self._queue.popleft()
                    self._owner_run_id = run_id
                    return
                await self._condition.wait()

    async def release(self, run_id: str) -> None:
        async with self._condition:
            if self._owner_run_id == run_id:
                self._owner_run_id = None
            self._condition.notify_all()

    async def cancel(self, run_id: str) -> bool:
        async with self._condition:
            removed = self._discard(run_id)
            if removed:
                self._condition.notify_all()
            return removed

    async def notify(self) -> None:
        async with self._condition:
            self._condition.notify_all()

    async def snapshot(self) -> BrowserRunAdmissionSnapshot:
        async with self._condition:
            return BrowserRunAdmissionSnapshot(
                owner_run_id=self._owner_run_id,
                queued_run_ids=list(self._queue),
            )

    def _discard(self, run_id: str) -> bool:
        try:
            self._queue.remove(run_id)
            return True
        except ValueError:
            return False
