from __future__ import annotations

from collections import Counter
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any


PROMO_TERMS = {
    "ib",
    "inbox",
    "ref",
    "chot don",
    "mo the",
    "mo tk",
    "booking",
    "sale",
    "khuyen mai",
    "uu dai khung",
}

UI_NOISE_TERMS = {
    "like",
    "comment",
    "share",
    "thich",
    "binh luan",
    "chia se",
    "xem them",
    "view more",
    "most relevant",
}

QUESTION_SUFFIXES = ("co tot khong", "co uy tin khong", "co nen dung khong")
COMPLAINT_PREFIXES = ("loi", "phi", "chan", "te", "bi khoa", "bi tru")
TRUST_SIGNAL_TERMS = ("trust", "uy tin", "lua dao", "fraud", "scam", "bi lua")
COST_SIGNAL_TERMS = ("phi", "fee", "lai", "interest", "chi phi", "gia cao")
SYMPTOM_SIGNAL_TERMS = ("kich ung", "mun", "da nhay cam", "side effect", "tac dung phu", "pain")
PROMO_REASON_TERMS = ("promot", "seller", "commercial", "cta", "transactional")
TARGET_REASON_TERMS = ("target", "mention", "brand", "entity")


def strip_diacritics(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    lowered = strip_diacritics(value).lower()
    lowered = re.sub(r"https?://\S+", " ", lowered)
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            continue
        normalized = normalize_text(cleaned)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(cleaned)
    return ordered


def clean_payload_text(value: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    lines: list[str] = []
    seen_lines: set[str] = set()
    for raw_line in re.split(r"[\r\n]+", value):
        line = re.sub(r"\s+", " ", raw_line).strip(" -")
        if not line:
            continue
        normalized = normalize_text(line)
        if not normalized:
            continue
        if normalized in seen_lines:
            flags.append("duplicate_line_removed")
            continue
        if normalized in UI_NOISE_TERMS:
            flags.append("ui_noise_removed")
            continue
        if len(normalized) < 3:
            continue
        seen_lines.add(normalized)
        lines.append(line)
    cleaned = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if len(cleaned) < 24:
        flags.append("too_short")
    return cleaned or value.strip(), dedupe_keep_order(flags)


@dataclass
class RetrievalScore:
    status: str
    score_total: float
    reason: str
    score_breakdown: dict[str, float]
    quality_flags: list[str]
    cleaned_text: str
    query_family: str


@dataclass
class BatchHealth:
    accepted_ratio: float
    uncertain_ratio: float
    strong_accept_count: int
    accepted_count: int
    uncertain_count: int
    rejected_count: int
    decision: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted_ratio": round(self.accepted_ratio, 4),
            "uncertain_ratio": round(self.uncertain_ratio, 4),
            "strong_accept_count": self.strong_accept_count,
            "accepted_count": self.accepted_count,
            "uncertain_count": self.uncertain_count,
            "rejected_count": self.rejected_count,
            "decision": self.decision,
        }


class RetrievalProfileBuilder:
    def build(self, *, topic: str, keyword_map: dict[str, list[str]] | None) -> dict[str, Any]:
        keyword_map = keyword_map or {}
        brand_terms = dedupe_keep_order(keyword_map.get("brand", []))
        pain_terms = dedupe_keep_order(keyword_map.get("pain_points", []))
        behavior_terms = dedupe_keep_order(keyword_map.get("behavior", []))
        comparison_terms = dedupe_keep_order(keyword_map.get("comparison", []))
        sentiment_terms = dedupe_keep_order(keyword_map.get("sentiment", []))

        anchors = dedupe_keep_order(brand_terms + [topic])
        related_terms = dedupe_keep_order(pain_terms + behavior_terms + comparison_terms + sentiment_terms)
        negative_terms = dedupe_keep_order(list(PROMO_TERMS))
        base_query = anchors[0] if anchors else topic

        query_families = [
            {"intent": "brand", "query": base_query},
        ]
        for term in pain_terms[:2]:
            query_families.append({"intent": "pain_point", "query": term})
        for suffix in QUESTION_SUFFIXES[:2]:
            query_families.append({"intent": "question", "query": f"{base_query} {suffix}".strip()})
        for term in comparison_terms[:2]:
            query_families.append({"intent": "comparison", "query": term})
        for prefix in COMPLAINT_PREFIXES[:2]:
            query_families.append({"intent": "complaint", "query": f"{prefix} {base_query}".strip()})

        source_hints = dedupe_keep_order(brand_terms[:3] + pain_terms[:2])
        return {
            "anchors": anchors[:8],
            "related_terms": related_terms[:16],
            "negative_terms": negative_terms[:16],
            "query_families": query_families[:8],
            "source_hints": source_hints[:5],
        }

    def serialize(self, profile: dict[str, Any]) -> str:
        return json.dumps(profile, ensure_ascii=False)

    def infer_query_family(self, query: str, profile: dict[str, Any] | None) -> str:
        normalized_query = normalize_text(query)
        if not profile:
            return "generic"
        for family in profile.get("query_families", []):
            family_query = normalize_text(str(family.get("query") or ""))
            if family_query and (family_query in normalized_query or normalized_query in family_query):
                return str(family.get("intent") or "generic")
        if "?" in query or "co " in query.lower():
            return "question"
        return "generic"

    def suggest_queries(
        self,
        query: str,
        profile: dict[str, Any] | None,
        *,
        validity_spec: dict[str, Any] | None = None,
        max_variants: int = 2,
    ) -> list[str]:
        profile = profile or {}
        max_variants = max(1, max_variants)
        normalized_query = normalize_text(query)
        query_families = profile.get("query_families", [])
        incomplete_comparison = normalized_query.endswith(" vs") or " vs " in normalized_query
        preferred_intents = self._preferred_intents(query, profile, validity_spec)

        ordered_queries: list[str] = []
        if not incomplete_comparison:
            ordered_queries.append(query)
            ordered_queries.extend(self._build_semantic_expansions(query, profile, validity_spec))

        primary_inserted = False
        for intent in preferred_intents:
            for family in query_families:
                if family.get("intent") != intent:
                    continue
                candidate = str(family.get("query") or "").strip()
                if candidate:
                    ordered_queries.append(candidate)
            if incomplete_comparison and not primary_inserted:
                ordered_queries.append(query)
                primary_inserted = True

        ordered_queries.append(query)
        return dedupe_keep_order(ordered_queries)[:max_variants]

    def build_reformulations(
        self,
        query: str,
        profile: dict[str, Any] | None,
        validity_spec: dict[str, Any] | None,
        reason_cluster: str,
        *,
        max_variants: int = 2,
    ) -> list[str]:
        ordered: list[str] = []
        base_query = self._base_query(query, profile)
        if reason_cluster == "promo_noise":
            ordered.extend(
                [
                    f"{base_query} bi lua".strip(),
                    f"{base_query} co uy tin khong".strip(),
                    f"review {base_query}".strip(),
                ]
            )
        elif reason_cluster == "trust_gap":
            ordered.extend(
                [
                    f"{base_query} bi lua".strip(),
                    f"{base_query} co uy tin khong".strip(),
                ]
            )
        elif reason_cluster == "cost_gap":
            ordered.extend(
                [
                    f"{base_query} phi cao".strip(),
                    f"{base_query} lai suat cao".strip(),
                ]
            )
        elif reason_cluster == "symptom_gap":
            for term in (profile or {}).get("related_terms", [])[:2]:
                ordered.append(f"{base_query} {term}".strip())
        elif reason_cluster == "target_weak":
            ordered.extend([base_query, f"review {base_query}".strip()])

        ordered.extend(
            self.suggest_queries(
                query,
                profile,
                validity_spec=validity_spec,
                max_variants=max(max_variants + 1, 3),
            )
        )
        return [candidate for candidate in dedupe_keep_order(ordered) if normalize_text(candidate) != normalize_text(query)][
            :max_variants
        ]

    def cluster_reject_reasons(
        self,
        reason_codes: list[str],
        *,
        query: str,
        validity_spec: dict[str, Any] | None = None,
    ) -> str:
        counter: Counter[str] = Counter()
        validity_text = self._validity_signal_text(validity_spec)
        normalized_query = normalize_text(query)
        for reason_code in reason_codes:
            normalized = normalize_text(reason_code)
            if any(token in normalized for token in PROMO_REASON_TERMS):
                counter["promo_noise"] += 1
            elif any(token in normalized for token in TARGET_REASON_TERMS):
                counter["target_weak"] += 1
            elif any(token in normalized for token in COST_SIGNAL_TERMS):
                counter["cost_gap"] += 1
            elif any(token in normalized for token in TRUST_SIGNAL_TERMS):
                counter["trust_gap"] += 1
            elif any(token in normalized for token in SYMPTOM_SIGNAL_TERMS):
                counter["symptom_gap"] += 1
            else:
                counter["generic_weak"] += 1

        if any(token in validity_text for token in TRUST_SIGNAL_TERMS) and not any(
            token in normalized_query for token in TRUST_SIGNAL_TERMS
        ):
            counter["trust_gap"] += 1
        if any(token in validity_text for token in COST_SIGNAL_TERMS) and not any(
            token in normalized_query for token in COST_SIGNAL_TERMS
        ):
            counter["cost_gap"] += 1
        if any(token in validity_text for token in SYMPTOM_SIGNAL_TERMS) and not any(
            token in normalized_query for token in SYMPTOM_SIGNAL_TERMS
        ):
            counter["symptom_gap"] += 1
        if not counter:
            return "generic_weak"
        return counter.most_common(1)[0][0]

    def _preferred_intents(
        self,
        query: str,
        profile: dict[str, Any] | None,
        validity_spec: dict[str, Any] | None,
    ) -> list[str]:
        normalized_query = normalize_text(query)
        validity_text = self._validity_signal_text(validity_spec)
        if normalized_query.endswith(" vs") or " vs " in normalized_query:
            return ["comparison", "pain_point", "question", "complaint"]
        if any(term in normalized_query for term in ("fake", "lua dao", "loi", "te")):
            return ["complaint", "pain_point", "question", "comparison"]
        if any(term in validity_text for term in TRUST_SIGNAL_TERMS + COST_SIGNAL_TERMS):
            return ["complaint", "pain_point", "question", "comparison", "brand"]
        if any(term in validity_text for term in SYMPTOM_SIGNAL_TERMS):
            return ["pain_point", "question", "comparison", "complaint", "brand"]
        inferred_family = self.infer_query_family(query, profile)
        if inferred_family in {"generic", "brand"}:
            return ["pain_point", "question", "comparison", "complaint"]
        if inferred_family == "comparison":
            return ["comparison", "pain_point", "question", "complaint"]
        return ["question", "pain_point", "comparison", "complaint"]

    def _build_semantic_expansions(
        self,
        query: str,
        profile: dict[str, Any] | None,
        validity_spec: dict[str, Any] | None,
    ) -> list[str]:
        profile = profile or {}
        validity_text = self._validity_signal_text(validity_spec)
        base_query = self._base_query(query, profile)
        expansions: list[str] = []
        if any(term in validity_text for term in TRUST_SIGNAL_TERMS):
            expansions.extend(
                [
                    f"{base_query} bi lua".strip(),
                ]
            )
        if any(term in validity_text for term in COST_SIGNAL_TERMS):
            expansions.extend(
                [
                    f"{base_query} phi cao".strip(),
                    f"{base_query} lai suat cao".strip(),
                ]
            )
        if any(term in validity_text for term in TRUST_SIGNAL_TERMS):
            expansions.extend(
                [
                    f"{base_query} review".strip(),
                    f"{base_query} co uy tin khong".strip(),
                ]
            )
        for term in profile.get("related_terms", [])[:2]:
            expansions.append(f"{base_query} {term}".strip())
        return [candidate for candidate in dedupe_keep_order(expansions) if normalize_text(candidate) != normalize_text(query)]

    def _validity_signal_text(self, validity_spec: dict[str, Any] | None) -> str:
        validity_spec = validity_spec or {}
        joined = " ".join(
            [
                str(validity_spec.get("research_objective") or ""),
                " ".join(str(item) for item in validity_spec.get("target_signal_types", [])),
                " ".join(str(item) for item in validity_spec.get("must_have_signals", [])),
            ]
        )
        return normalize_text(joined)

    def _base_query(self, query: str, profile: dict[str, Any] | None) -> str:
        profile = profile or {}
        anchors = profile.get("anchors", [])
        return str(anchors[0] if anchors else query).strip()


class DeterministicRelevanceEngine:
    def score(
        self,
        *,
        content: str,
        retrieval_profile: dict[str, Any] | None,
        record_type: str,
        source_type: str,
        query_family: str,
        parent_text: str | None = None,
        parent_status: str | None = None,
    ) -> RetrievalScore:
        cleaned_text, quality_flags = clean_payload_text(content)
        normalized_text = normalize_text(cleaned_text)
        profile = retrieval_profile or {}
        anchors = [normalize_text(term) for term in profile.get("anchors", [])]
        related_terms = [normalize_text(term) for term in profile.get("related_terms", [])]
        negative_terms = [normalize_text(term) for term in profile.get("negative_terms", [])]

        anchor_hits = sum(1 for term in anchors if term and term in normalized_text)
        related_hits = sum(1 for term in related_terms if term and term in normalized_text)
        negative_hits = sum(1 for term in negative_terms if term and term in normalized_text)

        anchor_score = min(anchor_hits * 0.22, 0.44)
        related_score = min(related_hits * 0.06, 0.24)
        negative_penalty = min(negative_hits * 0.18, 0.54)
        quality_score = 0.0
        if len(normalized_text) >= 24:
            quality_score += 0.10
        if len(normalized_text) >= 80:
            quality_score += 0.08
        if "too_short" in quality_flags:
            quality_score -= 0.08
        if "ui_noise_removed" in quality_flags:
            quality_score -= 0.02

        source_score = 0.06 if source_type in {"SEARCH_IN_GROUP", "CRAWL_FEED"} else 0.03
        parent_context_score = 0.0
        if record_type == "COMMENT":
            normalized_parent = normalize_text(parent_text or "")
            if parent_status == "ACCEPTED":
                parent_context_score += 0.18
            if normalized_parent:
                parent_context_score += 0.06
                if any(term and term in normalized_parent for term in anchors[:3]):
                    parent_context_score += 0.06

        score_total = round(
            anchor_score + related_score + quality_score + source_score + parent_context_score - negative_penalty,
            4,
        )
        breakdown = {
            "anchor_score": round(anchor_score, 4),
            "related_score": round(related_score, 4),
            "quality_score": round(quality_score, 4),
            "source_score": round(source_score, 4),
            "parent_context_score": round(parent_context_score, 4),
            "negative_penalty": round(negative_penalty, 4),
        }
        if record_type == "COMMENT":
            accepted_threshold = 0.36
            uncertain_threshold = 0.20
        else:
            accepted_threshold = 0.48
            uncertain_threshold = 0.30
        if anchor_score >= 0.22 and score_total >= accepted_threshold:
            status = "ACCEPTED"
        elif score_total >= accepted_threshold:
            status = "ACCEPTED"
        elif score_total >= uncertain_threshold:
            status = "UNCERTAIN"
        else:
            status = "REJECTED"

        if negative_penalty >= 0.36 and status == "ACCEPTED":
            status = "UNCERTAIN"
        if "too_short" in quality_flags and status == "ACCEPTED":
            status = "UNCERTAIN"
        if record_type == "COMMENT" and parent_context_score >= 0.18 and status == "REJECTED":
            status = "UNCERTAIN"

        reason_parts: list[str] = []
        if anchor_hits:
            reason_parts.append(f"anchor_hits={anchor_hits}")
        if related_hits:
            reason_parts.append(f"related_hits={related_hits}")
        if negative_hits:
            reason_parts.append(f"negative_hits={negative_hits}")
        if record_type == "COMMENT" and parent_context_score > 0:
            reason_parts.append("parent_context")
        if not reason_parts:
            reason_parts.append("weak_signal")
        return RetrievalScore(
            status=status,
            score_total=max(score_total, 0.0),
            reason=", ".join(reason_parts),
            score_breakdown=breakdown,
            quality_flags=quality_flags,
            cleaned_text=cleaned_text,
            query_family=query_family,
        )


class BatchHealthEvaluator:
    def __init__(self, *, continue_ratio: float, weak_ratio: float, weak_uncertain_ratio: float, strong_accept_count: int) -> None:
        self._continue_ratio = continue_ratio
        self._weak_ratio = weak_ratio
        self._weak_uncertain_ratio = weak_uncertain_ratio
        self._strong_accept_count = strong_accept_count

    def evaluate(self, scores: list[RetrievalScore]) -> BatchHealth:
        total = max(len(scores), 1)
        accepted_count = sum(1 for score in scores if score.status == "ACCEPTED")
        uncertain_count = sum(1 for score in scores if score.status == "UNCERTAIN")
        rejected_count = sum(1 for score in scores if score.status == "REJECTED")
        strong_accept_count = sum(1 for score in scores if score.status == "ACCEPTED" and score.score_total >= 0.7)
        accepted_ratio = accepted_count / total
        uncertain_ratio = uncertain_count / total
        decision = "continue"
        if accepted_ratio < self._weak_ratio and uncertain_ratio < self._weak_uncertain_ratio:
            decision = "weak"
        if accepted_ratio >= self._continue_ratio or strong_accept_count >= self._strong_accept_count:
            decision = "continue"
        return BatchHealth(
            accepted_ratio=accepted_ratio,
            uncertain_ratio=uncertain_ratio,
            strong_accept_count=strong_accept_count,
            accepted_count=accepted_count,
            uncertain_count=uncertain_count,
            rejected_count=rejected_count,
            decision=decision,
        )
