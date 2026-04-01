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

    def test_suggests_comparison_fallback_for_incomplete_vs_query(self) -> None:
        builder = RetrievalProfileBuilder()
        profile = builder.build(
            topic="mặt nạ ngũ hoa",
            keyword_map={
                "brand": ["mặt nạ ngũ hoa"],
                "pain_points": ["mặt nạ ngũ hoa hiệu quả không"],
                "comparison": ["mặt nạ ngũ hoa vs thương hiệu khác"],
                "behavior": [],
                "sentiment": [],
            },
        )

        queries = builder.suggest_queries("mặt nạ ngũ hoa vs", profile, max_variants=2)

        self.assertEqual(len(queries), 2)
        self.assertEqual(queries[0], "mặt nạ ngũ hoa vs thương hiệu khác")
        self.assertEqual(queries[1], "mặt nạ ngũ hoa vs")

    def test_prioritizes_trust_and_cost_queries_when_validity_spec_demands_it(self) -> None:
        builder = RetrievalProfileBuilder()
        profile = builder.build(
            topic="FE Credit",
            keyword_map={
                "brand": ["FE Credit"],
                "pain_points": ["phi cao", "lãi suất cao"],
                "comparison": [],
                "behavior": [],
                "sentiment": [],
            },
        )

        queries = builder.suggest_queries(
            "FE Credit",
            profile,
            validity_spec={
                "research_objective": "Tim trustworthiness va fee complaints ve FE Credit.",
                "target_signal_types": ["trustworthiness_assessment", "fee_complaint_signal"],
                "must_have_signals": ["customer fraud warning", "interest rate discussion"],
            },
            max_variants=3,
        )

        self.assertIn("FE Credit bi lua", queries)
        self.assertIn("FE Credit phi cao", queries)

    def test_builds_reason_aware_reformulations(self) -> None:
        builder = RetrievalProfileBuilder()
        profile = builder.build(
            topic="mặt nạ ngũ hoa",
            keyword_map={
                "brand": ["mặt nạ ngũ hoa"],
                "pain_points": ["kích ứng", "mụn"],
                "comparison": [],
                "behavior": [],
                "sentiment": ["review"],
            },
        )

        cluster = builder.cluster_reject_reasons(
            ["commercial_noise", "seller_cta"],
            query="mặt nạ ngũ hoa",
            validity_spec={"research_objective": "Tim review that va tac dung phu neu co."},
        )
        reformulations = builder.build_reformulations(
            "mặt nạ ngũ hoa",
            profile,
            {"research_objective": "Tim review that va tac dung phu neu co."},
            cluster,
            max_variants=2,
        )

        self.assertEqual(cluster, "promo_noise")
        self.assertTrue(any("review" in query.lower() or "bi lua" in query.lower() for query in reformulations))

    def test_adds_image_bearing_queries_for_visual_topics(self) -> None:
        builder = RetrievalProfileBuilder()
        profile = builder.build(
            topic="Review co hinh anh ve mat na Ngu Hoa truoc va sau khi dung",
            keyword_map={
                "brand": ["mat na Ngu Hoa"],
                "pain_points": ["kich ung"],
                "comparison": [],
                "behavior": [],
                "sentiment": [],
            },
        )

        intents = [item["intent"] for item in profile["query_families"]]
        self.assertIn("image_review", intents)
        self.assertIn("before_after", intents)

        queries = builder.suggest_queries(
            "mat na Ngu Hoa",
            profile,
            validity_spec={
                "research_objective": "Tim review co hinh anh va bang chung truoc va sau cua mat na Ngu Hoa.",
                "target_signal_types": ["visual_review_signal"],
                "must_have_signals": ["hinh anh that", "truoc va sau"],
            },
            max_variants=3,
        )

        self.assertIn("mat na Ngu Hoa review co hinh anh", queries)


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
