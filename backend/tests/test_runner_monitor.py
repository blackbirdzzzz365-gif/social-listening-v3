from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.approval import ApprovalGrant
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.models.run import PlanRun, StepRun
from app.services.runner import RunnerService


class RunnerMonitorOrderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "runner-monitor.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_get_run_orders_steps_by_numeric_step_order(self) -> None:
        with self.session_local() as session:
            session.add(ProductContext(context_id="ctx-1", topic="demo", status="keywords_ready"))
            session.add(Plan(plan_id="plan-1", context_id="ctx-1", version=1, status="ready"))
            session.add(
                ApprovalGrant(
                    grant_id="grant-1",
                    plan_id="plan-1",
                    plan_version=1,
                    approved_step_ids=json.dumps(["step-1", "step-2", "step-10"]),
                    approver_id="tester",
                )
            )
            session.add(
                PlanRun(
                    run_id="run-1",
                    plan_id="plan-1",
                    plan_version=1,
                    grant_id="grant-1",
                    status="RUNNING",
                    total_records=0,
                )
            )
            session.add_all(
                [
                    PlanStep(
                        step_id="plan-1:step-1",
                        plan_id="plan-1",
                        plan_version=1,
                        step_order=1,
                        action_type="SEARCH_POSTS",
                        read_or_write="READ",
                        target="first",
                        risk_level="LOW",
                        dependency_step_ids="[]",
                    ),
                    PlanStep(
                        step_id="plan-1:step-2",
                        plan_id="plan-1",
                        plan_version=1,
                        step_order=2,
                        action_type="SEARCH_POSTS",
                        read_or_write="READ",
                        target="second",
                        risk_level="LOW",
                        dependency_step_ids="[]",
                    ),
                    PlanStep(
                        step_id="plan-1:step-10",
                        plan_id="plan-1",
                        plan_version=1,
                        step_order=10,
                        action_type="SEARCH_IN_GROUP",
                        read_or_write="READ",
                        target="tenth",
                        risk_level="LOW",
                        dependency_step_ids="[]",
                    ),
                ]
            )
            session.add_all(
                [
                    StepRun(
                        step_run_id="step-run-10",
                        run_id="run-1",
                        step_id="plan-1:step-10",
                        status="PENDING",
                        checkpoint=json.dumps({"step_id": "step-10"}),
                    ),
                    StepRun(
                        step_run_id="step-run-1",
                        run_id="run-1",
                        step_id="plan-1:step-1",
                        status="DONE",
                        started_at="2026-04-02T10:00:00+00:00",
                        checkpoint=json.dumps({"step_id": "step-1"}),
                    ),
                    StepRun(
                        step_run_id="step-run-2",
                        run_id="run-1",
                        step_id="plan-1:step-2",
                        status="DONE",
                        started_at="2026-04-02T10:01:00+00:00",
                        checkpoint=json.dumps({"step_id": "step-2"}),
                    ),
                ]
            )
            session.commit()

        with patch("app.services.runner.SessionLocal", self.session_local):
            payload = RunnerService.get_run(object.__new__(RunnerService), "run-1")

        self.assertEqual([step["step_id"] for step in payload["steps"]], ["step-1", "step-2", "step-10"])
        self.assertEqual([step["step_order"] for step in payload["steps"]], [1, 2, 10])


if __name__ == "__main__":
    unittest.main()
