from __future__ import annotations

import unittest

from app.services.comment_context import build_context_map, build_record_context
from app.services.labeling_heuristics import classify_content


class CommentHeuristicsTests(unittest.TestCase):
    def test_comment_always_stays_ai_reviewable(self) -> None:
        result = classify_content(
            record_type="COMMENT",
            content="Co ai duoc mien phi nam dau khong vay?",
            parent_summary="Parent post: TPBank EVO bi tru phi thuong nien.",
            source_url="https://www.facebook.com/groups/demo/posts/1?comment_id=2",
        )

        self.assertFalse(result.should_skip_ai)
        self.assertEqual(result.payload["label_source"], "hybrid")
        self.assertEqual(result.payload["label_reason"], "comment_requires_thread_context")


class CommentContextTests(unittest.TestCase):
    def test_builds_reply_context_with_parent_comment_and_post(self) -> None:
        posts = [
            {
                "post_id": "post-1",
                "record_type": "POST",
                "content": "Da mun boi tretinoin bi bong troc va do rat nhieu ngay.",
                "content_masked": "Da mun boi tretinoin bi bong troc va do rat nhieu ngay.",
                "parent_post_id": None,
            },
            {
                "post_id": "comment-1",
                "record_type": "COMMENT",
                "content": "Minh cung bi y nhu vay tuan dau.",
                "content_masked": "Minh cung bi y nhu vay tuan dau.",
                "parent_post_id": "post-1",
            },
            {
                "post_id": "comment-2",
                "record_type": "COMMENT",
                "content": "Ban giam tan suat xuong cach ngay thu chua?",
                "content_masked": "Ban giam tan suat xuong cach ngay thu chua?",
                "parent_post_id": "comment-1",
            },
        ]

        context_map = build_context_map(posts)
        context = build_record_context(posts[2], context_map)

        self.assertEqual(context["parent_comment_summary"], "Minh cung bi y nhu vay tuan dau.")
        self.assertEqual(context["parent_post_summary"], "Da mun boi tretinoin bi bong troc va do rat nhieu ngay.")
        self.assertIn("Parent post:", context["thread_context"] or "")
        self.assertIn("Parent comment:", context["thread_context"] or "")

    def test_top_level_comment_keeps_only_parent_post_context(self) -> None:
        posts = [
            {
                "post_id": "post-1",
                "record_type": "POST",
                "content": "Routine tri mun nay dang gay bong da quanh mieng.",
                "content_masked": "Routine tri mun nay dang gay bong da quanh mieng.",
                "parent_post_id": None,
            },
            {
                "post_id": "comment-1",
                "record_type": "COMMENT",
                "content": "Minh gap y chang sau 3 ngay dau.",
                "content_masked": "Minh gap y chang sau 3 ngay dau.",
                "parent_post_id": "post-1",
            },
        ]

        context_map = build_context_map(posts)
        context = build_record_context(posts[1], context_map)

        self.assertIsNone(context["parent_comment_summary"])
        self.assertEqual(context["parent_post_summary"], "Routine tri mun nay dang gay bong da quanh mieng.")
        self.assertEqual(context["thread_context"], "Parent post: Routine tri mun nay dang gay bong da quanh mieng.")


if __name__ == "__main__":
    unittest.main()
