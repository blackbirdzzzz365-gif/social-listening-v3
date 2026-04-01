from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.plans import router as plans_router
from app.infra.ai_client import ProviderServerError
from app.infrastructure.config import Settings
from app.models import Base
from app.models.product_context import ProductContext
from app.services.planner import PlannerProviderUnavailableError, PlannerService


class FakeValiditySpecBuilder:
    async def build(
        self,
        *,
        topic: str,
        clarification_history: list[dict[str, str]],
        keywords: dict[str, list[str]] | None,
        retrieval_profile: dict[str, Any] | None,
        plan_intent: str | None = None,
    ) -> dict[str, Any]:
        return {
            "research_objective": f"Find evidence about {topic}",
            "target_signal_types": ["end_user_experience"],
            "must_have_signals": ["real feedback"],
        }


class RecordingPlannerAIClient:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def call(
        self,
        model: str,
        system_prompt: str,
        user_input: str,
        *,
        stream: bool = False,
        thinking: bool = False,
        provider_slot: str = "default",
        user_content: str | list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "model": model,
                "provider_slot": provider_slot,
                "thinking": thinking,
                "system_prompt": system_prompt,
            }
        )
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def build_settings() -> Settings:
    return Settings(
        anthropic_api_key="",
        planner_retry_count=1,
        planner_retry_backoff_sec=0,
    )


class PlannerPhase11Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase11-planner.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_analyze_topic_retries_provider_failure_and_persists_planning_meta(self) -> None:
        ai_client = RecordingPlannerAIClient(
            [
                ProviderServerError("planner overloaded"),
                {
                    "status": "keywords_ready",
                    "keywords": {"brand": ["FE Credit"], "pain_points": [], "sentiment": [], "behavior": [], "comparison": []},
                    "_provider_meta": {
                        "provider_used": "chiasegpu",
                        "fallback_used": False,
                        "primary_model": "gpt-4o",
                        "fallback_model": "claude-haiku-4-5",
                        "failure_reason": None,
                    },
                },
            ]
        )
        service = PlannerService(ai_client, build_settings())
        service._validity_spec_builder = FakeValiditySpecBuilder()  # type: ignore[assignment]

        with patch("app.services.planner.SessionLocal", self.session_local):
            result = await service.analyze_topic("FE Credit", "KEYWORD_ANALYSIS")

        self.assertEqual(result.status, "keywords_ready")
        assert result.planning_meta is not None
        analysis_meta = result.planning_meta["analysis"]
        self.assertEqual(analysis_meta["attempt_count"], 2)
        self.assertEqual(analysis_meta["provider_used"], "chiasegpu")
        self.assertEqual(len(analysis_meta["attempts"]), 2)

        with self.session_local() as session:
            context = session.get(ProductContext, result.context_id)
            assert context is not None
            stored = json.loads(context.planning_meta_json or "{}")
        self.assertEqual(stored["analysis"]["attempt_count"], 2)

    async def test_generate_plan_returns_generation_meta(self) -> None:
        with self.session_local() as session:
            session.add(
                ProductContext(
                    context_id="ctx-1",
                    topic="FE Credit",
                    status="keywords_ready",
                    keyword_json=json.dumps(
                        {
                            "brand": ["FE Credit"],
                            "pain_points": [],
                            "sentiment": [],
                            "behavior": [],
                            "comparison": [],
                        }
                    ),
                    retrieval_profile_json=json.dumps({"query_families": [{"intent": "brand", "query": "FE Credit"}]}),
                    validity_spec_json=json.dumps({"target_signal_types": ["end_user_experience"]}),
                )
            )
            session.commit()

        ai_client = RecordingPlannerAIClient(
            [
                {
                    "steps": [
                        {
                            "step_id": "step-1",
                            "action_type": "SEARCH_POSTS",
                            "target": "FE Credit bi lua",
                            "estimated_count": 20,
                            "estimated_duration_sec": 300,
                            "risk_level": "LOW",
                            "dependency_step_ids": [],
                        }
                    ],
                    "_provider_meta": {
                        "provider_used": "anthropic",
                        "fallback_used": True,
                        "primary_model": "gpt-4o",
                        "fallback_model": "claude-haiku-4-5",
                        "failure_reason": "ProviderServerError",
                    },
                }
            ]
        )
        service = PlannerService(ai_client, build_settings())

        with patch("app.services.planner.SessionLocal", self.session_local):
            payload = await service.generate_plan("ctx-1", "PLAN_GENERATION")

        self.assertEqual(payload["generation_meta"]["provider_used"], "anthropic")
        self.assertTrue(payload["generation_meta"]["fallback_used"])
        self.assertEqual(payload["generation_meta"]["attempt_count"], 1)

    def test_create_session_maps_planner_provider_error_to_503(self) -> None:
        class FailingPlanner:
            async def analyze_topic(self, topic: str, prompt: str) -> Any:
                raise PlannerProviderUnavailableError(
                    "analysis",
                    "planner stage 'analysis' is temporarily unavailable: overloaded",
                    {"stage": "analysis", "status": "provider_unavailable"},
                )

        app = FastAPI()
        app.include_router(plans_router)
        app.state.planner_service = FailingPlanner()

        client = TestClient(app)
        response = client.post("/api/sessions", json={"topic": "test topic"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("temporarily unavailable", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
