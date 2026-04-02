from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.ai_client import AIClient
from app.infra.browser_agent import SessionExpiredException
from app.infrastructure.config import Settings
from app.models import Base
from app.models.approval import ApprovalGrant
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.services.runner import RunnerService


class ExpiredPreflightBrowserAgent:
    async def assert_session_valid(self) -> None:
        raise SessionExpiredException("Facebook session expired")


class MidStepExpiryBrowserAgent:
    async def assert_session_valid(self) -> None:
        return None

    async def search_posts(
        self,
        query: str,
        *,
        target_count: int = 10,
        filter_recent: bool = True,
        progress_callback=None,
    ) -> dict[str, object]:
        if progress_callback is not None:
            maybe_coro = progress_callback({"activity": "search_posts", "query": query})
            if hasattr(maybe_coro, "__await__"):
                await maybe_coro
        raise SessionExpiredException("Facebook session expired")


class FakeHealthMonitor:
    def __init__(self) -> None:
        self.session_status = "VALID"
        self.health_status = "HEALTHY"

    def is_write_allowed(self) -> bool:
        return True

    def get_browser_runtime_state(self):
        class State:
            pass

        state = State()
        state.session_status = self.session_status
        state.account_id_hash = "account"
        state.health_status = self.health_status
        state.cooldown_until = None
        state.last_checked = None
        state.runnable = self.session_status == "VALID"
        state.action_required = None if state.runnable else "REAUTH_REQUIRED"
        state.block_reason = None if state.runnable else "session_expired"
        return state

    async def mark_session_expired(self, raw_signal=None):
        self.session_status = "EXPIRED"
        self.health_status = "CAUTION"
        return self.get_browser_runtime_state()


class RunnerPhase13Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase13-runner.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

        with self.session_local() as session:
            session.add(ProductContext(context_id="context-1", topic="fe credit", status="keywords_ready"))
            session.add(Plan(plan_id="plan-1", context_id="context-1", version=1, status="ready"))
            session.add(
                PlanStep(
                    step_id="plan-1:step-1",
                    plan_id="plan-1",
                    plan_version=1,
                    step_order=1,
                    action_type="SEARCH_POSTS",
                    read_or_write="READ",
                    target="FE Credit",
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

    def build_runner(self, browser_agent) -> RunnerService:
        settings = Settings(
            database_url=f"sqlite:///{Path(self.temp_dir.name) / 'phase13-runner.db'}",
            browser_mock_mode=True,
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

    async def test_preflight_expired_session_ends_run_without_starting_step(self) -> None:
        runner = self.build_runner(ExpiredPreflightBrowserAgent())

        with patch("app.services.runner.SessionLocal", self.session_local):
            payload = await runner.start_run("plan-1", "grant-1")
            await runner._tasks[payload["run_id"]]
            final_payload = runner.get_run(payload["run_id"])

        self.assertEqual(final_payload["status"], "DONE")
        self.assertEqual(final_payload["completion_reason"], "REAUTH_REQUIRED")
        self.assertEqual(final_payload["answer_status"], "REAUTH_REQUIRED")
        self.assertEqual(final_payload["steps"][0]["status"], "SKIPPED")
        self.assertEqual(final_payload["steps"][0]["checkpoint"]["skip_reason"], "reauth_required")

    async def test_mid_step_expiry_converts_to_reauth_required_outcome(self) -> None:
        runner = self.build_runner(MidStepExpiryBrowserAgent())

        with patch("app.services.runner.SessionLocal", self.session_local):
            payload = await runner.start_run("plan-1", "grant-1")
            await runner._tasks[payload["run_id"]]
            final_payload = runner.get_run(payload["run_id"])

        self.assertEqual(final_payload["status"], "DONE")
        self.assertEqual(final_payload["completion_reason"], "REAUTH_REQUIRED")
        self.assertEqual(final_payload["failure_class"], "AUTH_SESSION_EXPIRED")
        self.assertEqual(final_payload["steps"][0]["status"], "FAILED")
        self.assertEqual(final_payload["steps"][0]["checkpoint"]["failure_class"], "AUTH_SESSION_EXPIRED")

