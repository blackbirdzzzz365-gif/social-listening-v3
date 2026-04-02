from __future__ import annotations

from types import SimpleNamespace
from typing import Any
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.plans import router as plans_router


class FakeHealthMonitor:
    def __init__(
        self,
        *,
        runnable: bool,
        session_status: str = "VALID",
        health_status: str = "HEALTHY",
        action_required: str | None = None,
        block_reason: str | None = None,
    ) -> None:
        self._state = SimpleNamespace(
            runnable=runnable,
            session_status=session_status,
            health_status=health_status,
            action_required=action_required,
            block_reason=block_reason,
            last_checked="2026-04-02T07:00:00+00:00",
        )

    def get_browser_runtime_state(self) -> Any:
        return self._state


class RecordingPlanner:
    def __init__(self) -> None:
        self.analysis_called = False
        self.clarification_called = False
        self.plan_called = False
        self.refine_called = False

    async def analyze_topic(self, topic: str, prompt: str) -> Any:
        self.analysis_called = True
        return SimpleNamespace(
            context_id="ctx-1",
            topic=topic,
            status="keywords_ready",
            clarifying_questions=[],
            keywords={"brand": ["FE Credit"], "pain_points": [], "sentiment": [], "behavior": [], "comparison": []},
            retrieval_profile={},
            validity_spec={},
            clarification_history=[],
            planning_meta={"analysis": {"provider_used": "anthropic"}},
        )

    async def submit_clarifications(self, context_id: str, answers: list[str], prompt: str) -> Any:
        self.clarification_called = True
        return SimpleNamespace(
            context_id=context_id,
            topic="FE Credit",
            status="keywords_ready",
            clarifying_questions=[],
            keywords={"brand": ["FE Credit"], "pain_points": [], "sentiment": [], "behavior": [], "comparison": []},
            retrieval_profile={},
            validity_spec={},
            clarification_history=[],
            planning_meta={"clarification": {"provider_used": "anthropic"}},
        )

    async def generate_plan(self, context_id: str, prompt: str) -> dict[str, Any]:
        self.plan_called = True
        return {
            "plan_id": "plan-1",
            "context_id": context_id,
            "version": 1,
            "status": "draft",
            "steps": [],
            "estimated_total_duration_sec": 0,
            "warnings": [],
            "diff_summary": None,
            "generation_meta": {"provider_used": "anthropic"},
        }

    async def refine_plan(self, plan_id: str, instruction: str, prompt: str) -> dict[str, Any]:
        self.refine_called = True
        return {
            "plan_id": plan_id,
            "context_id": "ctx-1",
            "version": 2,
            "status": "draft",
            "steps": [],
            "estimated_total_duration_sec": 0,
            "warnings": [],
            "diff_summary": "refined",
            "generation_meta": {"provider_used": "anthropic"},
        }

    async def explain_steps(self, payload: dict[str, Any], prompt: str) -> dict[str, str]:
        return {}

    async def get_context_result(self, context_id: str, prompt: str) -> Any:
        return SimpleNamespace(
            context_id=context_id,
            topic="FE Credit",
            status="keywords_ready",
            clarifying_questions=[],
            keywords={"brand": ["FE Credit"], "pain_points": [], "sentiment": [], "behavior": [], "comparison": []},
            retrieval_profile={},
            validity_spec={},
            clarification_history=[],
            planning_meta={"analysis": {"provider_used": "anthropic"}},
        )

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        return {
            "plan_id": plan_id,
            "context_id": "ctx-1",
            "version": 1,
            "status": "draft",
            "steps": [],
            "estimated_total_duration_sec": 0,
            "warnings": [],
            "diff_summary": None,
            "generation_meta": {"provider_used": "anthropic"},
        }


class PlansPhase14Tests(unittest.TestCase):
    def _build_client(self, *, runnable: bool, session_status: str = "VALID", action_required: str | None = None) -> tuple[TestClient, RecordingPlanner]:
        app = FastAPI()
        app.include_router(plans_router)
        planner = RecordingPlanner()
        app.state.planner_service = planner
        app.state.health_monitor = FakeHealthMonitor(
            runnable=runnable,
            session_status=session_status,
            action_required=action_required,
            block_reason="session_expired" if session_status == "EXPIRED" else None,
            health_status="CAUTION" if session_status == "EXPIRED" else "HEALTHY",
        )
        return TestClient(app), planner

    def test_create_session_blocks_before_planner_when_runtime_not_ready(self) -> None:
        client, planner = self._build_client(runnable=False, session_status="EXPIRED", action_required="REAUTH_REQUIRED")

        response = client.post("/api/sessions", json={"topic": "test topic"})

        self.assertEqual(response.status_code, 409)
        self.assertIn("Facebook session has expired", response.json()["detail"])
        self.assertFalse(planner.analysis_called)

    def test_create_plan_blocks_before_planner_when_runtime_not_ready(self) -> None:
        client, planner = self._build_client(runnable=False, session_status="NOT_SETUP", action_required="CONNECT_FACEBOOK")

        response = client.post("/api/plans", json={"context_id": "ctx-1"})

        self.assertEqual(response.status_code, 409)
        self.assertIn("connect the Facebook session", response.json()["detail"])
        self.assertFalse(planner.plan_called)

    def test_successful_session_includes_runtime_readiness(self) -> None:
        client, _planner = self._build_client(runnable=True)

        response = client.post("/api/sessions", json={"topic": "test topic"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["runtime_readiness"]["runnable"])
        self.assertEqual(payload["runtime_readiness"]["session_status"], "VALID")


if __name__ == "__main__":
    unittest.main()
