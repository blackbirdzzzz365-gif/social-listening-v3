from __future__ import annotations

import unittest

from app.services.runner import RunnerService


class RunnerSourcePrefilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = object.__new__(RunnerService)
        self.runner._source_filter_group_terms = (
            "vay tien",
            "vay von",
            "ho tro vay",
            "tin dung",
            "the chap",
            "tra gop",
            "dao han",
            "rut tien",
            "mo the",
            "tai chinh",
            "finance",
        )
        self.runner._source_filter_discussion_terms = (
            "review",
            "hoi dap",
            "kinh nghiem",
            "phan hoi",
            "so sanh",
            "cong dong",
            "khach hang",
        )
        self.validity_spec = {
            "research_objective": "Find comparative end-user insights about Shinhan cash loans versus competing banks.",
            "target_author_types": ["consumers actively comparing multiple banks"],
            "non_target_author_types": ["bank representatives", "pure product advertisers"],
            "hard_reject_signals": ["pure promotional content", "transactional requests"],
            "target_signal_types": ["comparative analysis between Shinhan and other banks"],
        }
        self.profile = {
            "anchors": ["Shinhan", "vay tien mat tai shinhan"],
        }

    def test_rejects_broker_group_sources_early(self) -> None:
        filter_result = self.runner._source_prefilter(
            raw={
                "post_id": "post-1",
                "content": "Tu van vay nhanh.",
                "source_group_name": "Vay tien mat Quang Ngai 0979725952",
                "source_url": "https://www.facebook.com/groups/757487308289548/?multi_permalinks=895612761143668",
            },
            query_family="brand",
            query_text="Vay tien mat Shinhan",
            profile=self.profile,
            validity_spec=self.validity_spec,
        )

        self.assertIsNotNone(filter_result)
        assert filter_result is not None
        self.assertEqual(filter_result.reason_code, "source_prefilter_broker_group")

    def test_rejects_official_brand_pages_for_brand_queries(self) -> None:
        filter_result = self.runner._source_prefilter(
            raw={
                "post_id": "post-2",
                "content": "Shinhan Life uu dai moi.",
                "source_group_name": "",
                "source_url": "https://www.facebook.com/shinhanlifevietnam/posts/pfbid0BnyJdqgLpUEYu2HgAUPbih89VeR4xt1kK8k4YfhQovJdqVZKs5EbvcXVeq6jwqbbl",
            },
            query_family="brand",
            query_text="Shinhan",
            profile=self.profile,
            validity_spec=self.validity_spec,
        )

        self.assertIsNotNone(filter_result)
        assert filter_result is not None
        self.assertEqual(filter_result.reason_code, "source_prefilter_official_brand_page")

    def test_keeps_discussion_community_sources(self) -> None:
        filter_result = self.runner._source_prefilter(
            raw={
                "post_id": "post-3",
                "content": "Moi nguoi review vay Shinhan voi.",
                "source_group_name": "Cong dong khach hang Shinhan Bank Viet Nam",
                "source_url": "https://www.facebook.com/groups/3495470807389694/?multi_permalinks=3822307824705989",
            },
            query_family="brand",
            query_text="Vay tien mat Shinhan",
            profile=self.profile,
            validity_spec=self.validity_spec,
        )

        self.assertIsNone(filter_result)


if __name__ == "__main__":
    unittest.main()
