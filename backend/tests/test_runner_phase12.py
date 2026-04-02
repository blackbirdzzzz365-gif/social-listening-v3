from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.ai_client import AIClient
from app.infrastructure.config import Settings
from app.models import Base
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.models.run import PlanRun, StepRun
from app.services.runner import RunnerService


class DummyBrowserAgent:
    pass


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


class RunnerPhase12Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase12-runner.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

        with self.session_local() as session:
            session.add(
                ProductContext(
                    context_id="context-1",
                    topic="vay tien mat o shinhan",
                    status="keywords_ready",
                )
            )
            session.add(Plan(plan_id="plan-1", context_id="context-1", version=1, status="ready"))
            for order, action_type in enumerate(("SEARCH_POSTS", "SEARCH_IN_GROUP", "SEARCH_POSTS"), start=1):
                session.add(
                    PlanStep(
                        step_id=f"plan-1:step-{order}",
                        plan_id="plan-1",
                        plan_version=1,
                        step_order=order,
                        action_type=action_type,
                        read_or_write="READ",
                        target=f"query-{order}",
                        estimated_count=60,
                        estimated_duration_sec=60,
                        risk_level="LOW",
                        dependency_step_ids="[]",
                    )
                )
            session.add(
                PlanRun(
                    run_id="run-1",
                    plan_id="plan-1",
                    plan_version=1,
                    grant_id="grant-1",
                    status="RUNNING",
                    completion_reason=None,
                    failure_class=None,
                    answer_status=None,
                    answer_generated_at=None,
                    answer_payload_json=None,
                    started_at="2026-04-02T00:00:00+00:00",
                    total_records=140,
                )
            )
            for step_no in (1, 2):
                session.add(
                    StepRun(
                        step_run_id=f"step-run-{step_no}",
                        run_id="run-1",
                        step_id=f"plan-1:step-{step_no}",
                        status="DONE",
                        started_at="2026-04-02T00:00:00+00:00",
                        ended_at="2026-04-02T00:01:00+00:00",
                        actual_count=70,
                        checkpoint=json.dumps(
                            {
                                "phase": "done",
                                "step_id": f"step-{step_no}",
                                "query_attempts": [
                                    {
                                        "query": f"shinhan-{step_no}",
                                        "collected_count": 70,
                                        "accepted_count": 0,
                                        "stop_reason": "zero_accepted_batches_exceeded",
                                        "reason_cluster": "generic_weak",
                                        "used_reformulation": False,
                                    }
                                ],
                            }
                        ),
                        checkpoint_json=None,
                        retry_count=0,
                    )
                )
            session.add(
                StepRun(
                    step_run_id="step-run-3",
                    run_id="run-1",
                    step_id="plan-1:step-3",
                    status="PENDING",
                    started_at=None,
                    ended_at=None,
                    actual_count=None,
                    checkpoint=json.dumps({"phase": "pending", "step_id": "step-3"}),
                    checkpoint_json=None,
                    retry_count=0,
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_goal_aware_exhaustion_skips_pending_tail_steps(self) -> None:
        settings = Settings(
            database_url=f"sqlite:///{Path(self.temp_dir.name) / 'phase12-runner.db'}",
            goal_aware_exhaustion_enabled=True,
            goal_aware_min_search_steps=2,
            goal_aware_min_scanned_records=100,
            openai_compatible_api_key="",
            phase8_judge_api_key="",
            phase8_ocr_api_key="",
            anthropic_api_key="",
        )
        runner = RunnerService(
            browser_agent=DummyBrowserAgent(),
            health_monitor=FakeHealthMonitor(),
            ai_client=AIClient(settings),
            label_job_service=None,
            settings=settings,
        )

        with self.session_local() as session:
            summary = runner._apply_goal_aware_exhaustion(session, "run-1")
            session.commit()

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["dominant_reason_cluster"], "generic_weak")
        self.assertIn("step-3", summary["skipped_step_ids"])

        with self.session_local() as session:
            step_run = session.get(StepRun, "step-run-3")
            assert step_run is not None
            self.assertEqual(step_run.status, "SKIPPED")
            checkpoint = json.loads(step_run.checkpoint or step_run.checkpoint_json or "{}")
            self.assertEqual(checkpoint["skip_reason"], "goal_aware_exhaustion")


if __name__ == "__main__":
    unittest.main()
