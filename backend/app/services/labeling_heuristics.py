from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.label_taxonomy import TAXONOMY_VERSION


@dataclass
class HeuristicLabelResult:
    payload: dict[str, object]
    confidence: float
    should_skip_ai: bool
    signals: list[str]


SELLER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bib\b",
        r"\binbox\b",
        r"\bzalo\b",
        r"li[eê]n h[ệe]",
        r"\bhotline\b",
        r"đăng ký|dang ky|mở thẻ|mo the|tư vấn|tu van",
        r"ưu đãi|uu dai|khuyến mãi|khuyen mai|combo|deal|ref",
    )
]
OFFICIAL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"fanpage ch[íi]nh th[ứu]c|fanpage chinh thuc|official",
        r"\bcskh\b|chăm sóc khách hàng|cham soc khach hang",
        r"thông báo|thong bao",
    )
]
ADMIN_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\badmin\b",
        r"\bmod\b",
        r"quản trị viên|quan tri vien",
        r"duyệt bài|duyet bai|nội quy|noi quy",
    )
]
QUESTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"cho em hỏi|cho minh hoi|cho mình hỏi|xin review",
        r"có ai|co ai|ai biết|ai biet",
        r"nên|nen|sao|thế nào|the nao",
    )
]
EXPERIENCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"mình dùng|minh dung|em dùng|em dung",
        r"mình bị|minh bi|em bị|em bi",
        r"trải nghiệm|trai nghiem|review",
        r"phí|phi|lỗi|loi|hoàn tiền|hoan tien|từ chối|tu choi",
    )
]
SUPPORT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"vui lòng|vui long",
        r"liên hệ inbox|lien he inbox",
        r"ad check ib|page hỗ trợ|page ho tro",
    )
]
COMPARISON_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"so sánh|so sanh|\bvs\b",
        r"khác gì|khac gi|hơn|hon",
    )
]


def classify_content(
    *,
    record_type: str,
    content: str,
    parent_summary: str | None = None,
    source_url: str | None = None,
) -> HeuristicLabelResult:
    text = " ".join(part for part in [content, parent_summary or "", source_url or ""] if part).strip()
    seller_hits = _count_hits(SELLER_PATTERNS, text)
    official_hits = _count_hits(OFFICIAL_PATTERNS, text)
    admin_hits = _count_hits(ADMIN_PATTERNS, text)
    question_hits = _count_hits(QUESTION_PATTERNS, text)
    experience_hits = _count_hits(EXPERIENCE_PATTERNS, text)
    support_hits = _count_hits(SUPPORT_PATTERNS, text)
    comparison_hits = _count_hits(COMPARISON_PATTERNS, text)

    signals: list[str] = []
    if seller_hits:
        signals.append(f"seller:{seller_hits}")
    if official_hits:
        signals.append(f"official:{official_hits}")
    if admin_hits:
        signals.append(f"admin:{admin_hits}")
    if question_hits:
        signals.append(f"question:{question_hits}")
    if experience_hits:
        signals.append(f"experience:{experience_hits}")
    if support_hits:
        signals.append(f"support:{support_hits}")
    if comparison_hits:
        signals.append(f"comparison:{comparison_hits}")

    payload = {
        "author_role": "unknown",
        "content_intent": "other",
        "commerciality_level": "medium",
        "user_feedback_relevance": "low",
        "label_confidence": 0.55,
        "label_reason": "ambiguous_content_needs_ai_review",
        "label_source": "hybrid",
        "taxonomy_version": TAXONOMY_VERSION,
    }
    confidence = 0.55
    should_skip_ai = False

    if admin_hits:
        payload.update(
            author_role="community_admin",
            content_intent="other",
            commerciality_level="low",
            user_feedback_relevance="low",
            label_reason="admin_or_group_rule_markers_detected",
            label_source="heuristic",
        )
        confidence = 0.94
        should_skip_ai = True
    elif official_hits and support_hits:
        payload.update(
            author_role="brand_official",
            content_intent="support_answer",
            commerciality_level="medium",
            user_feedback_relevance="low",
            label_reason="official_support_markers_detected",
            label_source="heuristic",
        )
        confidence = 0.93
        should_skip_ai = True
    elif seller_hits >= 2 and question_hits == 0 and experience_hits == 0:
        payload.update(
            author_role="seller_affiliate",
            content_intent="promotion",
            commerciality_level="high",
            user_feedback_relevance="low",
            label_reason="promotion_markers_detected",
            label_source="heuristic",
        )
        confidence = 0.92
        should_skip_ai = True
    elif experience_hits and seller_hits == 0 and official_hits == 0:
        payload.update(
            author_role="end_user",
            content_intent="experience",
            commerciality_level="low",
            user_feedback_relevance="high",
            label_reason="experience_markers_detected",
            label_source="heuristic",
        )
        confidence = 0.9
        should_skip_ai = True
    elif question_hits and seller_hits == 0 and official_hits == 0:
        payload.update(
            author_role="end_user",
            content_intent="question",
            commerciality_level="low",
            user_feedback_relevance="high" if record_type == "COMMENT" else "medium",
            label_reason="question_markers_detected",
            label_source="heuristic",
        )
        confidence = 0.88
        should_skip_ai = True
    elif comparison_hits and experience_hits:
        payload.update(
            author_role="end_user",
            content_intent="comparison",
            commerciality_level="low",
            user_feedback_relevance="medium",
            label_reason="comparison_and_experience_markers_detected",
            label_source="heuristic",
        )
        confidence = 0.86
        should_skip_ai = True

    if record_type == "COMMENT":
        should_skip_ai = False
        payload["label_source"] = "hybrid"
        payload["label_reason"] = "comment_requires_thread_context"
        confidence = min(confidence, 0.72)

    payload["label_confidence"] = confidence
    return HeuristicLabelResult(
        payload=payload,
        confidence=confidence,
        should_skip_ai=should_skip_ai,
        signals=signals,
    )


def fallback_label(reason: str = "fallback_label_applied") -> dict[str, object]:
    return {
        "author_role": "unknown",
        "content_intent": "other",
        "commerciality_level": "medium",
        "user_feedback_relevance": "low",
        "label_confidence": 0.35,
        "label_reason": reason,
        "label_source": "fallback",
        "taxonomy_version": TAXONOMY_VERSION,
    }


def _count_hits(patterns: list[re.Pattern[str]], text: str) -> int:
    lowered = text.lower()
    return sum(1 for pattern in patterns if pattern.search(lowered))
