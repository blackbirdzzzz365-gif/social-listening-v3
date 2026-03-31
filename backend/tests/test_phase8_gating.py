from __future__ import annotations

import asyncio
import unittest

from app.infra.ai_client import AIClient
from app.infrastructure.config import Settings
from app.schemas.phase8 import JudgeResult
from app.services.research_gating import (
    ModelJudgeService,
    Phase8BatchHealthEvaluator,
    ValiditySpecBuilder,
)


def build_test_settings() -> Settings:
    return Settings(
        openai_compatible_api_key="",
        phase8_judge_api_key="",
        phase8_ocr_api_key="",
        anthropic_api_key="",
        validity_spec_model="mock-validity-spec",
        content_judge_model="mock-judge",
        image_fallback_model="mock-image",
    )


class ValiditySpecBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = build_test_settings()
        self.ai_client = AIClient(self.settings)
        self.builder = ValiditySpecBuilder(self.ai_client, self.settings)

    def test_builds_versioned_validity_spec(self) -> None:
        spec = asyncio.run(
            self.builder.build(
                topic="mặt nạ bột đậu xanh",
                clarification_history=[
                    {
                        "question": "Ban muon nghien cuu doi tuong nao?",
                        "answer": "Tap trung vao end-user that su da dung mat na tu nhien.",
                    }
                ],
                keywords={
                    "brand": ["mặt nạ bột đậu xanh"],
                    "pain_points": ["da dầu", "kích ứng"],
                    "sentiment": ["có tốt không"],
                    "behavior": ["ib mình nhé"],
                    "comparison": ["mặt nạ đậu xanh vs yến mạch"],
                },
                retrieval_profile={"anchors": ["mặt nạ bột đậu xanh"], "related_terms": ["da dầu"]},
                plan_intent="Tim bai viet end-user co trai nghiem that, loai bot noi dung ban hang.",
            )
        )

        self.assertTrue(spec["spec_id"].startswith("spec-mat-na-bot-dau-xanh-"))
        self.assertTrue(spec["spec_version"].startswith("phase8-v1-"))
        self.assertIn("end_user_experience", spec["target_signal_types"])
        self.assertTrue(spec["comment_policy"]["reject_transactional_only_comments"])
        self.assertGreaterEqual(spec["batch_policy"]["max_consecutive_weak_batches"], 1)


class ModelJudgeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = build_test_settings()
        self.ai_client = AIClient(self.settings)
        self.service = ModelJudgeService(self.ai_client, self.settings)
        self.spec = {
            "spec_id": "spec-demo",
            "spec_version": "phase8-v1-demo",
            "research_objective": "Find real end-user experience.",
            "comment_policy": {
                "allow_parent_context": True,
                "reject_transactional_only_comments": True,
                "minimum_comment_text_length": 8,
            },
            "batch_policy": {
                "min_accept_ratio": 0.15,
                "min_high_conf_accept_ratio": 0.05,
                "max_consecutive_weak_batches": 2,
                "uncertain_reformulation_floor": 0.25,
            },
        }

    def test_hard_filter_rejects_transactional_comment(self) -> None:
        result = self.service.hard_filter(
            content="Xin gia ib minh",
            record_type="COMMENT",
            validity_spec=self.spec,
        )

        self.assertTrue(result.rejected)
        self.assertEqual(result.reason_code, "transactional_only_comment")

    def test_judge_text_returns_structured_result(self) -> None:
        result = asyncio.run(
            self.service.judge_text(
                validity_spec=self.spec,
                content_id="post-1",
                content="Minh da dung mat na nay 2 tuan va da giam do kich ung.",
                record_type="POST",
                source_type="SEARCH_POSTS",
                source_url="https://facebook.com/posts/1",
                query_text="mat na dau xanh",
                query_family="pain_point",
                parent_context=None,
            )
        )

        self.assertIsInstance(result, JudgeResult)
        self.assertEqual(result.decision, "ACCEPTED")
        self.assertGreater(result.relevance_score, 0.7)
        self.assertTrue(result.reason_codes)

    def test_image_fallback_path_can_be_triggered(self) -> None:
        initial = JudgeResult(
            spec_id="spec-demo",
            content_id="post-2",
            decision="UNCERTAIN",
            relevance_score=0.42,
            confidence_score=0.51,
            reason_codes=["mixed_signal"],
            short_rationale="Tin hieu chua du ro.",
            used_image_understanding=False,
            image_summary="",
            model_family="mock",
            model_version="mock-v1",
            policy_version="phase8-v1-demo",
            cache_key="spec-demo:post-2",
        )
        candidate = {
            "content": "Anh nay co thong tin san pham nhung text rat it.",
            "image_ocr_text": "khong con kich ung sau 7 ngay",
            "image_urls": ["https://example.com/test.jpg"],
        }

        self.assertTrue(
            self.service.should_use_image_fallback(
                candidate=candidate,
                initial_result=initial,
                validity_spec=self.spec,
            )
        )
        image_summary, meta = asyncio.run(
            self.service.build_image_summary(candidate=candidate, validity_spec=self.spec)
        )
        self.assertIn("khong con kich ung", image_summary)
        self.assertIn("ocr_text_present", meta["signals"])

    def test_image_fallback_can_upgrade_uncertain_record(self) -> None:
        candidate = {
            "post_id": "post-vision-1",
            "content": "Anh review ngan, text khong ro.",
            "image_ocr_text": "da do giam sau 7 ngay va khong con kich ung",
            "image_urls": ["https://example.com/test.jpg"],
        }

        image_summary, _meta = asyncio.run(
            self.service.build_image_summary(candidate=candidate, validity_spec=self.spec)
        )
        result = asyncio.run(
            self.service.judge_text(
                validity_spec=self.spec,
                content_id="post-vision-1",
                content="Anh review ngan, text khong ro.",
                record_type="POST",
                source_type="SEARCH_POSTS",
                source_url="https://facebook.com/posts/vision-1",
                query_text="mat na ngũ hoa truoc sau",
                query_family="pain_point",
                parent_context=None,
                image_summary=image_summary,
                used_image_understanding=True,
            )
        )

        self.assertEqual(result.decision, "ACCEPTED")
        self.assertTrue(result.used_image_understanding)
        self.assertIn("OCR", result.image_summary)


class BatchRoutingV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = Phase8BatchHealthEvaluator(build_test_settings())
        self.spec = {
            "batch_policy": {
                "min_accept_ratio": 0.15,
                "min_high_conf_accept_ratio": 0.05,
                "max_consecutive_weak_batches": 2,
                "uncertain_reformulation_floor": 0.25,
            }
        }

    def test_marks_healthy_batch_as_continue(self) -> None:
        results = [
            JudgeResult(
                spec_id="spec",
                content_id=f"post-{index}",
                decision="ACCEPTED",
                relevance_score=0.8,
                confidence_score=0.82,
                reason_codes=["experience_signal"],
                short_rationale="ok",
                used_image_understanding=False,
                image_summary="",
                model_family="mock",
                model_version="mock",
                policy_version="v1",
                cache_key=f"spec:post-{index}",
            )
            for index in range(4)
        ]
        results.extend(
            [
                JudgeResult(
                    spec_id="spec",
                    content_id="post-r",
                    decision="REJECTED",
                    relevance_score=0.1,
                    confidence_score=0.9,
                    reason_codes=["commercial_noise"],
                    short_rationale="reject",
                    used_image_understanding=False,
                    image_summary="",
                    model_family="mock",
                    model_version="mock",
                    policy_version="v1",
                    cache_key="spec:post-r",
                )
            ]
        )

        health = self.evaluator.evaluate(results, self.spec)
        self.assertEqual(health.decision, "continue")

    def test_marks_uncertain_batch_for_reformulation(self) -> None:
        results = [
            JudgeResult(
                spec_id="spec",
                content_id=f"post-{index}",
                decision="UNCERTAIN",
                relevance_score=0.45,
                confidence_score=0.6,
                reason_codes=["mixed_signal"],
                short_rationale="uncertain",
                used_image_understanding=False,
                image_summary="",
                model_family="mock",
                model_version="mock",
                policy_version="v1",
                cache_key=f"spec:post-{index}",
            )
            for index in range(6)
        ]
        results.extend(
            [
                JudgeResult(
                    spec_id="spec",
                    content_id=f"rej-{index}",
                    decision="REJECTED",
                    relevance_score=0.1,
                    confidence_score=0.8,
                    reason_codes=["noise"],
                    short_rationale="reject",
                    used_image_understanding=False,
                    image_summary="",
                    model_family="mock",
                    model_version="mock",
                    policy_version="v1",
                    cache_key=f"spec:rej-{index}",
                )
                for index in range(4)
            ]
        )

        health = self.evaluator.evaluate(results, self.spec)
        self.assertEqual(health.decision, "reformulate")

    def test_marks_low_quality_batch_as_weak(self) -> None:
        results = [
            JudgeResult(
                spec_id="spec",
                content_id=f"rej-{index}",
                decision="REJECTED",
                relevance_score=0.05,
                confidence_score=0.9,
                reason_codes=["commercial_noise"],
                short_rationale="reject",
                used_image_understanding=False,
                image_summary="",
                model_family="mock",
                model_version="mock",
                policy_version="v1",
                cache_key=f"spec:rej-{index}",
            )
            for index in range(10)
        ]

        health = self.evaluator.evaluate(results, self.spec)
        self.assertEqual(health.decision, "weak")


if __name__ == "__main__":
    unittest.main()
