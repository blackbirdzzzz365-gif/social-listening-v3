from __future__ import annotations

import asyncio
import unittest

from app.services.browser_run_admission import (
    BrowserRunAdmissionCancelled,
    BrowserRunAdmissionService,
)


class BrowserRunAdmissionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_serializes_two_runs_and_releases_next(self) -> None:
        service = BrowserRunAdmissionService()

        self.assertEqual(await service.register("run-a"), "RUNNING")
        self.assertEqual(await service.register("run-b"), "QUEUED")

        await service.acquire("run-a")
        second_acquired = asyncio.Event()

        async def acquire_second() -> None:
            await service.acquire("run-b")
            second_acquired.set()

        task = asyncio.create_task(acquire_second())
        await asyncio.sleep(0.05)
        self.assertFalse(second_acquired.is_set())

        await service.release("run-a")
        await asyncio.wait_for(second_acquired.wait(), timeout=1.0)
        await service.release("run-b")
        await task

    async def test_cancelled_run_exits_queue(self) -> None:
        service = BrowserRunAdmissionService()
        await service.register("run-a")
        await service.register("run-b")
        await service.acquire("run-a")

        cancelled = asyncio.Event()
        should_cancel = {"value": False}

        async def wait_on_second() -> None:
            try:
                await service.acquire("run-b", should_cancel=lambda: should_cancel["value"])
            except BrowserRunAdmissionCancelled:
                cancelled.set()

        task = asyncio.create_task(wait_on_second())
        await asyncio.sleep(0.05)
        should_cancel["value"] = True
        await service.cancel("run-b")
        await service.notify()
        await service.release("run-a")
        await asyncio.wait_for(cancelled.wait(), timeout=1.0)
        await task


if __name__ == "__main__":
    unittest.main()
