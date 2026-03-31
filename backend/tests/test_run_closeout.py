from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config import Settings
from app.models import Base
from app.models.run import PlanRun
from app.services.run_closeout import RunCloseoutService


class FakeInsightService:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str]] = []

    async def analyze_themes(self, run_id: str, prompt: str, audience_filter: str | None = None) -> dict:
        self.calls.append((run_id, audience_filter or ""))
        return self.payload


class RunCloseoutServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase9-closeout.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_marks_run_answer_ready_when_themes_exist(self) -> None:
        with self.session_local() as session:
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
                    started_at="2026-03-31T00:00:00+00:00",
                    total_records=10,
                )
            )
            session.commit()

        service = RunCloseoutService(
            FakeInsightService(
                {
                    "run_id": "run-1",
                    "audience_filter": "end_user_only",
                    "taxonomy_version": "v1",
                    "posts_crawled": 10,
                    "posts_included": 4,
                    "posts_excluded": 6,
                    "excluded_by_label_count": 6,
                    "excluded_breakdown": {"excluded": 6},
                    "themes": [
                        {
                            "theme_id": "theme-1",
                            "label": "pain_point",
                            "dominant_sentiment": "negative",
                            "post_count": 4,
                            "sample_quotes": ["sample"],
                        }
                    ],
                    "warning": None,
                }
            ),
            Settings(),
        )

        with patch("app.services.run_closeout.SessionLocal", self.session_local):
            summary = await service.ensure_closeout_for_run("run-1")

        self.assertEqual(summary["answer_status"], "ANSWER_READY")
        with self.session_local() as session:
            run = session.get(PlanRun, "run-1")
            assert run is not None
            self.assertEqual(run.answer_status, "ANSWER_READY")
            self.assertIsNotNone(run.answer_generated_at)

    async def test_marks_run_no_answer_when_theme_list_empty(self) -> None:
        with self.session_local() as session:
            session.add(
                PlanRun(
                    run_id="run-2",
                    plan_id="plan-1",
                    plan_version=1,
                    grant_id="grant-1",
                    status="RUNNING",
                    completion_reason=None,
                    failure_class=None,
                    answer_status=None,
                    answer_generated_at=None,
                    started_at="2026-03-31T00:00:00+00:00",
                    total_records=3,
                )
            )
            session.commit()

        service = RunCloseoutService(
            FakeInsightService(
                {
                    "run_id": "run-2",
                    "audience_filter": "end_user_only",
                    "taxonomy_version": "v1",
                    "posts_crawled": 3,
                    "posts_included": 0,
                    "posts_excluded": 3,
                    "excluded_by_label_count": 3,
                    "excluded_breakdown": {"pre_ai_rejected": 3},
                    "themes": [],
                    "warning": "No eligible records remained after pre-AI gating. Theme analysis was skipped.",
                }
            ),
            Settings(),
        )

        with patch("app.services.run_closeout.SessionLocal", self.session_local):
            summary = await service.ensure_closeout_for_run("run-2")

        self.assertEqual(summary["answer_status"], "NO_ANSWER_CONTENT")
        with self.session_local() as session:
            run = session.get(PlanRun, "run-2")
            assert run is not None
            self.assertEqual(run.answer_status, "NO_ANSWER_CONTENT")
            self.assertIsNone(run.answer_generated_at)


if __name__ == "__main__":
    unittest.main()
