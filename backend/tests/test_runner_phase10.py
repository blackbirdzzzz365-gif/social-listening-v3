from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.ai_client import AIClient
from app.infrastructure.config import Settings
from app.models import Base
from app.models.approval import ApprovalGrant
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.services.runner import RunnerService


class FakeHealthMonitor:
    def is_write_allowed(self) -> bool:
        return True


class ControlledBrowserAgent:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def search_posts(
        self,
        query: str,
        *,
        target_count: int = 10,
        filter_recent: bool = True,
        progress_callback=None,
    ) -> dict[str, object]:
        self.started.set()
        if progress_callback is not None:
            maybe_coro = progress_callback({"activity": "waiting_for_results", "query": query})
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        return {"posts": [], "discovered_groups": []}


class RunnerPhase10Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase10-runner.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

        with self.session_local() as session:
            session.add(
                ProductContext(
                    context_id="context-1",
                    topic="Phase 10 runner test",
                    status="keywords_ready",
                    keyword_json=json.dumps({"brand": ["phase 10"]}),
                    retrieval_profile_json=json.dumps({"anchors": ["phase 10"], "related_terms": []}),
                    validity_spec_json=json.dumps({"batch_policy": {}}),
                )
            )
            session.add(
                Plan(
                    plan_id="plan-1",
                    context_id="context-1",
                    version=1,
                    status="ready",
                )
            )
            session.add(
                PlanStep(
                    step_id="plan-1:step-1",
                    plan_id="plan-1",
                    plan_version=1,
                    step_order=1,
                    action_type="SEARCH_POSTS",
                    read_or_write="READ",
                    target="phase 10",
                    estimated_count=5,
                    estimated_duration_sec=60,
                    risk_level="LOW",
                    dependency_step_ids="[]",
                )
            )
            session.add(
                ApprovalGrant(
                    grant_id="grant-1",
                    plan_id="plan-1",
                    plan_version=1,
                    approved_step_ids=json.dumps(["step-1"]),
                    approver_id="test-user",
                    invalidated=False,
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def build_runner(self, browser_agent: ControlledBrowserAgent) -> RunnerService:
        settings = Settings(
            database_url=f"sqlite:///{Path(self.temp_dir.name) / 'phase10-runner.db'}",
            browser_mock_mode=True,
            step_heartbeat_interval_sec=0.05,
            search_posts_timeout_sec=5.0,
            openai_compatible_api_key="",
            phase8_judge_api_key="",
            phase8_ocr_api_key="",
            anthropic_api_key="",
        )
        return RunnerService(
            browser_agent=browser_agent,
            health_monitor=FakeHealthMonitor(),
            ai_client=AIClient(settings),
            label_job_service=None,
            settings=settings,
        )

    async def test_stop_run_converges_to_cancelled_without_leaving_running_step(self) -> None:
        browser_agent = ControlledBrowserAgent()
        runner = self.build_runner(browser_agent)

        with patch("app.services.runner.SessionLocal", self.session_local):
            payload = await runner.start_run("plan-1", "grant-1")
            run_id = payload["run_id"]

            await asyncio.wait_for(browser_agent.started.wait(), timeout=1.0)
            cancelling = await runner.stop_run(run_id)
            self.assertEqual(cancelling["status"], "CANCELLING")

            await asyncio.wait_for(runner._tasks[run_id], timeout=1.0)
            final_payload = runner.get_run(run_id)

        self.assertTrue(browser_agent.cancelled.is_set())
        self.assertEqual(final_payload["status"], "CANCELLED")
        self.assertEqual(final_payload["completion_reason"], "USER_CANCELLED")
        self.assertIsNotNone(final_payload["ended_at"])
        self.assertEqual(final_payload["steps"][0]["status"], "SKIPPED")

    async def test_running_step_exposes_heartbeat_progress(self) -> None:
        browser_agent = ControlledBrowserAgent()
        runner = self.build_runner(browser_agent)

        with patch("app.services.runner.SessionLocal", self.session_local):
            payload = await runner.start_run("plan-1", "grant-1")
            run_id = payload["run_id"]

            await asyncio.wait_for(browser_agent.started.wait(), timeout=1.0)
            await asyncio.sleep(0.12)
            running = runner.get_run(run_id)
            step = running["steps"][0]

            self.assertEqual(step["status"], "RUNNING")
            self.assertIsNotNone(step["checkpoint"])
            self.assertIn("heartbeat_at", step["checkpoint"])
            self.assertIn(
                step["checkpoint"]["progress"]["activity"],
                {"search_posts", "waiting_for_results"},
            )

            browser_agent.release.set()
            await asyncio.wait_for(runner._tasks[run_id], timeout=1.0)
            final_payload = runner.get_run(run_id)

        self.assertEqual(final_payload["status"], "DONE")
        self.assertEqual(final_payload["steps"][0]["status"], "DONE")


if __name__ == "__main__":
    unittest.main()
