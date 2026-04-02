from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config import Settings
from app.models import Base
from app.models.crawled_post import CrawledPost
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.models.run import PlanRun
from app.models.run import StepRun
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
                ProductContext(
                    context_id="context-2",
                    topic="shinhan vay tien mat",
                    status="keywords_ready",
                )
            )
            session.add(Plan(plan_id="plan-1", context_id="context-2", version=1, status="ready"))
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
        self.assertIsNotNone(summary["answer_payload"])
        self.assertEqual(summary["answer_payload"]["outcome_type"], "NO_ANSWER_CONTENT")
        with self.session_local() as session:
            run = session.get(PlanRun, "run-2")
            assert run is not None
            self.assertEqual(run.answer_status, "NO_ANSWER_CONTENT")
            self.assertIsNone(run.answer_generated_at)
            self.assertIsNotNone(run.answer_payload_json)

    async def test_builds_no_eligible_records_payload(self) -> None:
        with self.session_local() as session:
            session.add(
                ProductContext(
                    context_id="context-3",
                    topic="vay tiền mặt ở shin han",
                    status="keywords_ready",
                )
            )
            session.add(Plan(plan_id="plan-3", context_id="context-3", version=1, status="ready"))
            session.add(
                PlanStep(
                    step_id="plan-3:step-1",
                    plan_id="plan-3",
                    plan_version=1,
                    step_order=1,
                    action_type="SEARCH_POSTS",
                    read_or_write="READ",
                    target="shinhan",
                    estimated_count=80,
                    estimated_duration_sec=60,
                    risk_level="LOW",
                    dependency_step_ids="[]",
                )
            )
            session.add(
                PlanRun(
                    run_id="run-3",
                    plan_id="plan-3",
                    plan_version=1,
                    grant_id="grant-3",
                    status="DONE",
                    completion_reason="NO_ELIGIBLE_RECORDS",
                    failure_class=None,
                    answer_status=None,
                    answer_generated_at=None,
                    answer_payload_json=None,
                    started_at="2026-04-02T00:00:00+00:00",
                    total_records=2,
                )
            )
            session.add(
                StepRun(
                    step_run_id="step-run-3",
                    run_id="run-3",
                    step_id="plan-3:step-1",
                    status="DONE",
                    started_at="2026-04-02T00:00:00+00:00",
                    ended_at="2026-04-02T00:02:00+00:00",
                    actual_count=80,
                    checkpoint=json.dumps(
                        {
                            "phase": "done",
                            "step_id": "step-1",
                            "query_attempts": [
                                {
                                    "query": "shinhan phi cao",
                                    "collected_count": 80,
                                    "accepted_count": 0,
                                    "stop_reason": "zero_accepted_batches_exceeded",
                                    "reason_cluster": "generic_weak",
                                    "used_reformulation": True,
                                }
                            ],
                            "batch_summaries": [],
                        }
                    ),
                    checkpoint_json=None,
                    retry_count=0,
                )
            )
            session.add(
                CrawledPost(
                    post_id="post-1",
                    run_id="run-3",
                    step_run_id="step-run-3",
                    group_id_hash="group-1",
                    content="Shinhan vay nhanh inbox em",
                    content_masked="Shinhan vay nhanh inbox em",
                    record_type="POST",
                    source_url="https://example.com/post-1",
                    pre_ai_status="REJECTED",
                    judge_decision="REJECTED",
                    judge_relevance_score=0.12,
                    judge_reason_codes_json=json.dumps(["commercial_noise", "seller_cta"]),
                    judge_used_image_understanding=False,
                    label_status="PENDING",
                    is_excluded=False,
                )
            )
            session.add(
                CrawledPost(
                    post_id="post-2",
                    run_id="run-3",
                    step_run_id="step-run-3",
                    group_id_hash="group-2",
                    content="Shinhan lãi suất sao vậy",
                    content_masked="Shinhan lãi suất sao vậy",
                    record_type="POST",
                    source_url="https://example.com/post-2",
                    pre_ai_status="REJECTED",
                    judge_decision="REJECTED",
                    judge_relevance_score=0.42,
                    judge_reason_codes_json=json.dumps(["no_target_mention"]),
                    judge_used_image_understanding=False,
                    label_status="PENDING",
                    is_excluded=False,
                )
            )
            session.commit()

        service = RunCloseoutService(FakeInsightService({"themes": []}), Settings())

        with patch("app.services.run_closeout.SessionLocal", self.session_local):
            summary = await service.ensure_no_answer_closeout_for_run(
                "run-3",
                outcome_type="NO_ELIGIBLE_RECORDS",
                warning="No eligible records remained after pre-AI gating.",
            )

        self.assertEqual(summary["answer_status"], "NO_ELIGIBLE_RECORDS")
        payload = summary["answer_payload"]
        self.assertIsNotNone(payload)
        self.assertEqual(payload["outcome_type"], "NO_ELIGIBLE_RECORDS")
        self.assertEqual(payload["topic"], "vay tiền mặt ở shin han")
        self.assertEqual(payload["attempted_queries"][0]["query"], "shinhan phi cao")
        self.assertEqual(payload["dominant_reject_reasons"][0]["reason_code"], "commercial_noise")
        with self.session_local() as session:
            run = session.get(PlanRun, "run-3")
            assert run is not None
            self.assertEqual(run.answer_status, "NO_ELIGIBLE_RECORDS")
            self.assertIsNotNone(run.answer_generated_at)
            self.assertIsNotNone(run.answer_payload_json)

    async def test_builds_reauth_required_payload(self) -> None:
        with self.session_local() as session:
            session.add(
                ProductContext(
                    context_id="context-4",
                    topic="fe credit",
                    status="keywords_ready",
                )
            )
            session.add(Plan(plan_id="plan-4", context_id="context-4", version=1, status="ready"))
            session.add(
                PlanRun(
                    run_id="run-4",
                    plan_id="plan-4",
                    plan_version=1,
                    grant_id="grant-4",
                    status="DONE",
                    completion_reason="REAUTH_REQUIRED",
                    failure_class="AUTH_SESSION_EXPIRED",
                    answer_status=None,
                    answer_generated_at=None,
                    answer_payload_json=None,
                    started_at="2026-04-02T00:00:00+00:00",
                    total_records=0,
                )
            )
            from app.models.health import AccountHealthState

            session.add(
                AccountHealthState(
                    id=1,
                    status="CAUTION",
                    session_status="EXPIRED",
                    account_id_hash="account",
                    last_checked="2026-04-02T00:10:00+00:00",
                )
            )
            session.commit()

        service = RunCloseoutService(FakeInsightService({"themes": []}), Settings())

        with patch("app.services.run_closeout.SessionLocal", self.session_local):
            summary = await service.ensure_reauth_required_for_run(
                "run-4",
                warning="Facebook session expired",
                failed_step_id="step-1",
                failure_stage="preflight",
            )

        self.assertEqual(summary["answer_status"], "REAUTH_REQUIRED")
        payload = summary["answer_payload"]
        self.assertEqual(payload["outcome_type"], "REAUTH_REQUIRED")
        self.assertEqual(payload["operator_state"]["session_status"], "EXPIRED")
        self.assertEqual(payload["recommended_next_actions"][0], "Open the Facebook setup flow and reconnect the account.")


if __name__ == "__main__":
    unittest.main()
