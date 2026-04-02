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

    def get_browser_runtime_state(self):
        class State:
            session_status = "VALID"
            account_id_hash = "account"
            health_status = "HEALTHY"
            cooldown_until = None
            last_checked = None
            runnable = True
            action_required = None
            block_reason = None

        return State()

    async def mark_session_expired(self, raw_signal=None):
        class State:
            session_status = "EXPIRED"
            account_id_hash = "account"
            health_status = "CAUTION"
            cooldown_until = None
            last_checked = None
            runnable = False
            action_required = "REAUTH_REQUIRED"
            block_reason = "session_expired"

        return State()


class TimeoutBrowserAgent:
    async def search_posts(
        self,
        query: str,
        *,
        target_count: int = 10,
        filter_recent: bool = True,
        progress_callback=None,
    ) -> dict[str, object]:
        if progress_callback is not None:
            maybe_coro = progress_callback(
                {
                    "activity": "scanning_search_results",
                    "query": query,
                    "collected_count": 3,
                    "persisted_count": 0,
                    "image_candidate_count": 1,
                    "sample_candidates": [
                        {
                            "ordinal": 1,
                            "post_id": "raw-1",
                            "content_preview": "review co hinh anh ve Ngu Hoa",
                            "has_image_context": True,
                        }
                    ],
                }
            )
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
        await asyncio.sleep(0.2)
        return {"posts": [], "discovered_groups": []}


class RunnerPhase11TimeoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase11-timeout.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

        with self.session_local() as session:
            session.add(
                ProductContext(
                    context_id="context-1",
                    topic="Review co hinh anh ve mat na Ngu Hoa truoc va sau khi dung",
                    status="keywords_ready",
                    keyword_json=json.dumps({"brand": ["Ngu Hoa"]}),
                    retrieval_profile_json=json.dumps({"anchors": ["Ngu Hoa"], "related_terms": []}),
                    validity_spec_json=json.dumps({"batch_policy": {}}),
                )
            )
            session.add(Plan(plan_id="plan-1", context_id="context-1", version=1, status="ready"))
            session.add(
                PlanStep(
                    step_id="plan-1:step-1",
                    plan_id="plan-1",
                    plan_version=1,
                    step_order=1,
                    action_type="SEARCH_POSTS",
                    read_or_write="READ",
                    target="Ngu Hoa",
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

    def build_runner(self) -> RunnerService:
        settings = Settings(
            database_url=f"sqlite:///{Path(self.temp_dir.name) / 'phase11-timeout.db'}",
            browser_mock_mode=True,
            step_heartbeat_interval_sec=0.02,
            search_posts_timeout_sec=0.05,
            openai_compatible_api_key="",
            phase8_judge_api_key="",
            phase8_ocr_api_key="",
            anthropic_api_key="",
        )
        return RunnerService(
            browser_agent=TimeoutBrowserAgent(),
            health_monitor=FakeHealthMonitor(),
            ai_client=AIClient(settings),
            label_job_service=None,
            settings=settings,
        )

    async def test_timeout_preserves_salvage_metadata(self) -> None:
        runner = self.build_runner()

        with patch("app.services.runner.SessionLocal", self.session_local):
            payload = await runner.start_run("plan-1", "grant-1")
            run_id = payload["run_id"]
            await asyncio.wait_for(runner._tasks[run_id], timeout=1.0)
            final_payload = runner.get_run(run_id)

        self.assertEqual(final_payload["status"], "FAILED")
        self.assertEqual(final_payload["failure_class"], "STEP_STUCK_TIMEOUT")
        step = final_payload["steps"][0]
        self.assertEqual(step["status"], "FAILED")
        self.assertEqual(step["actual_count"], 3)
        checkpoint = step["checkpoint"] or {}
        salvage = checkpoint.get("salvage") or {}
        self.assertTrue(salvage.get("available"))
        self.assertEqual(salvage.get("collected_count"), 3)
        self.assertEqual(salvage.get("persisted_count"), 0)
        self.assertEqual(salvage.get("lost_before_persist_count"), 3)
        self.assertEqual(salvage.get("image_candidate_count"), 1)
        self.assertEqual(len(salvage.get("sample_candidates") or []), 1)


if __name__ == "__main__":
    unittest.main()
