from __future__ import annotations

import unittest

from app.services.retrieval_quality import (
    BatchHealthEvaluator,
    DeterministicRelevanceEngine,
    RetrievalProfileBuilder,
    clean_payload_text,
)


class RetrievalProfileBuilderTests(unittest.TestCase):
    def test_builds_query_families_and_terms(self) -> None:
        builder = RetrievalProfileBuilder()
        profile = builder.build(
            topic="Danh gia TPBank EVO",
            keyword_map={
                "brand": ["TPBank EVO", "the evo"],
                "pain_points": ["phi thuong nien", "bi khoa the"],
                "comparison": ["tpbank evo hay vpbank"],
                "behavior": ["review dung the"],
                "sentiment": ["co tot khong"],
            },
        )

        self.assertIn("TPBank EVO", profile["anchors"])
        self.assertIn("phi thuong nien", profile["related_terms"])
        intents = [item["intent"] for item in profile["query_families"]]
        self.assertIn("brand", intents)
        self.assertIn("pain_point", intents)
        self.assertIn("question", intents)


class RetrievalScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = RetrievalProfileBuilder()
        self.profile = self.builder.build(
            topic="TPBank EVO",
            keyword_map={
                "brand": ["TPBank EVO"],
                "pain_points": ["phi thuong nien", "bi tru tien"],
                "comparison": [],
                "behavior": ["review mo the"],
                "sentiment": ["co tot khong"],
            },
        )
        self.engine = DeterministicRelevanceEngine()

    def test_accepts_relevant_post(self) -> None:
        result = self.engine.score(
            content="Minh dang dung TPBank EVO va bi tru phi thuong nien du da noi la mien phi nam dau.",
            retrieval_profile=self.profile,
            record_type="POST",
            source_type="SEARCH_POSTS",
            query_family="pain_point",
        )

        self.assertEqual(result.status, "ACCEPTED")
        self.assertGreater(result.score_total, 0.45)

    def test_rejects_promo_post(self) -> None:
        result = self.engine.score(
            content="Mo the TPBank EVO inbox em de nhan ref va uu dai khung nhe",
            retrieval_profile=self.profile,
            record_type="POST",
            source_type="SEARCH_POSTS",
            query_family="brand",
        )

        self.assertEqual(result.status, "REJECTED")

    def test_comment_can_pass_with_parent_context(self) -> None:
        result = self.engine.score(
            content="minh cung bi vay",
            retrieval_profile=self.profile,
            record_type="COMMENT",
            source_type="CRAWL_COMMENTS",
            query_family="pain_point",
            parent_text="TPBank EVO bi tru phi thuong nien du khong su dung",
            parent_status="ACCEPTED",
        )

        self.assertIn(result.status, {"ACCEPTED", "UNCERTAIN"})
        self.assertGreater(result.score_breakdown["parent_context_score"], 0)


class BatchHealthEvaluatorTests(unittest.TestCase):
    def test_marks_weak_batch(self) -> None:
        builder = RetrievalProfileBuilder()
        profile = builder.build(
            topic="TPBank EVO",
            keyword_map={"brand": ["TPBank EVO"], "pain_points": [], "comparison": [], "behavior": [], "sentiment": []},
        )
        engine = DeterministicRelevanceEngine()
        scores = [
            engine.score(
                content="xin chao moi nguoi",
                retrieval_profile=profile,
                record_type="POST",
                source_type="SEARCH_POSTS",
                query_family="brand",
            )
            for _ in range(5)
        ]
        evaluator = BatchHealthEvaluator(
            continue_ratio=0.25,
            weak_ratio=0.10,
            weak_uncertain_ratio=0.20,
            strong_accept_count=3,
        )
        health = evaluator.evaluate(scores)
        self.assertEqual(health.decision, "weak")


class CleanPayloadTests(unittest.TestCase):
    def test_removes_duplicate_and_ui_noise(self) -> None:
        cleaned, flags = clean_payload_text("Like\nComment\nTPBank EVO bi tru phi\nTPBank EVO bi tru phi")
        self.assertIn("duplicate_line_removed", flags)
        self.assertIn("ui_noise_removed", flags)
        self.assertIn("TPBank EVO bi tru phi", cleaned)


if __name__ == "__main__":
    unittest.main()
