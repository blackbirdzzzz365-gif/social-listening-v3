from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.infra.ai_client import AIClient
from app.infrastructure.config import Settings
from app.schemas.phase8 import JudgeResult, ValiditySpec
from app.services.retrieval_quality import (
    DeterministicRelevanceEngine,
    RetrievalScore,
    clean_payload_text,
    normalize_text,
)

TRANSACTIONAL_COMMENT_PATTERNS = (
    "xin gia",
    "gia bn",
    "bao nhieu",
    "ib",
    "inbox",
    "check ib",
    "check inbox",
    "con hang",
    "ship",
)
SEVERE_UI_NOISE_PATTERNS = (
    "like comment share",
    "thich binh luan chia se",
    "view more",
    "xem them",
)


def _slugify(value: str) -> str:
    lowered = normalize_text(value.replace("đ", "d").replace("Đ", "D"))
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered or "research"


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:10]


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
        if not cleaned:
            continue
        normalized = normalize_text(cleaned)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(cleaned)
    return ordered


@dataclass
class HardFilterResult:
    rejected: bool
    decision: str
    reason_code: str
    rationale: str
    cleaned_text: str
    quality_flags: list[str]


@dataclass
class BatchHealthV2:
    accepted_ratio: float
    uncertain_ratio: float
    high_conf_accept_ratio: float
    mean_confidence: float
    accepted_count: int
    uncertain_count: int
    rejected_count: int
    high_conf_accept_count: int
    decision: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted_ratio": round(self.accepted_ratio, 4),
            "uncertain_ratio": round(self.uncertain_ratio, 4),
            "high_conf_accept_ratio": round(self.high_conf_accept_ratio, 4),
            "mean_confidence": round(self.mean_confidence, 4),
            "accepted_count": self.accepted_count,
            "uncertain_count": self.uncertain_count,
            "rejected_count": self.rejected_count,
            "high_conf_accept_count": self.high_conf_accept_count,
            "decision": self.decision,
        }


class ValiditySpecBuilder:
    def __init__(self, ai_client: AIClient, settings: Settings) -> None:
        self._ai_client = ai_client
        self._settings = settings
        self._prompt_path = Path(__file__).resolve().parents[1] / "skills" / "validity_spec_builder.md"

    async def build(
        self,
        *,
        topic: str,
        clarification_history: list[dict[str, str]],
        keywords: dict[str, list[str]] | None,
        retrieval_profile: dict[str, Any] | None,
        plan_intent: str | None = None,
    ) -> dict[str, Any]:
        fallback = self._build_fallback_spec(
            topic=topic,
            clarification_history=clarification_history,
            keywords=keywords,
            retrieval_profile=retrieval_profile,
            plan_intent=plan_intent,
        )
        prompt = self._prompt_path.read_text(encoding="utf-8")
        try:
            response = await self._ai_client.call(
                model=self._settings.validity_spec_model,
                system_prompt=prompt,
                user_input=json.dumps(
                    {
                        "topic": topic,
                        "clarification_history": clarification_history,
                        "keywords": keywords or {},
                        "retrieval_profile": retrieval_profile or {},
                        "plan_intent": plan_intent or "",
                    },
                    ensure_ascii=False,
                ),
                thinking=self._settings.validity_spec_thinking,
            )
        except Exception:
            response = {}
        return self._normalize_validity_spec(
            topic=topic,
            candidate=response,
            fallback=fallback,
            clarification_history=clarification_history,
            keywords=keywords or {},
            retrieval_profile=retrieval_profile or {},
            plan_intent=plan_intent,
        )

    def _build_fallback_spec(
        self,
        *,
        topic: str,
        clarification_history: list[dict[str, str]],
        keywords: dict[str, list[str]] | None,
        retrieval_profile: dict[str, Any] | None,
        plan_intent: str | None,
    ) -> dict[str, Any]:
        keyword_map = keywords or {}
        related = _dedupe_keep_order(
            keyword_map.get("pain_points", [])
            + keyword_map.get("comparison", [])
            + keyword_map.get("sentiment", [])
        )
        author_focus = "end_user"
        if any("seller" in normalize_text(item.get("answer", "")) for item in clarification_history):
            author_focus = "seller_affiliate"
        research_objective = (
            plan_intent
            or f"Find research-useful Facebook posts and comments about {topic} with real user signals."
        )
        spec = {
            "research_objective": research_objective,
            "target_signal_types": _dedupe_keep_order(
                ["end_user_experience", "pain_point", "comparison", "question_with_problem_context"]
            ),
            "target_author_types": [author_focus],
            "non_target_author_types": _dedupe_keep_order(["brand_official", "seller_affiliate"] if author_focus == "end_user" else ["brand_official"]),
            "must_have_signals": _dedupe_keep_order(
                [
                    f"clear signal about {topic}",
                    "real user problem, experience, comparison, or question with context",
                ]
            ),
            "nice_to_have_signals": related[:6],
            "hard_reject_signals": _dedupe_keep_order(
                [
                    "pure promotion",
                    "seller cta",
                    "price-only inquiry",
                    "inbox-only request",
                    "duplicate thread noise",
                ]
            ),
            "comment_policy": {
                "allow_parent_context": True,
                "reject_transactional_only_comments": author_focus == "end_user",
                "minimum_comment_text_length": 8 if author_focus == "end_user" else 4,
            },
            "valid_examples": [
                f"Minh da dung {topic} va gap van de cu the.",
                f"So sanh {topic} voi lua chon khac dua tren trai nghiem that.",
            ],
            "invalid_examples": [
                "Inbox de nhan gia.",
                "Con hang, ship toan quoc.",
            ],
            "batch_policy": {
                "min_accept_ratio": 0.15,
                "min_high_conf_accept_ratio": 0.05,
                "max_consecutive_weak_batches": max(1, int(getattr(self._settings, "retrieval_max_consecutive_weak_batches", 2))),
                "uncertain_reformulation_floor": 0.25,
            },
        }
        return self._normalize_validity_spec(
            topic=topic,
            candidate=spec,
            fallback=spec,
            clarification_history=clarification_history,
            keywords=keyword_map,
            retrieval_profile=retrieval_profile or {},
            plan_intent=plan_intent,
        )

    def _normalize_validity_spec(
        self,
        *,
        topic: str,
        candidate: dict[str, Any] | None,
        fallback: dict[str, Any],
        clarification_history: list[dict[str, str]],
        keywords: dict[str, list[str]],
        retrieval_profile: dict[str, Any],
        plan_intent: str | None,
    ) -> dict[str, Any]:
        payload = dict(fallback)
        if isinstance(candidate, dict):
            for key in (
                "research_objective",
                "target_signal_types",
                "target_author_types",
                "non_target_author_types",
                "must_have_signals",
                "nice_to_have_signals",
                "hard_reject_signals",
                "comment_policy",
                "valid_examples",
                "invalid_examples",
                "batch_policy",
            ):
                if key in candidate and candidate.get(key) is not None:
                    payload[key] = candidate[key]

        raw_contract = {
            "topic": topic,
            "clarification_history": clarification_history,
            "keywords": keywords,
            "retrieval_profile": retrieval_profile,
            "plan_intent": plan_intent or "",
            "research_objective": payload.get("research_objective"),
            "target_signal_types": payload.get("target_signal_types"),
            "must_have_signals": payload.get("must_have_signals"),
            "hard_reject_signals": payload.get("hard_reject_signals"),
        }
        version_hash = _stable_hash(raw_contract)
        normalized = {
            "spec_id": f"spec-{_slugify(topic)}-{version_hash}",
            "spec_version": f"phase8-v1-{version_hash}",
            "research_objective": str(payload.get("research_objective") or fallback["research_objective"]).strip(),
            "target_signal_types": _dedupe_keep_order(list(payload.get("target_signal_types") or fallback["target_signal_types"])),
            "target_author_types": _dedupe_keep_order(list(payload.get("target_author_types") or fallback["target_author_types"])),
            "non_target_author_types": _dedupe_keep_order(
                list(payload.get("non_target_author_types") or fallback["non_target_author_types"])
            ),
            "must_have_signals": _dedupe_keep_order(list(payload.get("must_have_signals") or fallback["must_have_signals"])),
            "nice_to_have_signals": _dedupe_keep_order(list(payload.get("nice_to_have_signals") or fallback["nice_to_have_signals"])),
            "hard_reject_signals": _dedupe_keep_order(list(payload.get("hard_reject_signals") or fallback["hard_reject_signals"])),
            "comment_policy": {
                "allow_parent_context": bool((payload.get("comment_policy") or {}).get("allow_parent_context", True)),
                "reject_transactional_only_comments": bool(
                    (payload.get("comment_policy") or {}).get(
                        "reject_transactional_only_comments",
                        (fallback.get("comment_policy") or {}).get("reject_transactional_only_comments", True),
                    )
                ),
                "minimum_comment_text_length": max(
                    0,
                    int(
                        (payload.get("comment_policy") or {}).get(
                            "minimum_comment_text_length",
                            (fallback.get("comment_policy") or {}).get("minimum_comment_text_length", 8),
                        )
                    ),
                ),
            },
            "valid_examples": _dedupe_keep_order(list(payload.get("valid_examples") or fallback["valid_examples"]))[:5],
            "invalid_examples": _dedupe_keep_order(list(payload.get("invalid_examples") or fallback["invalid_examples"]))[:5],
            "batch_policy": {
                "min_accept_ratio": max(
                    0.0,
                    min(1.0, float((payload.get("batch_policy") or {}).get("min_accept_ratio", fallback["batch_policy"]["min_accept_ratio"]))),
                ),
                "min_high_conf_accept_ratio": max(
                    0.0,
                    min(
                        1.0,
                        float(
                            (payload.get("batch_policy") or {}).get(
                                "min_high_conf_accept_ratio",
                                fallback["batch_policy"]["min_high_conf_accept_ratio"],
                            )
                        ),
                    ),
                ),
                "max_consecutive_weak_batches": max(
                    1,
                    int(
                        (payload.get("batch_policy") or {}).get(
                            "max_consecutive_weak_batches",
                            fallback["batch_policy"]["max_consecutive_weak_batches"],
                        )
                    ),
                ),
                "uncertain_reformulation_floor": max(
                    0.0,
                    min(
                        1.0,
                        float(
                            (payload.get("batch_policy") or {}).get(
                                "uncertain_reformulation_floor",
                                fallback["batch_policy"]["uncertain_reformulation_floor"],
                            )
                        ),
                    ),
                ),
            },
        }
        return ValiditySpec(**normalized).model_dump()


class ModelJudgeService:
    def __init__(self, ai_client: AIClient, settings: Settings) -> None:
        self._ai_client = ai_client
        self._settings = settings
        self._judge_prompt_path = Path(__file__).resolve().parents[1] / "skills" / "content_validity_judge.md"
        self._image_prompt_path = Path(__file__).resolve().parents[1] / "skills" / "image_understanding.md"

    def hard_filter(
        self,
        *,
        content: str,
        record_type: str,
        validity_spec: dict[str, Any] | None,
    ) -> HardFilterResult:
        cleaned_text, quality_flags = clean_payload_text(content)
        normalized = normalize_text(cleaned_text)
        if not normalized:
            return HardFilterResult(True, "REJECTED", "empty_content", "Content was empty after cleaning.", cleaned_text, quality_flags)
        if normalized in SEVERE_UI_NOISE_PATTERNS:
            return HardFilterResult(True, "REJECTED", "ui_noise_only", "Content was UI chrome only.", cleaned_text, quality_flags)
        if record_type.upper() == "COMMENT":
            comment_policy = (validity_spec or {}).get("comment_policy") or {}
            minimum_length = int(comment_policy.get("minimum_comment_text_length", 0) or 0)
            if minimum_length > 0 and len(normalized) < minimum_length:
                return HardFilterResult(True, "REJECTED", "comment_too_short", "Comment text was too short.", cleaned_text, quality_flags)
            if bool(comment_policy.get("reject_transactional_only_comments", False)) and self._is_transactional_only_comment(normalized):
                return HardFilterResult(
                    True,
                    "REJECTED",
                    "transactional_only_comment",
                    "Comment was transactional-only.",
                    cleaned_text,
                    quality_flags,
                )
        return HardFilterResult(False, "UNCERTAIN", "", "", cleaned_text, quality_flags)

    async def judge_text(
        self,
        *,
        validity_spec: dict[str, Any],
        content_id: str,
        content: str,
        record_type: str,
        source_type: str,
        source_url: str | None,
        query_text: str,
        query_family: str,
        parent_context: dict[str, Any] | None = None,
        image_summary: str = "",
        used_image_understanding: bool = False,
    ) -> JudgeResult:
        prompt = self._judge_prompt_path.read_text(encoding="utf-8")
        response = await self._ai_client.call(
            model=self._settings.content_judge_model,
            system_prompt=prompt,
            user_input=json.dumps(
                {
                    "validity_spec": validity_spec,
                    "candidate": {
                        "content_id": content_id,
                        "record_type": record_type,
                        "content": content,
                        "source_type": source_type,
                        "source_url": source_url,
                        "query_text": query_text,
                        "query_family": query_family,
                        "parent_context": parent_context or {},
                        "image_summary": image_summary,
                    },
                },
                ensure_ascii=False,
            ),
            thinking=self._settings.content_judge_thinking,
        )
        provider_meta = response.get("_provider_meta", {}) if isinstance(response, dict) else {}
        return self._normalize_judge_result(
            validity_spec=validity_spec,
            content_id=content_id,
            response=response,
            used_image_understanding=used_image_understanding,
            image_summary=image_summary,
            provider_meta=provider_meta,
        )

    def should_use_image_fallback(
        self,
        *,
        candidate: dict[str, Any],
        initial_result: JudgeResult,
        validity_spec: dict[str, Any],
    ) -> bool:
        visual_context = self._extract_image_context(candidate)
        if not visual_context:
            return False
        if initial_result.decision == "UNCERTAIN":
            return True
        if len(normalize_text(str(candidate.get("content") or ""))) < 24:
            return True
        target_signals = [normalize_text(item) for item in validity_spec.get("target_signal_types", [])]
        return any("visual" in signal or "image" in signal for signal in target_signals)

    async def build_image_summary(
        self,
        *,
        candidate: dict[str, Any],
        validity_spec: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        prompt = self._image_prompt_path.read_text(encoding="utf-8")
        image_context = self._extract_image_context(candidate)
        if not image_context:
            return "", {}
        response = await self._ai_client.call(
            model=self._settings.image_fallback_model,
            system_prompt=prompt,
            user_input=json.dumps(
                {
                    "validity_spec": validity_spec,
                    "image_context": image_context,
                    "content_hint": candidate.get("content"),
                },
                ensure_ascii=False,
            ),
            thinking=self._settings.image_fallback_thinking,
        )
        summary = str(response.get("image_summary") or "").strip()
        ocr_text = str(response.get("ocr_text") or "").strip()
        signals = response.get("signals") if isinstance(response.get("signals"), list) else []
        merged_summary = summary
        if ocr_text:
            merged_summary = f"{summary} OCR: {ocr_text}".strip()
        return merged_summary[:500], {"ocr_text": ocr_text, "signals": signals}

    def fallback_from_retrieval_score(
        self,
        *,
        validity_spec: dict[str, Any],
        content_id: str,
        score: RetrievalScore,
        reason_prefix: str,
    ) -> JudgeResult:
        confidence = 0.85 if score.status == "ACCEPTED" else 0.55 if score.status == "UNCERTAIN" else 0.9
        return JudgeResult(
            spec_id=str(validity_spec.get("spec_id") or "spec-fallback"),
            content_id=content_id,
            decision=score.status,
            relevance_score=score.score_total,
            confidence_score=confidence,
            reason_codes=[reason_prefix, score.reason],
            short_rationale=score.reason[:180],
            used_image_understanding=False,
            image_summary="",
            model_family="deterministic-fallback",
            model_version="phase7",
            policy_version=str(validity_spec.get("spec_version") or "fallback"),
            cache_key=f"{validity_spec.get('spec_id', 'spec-fallback')}:{content_id}",
            provider_used="fallback",
            fallback_used=True,
            raw_response={"score_breakdown": score.score_breakdown, "quality_flags": score.quality_flags},
        )

    def build_hard_reject_result(self, *, validity_spec: dict[str, Any], content_id: str, filter_result: HardFilterResult) -> JudgeResult:
        return JudgeResult(
            spec_id=str(validity_spec.get("spec_id") or "spec-fallback"),
            content_id=content_id,
            decision="REJECTED",
            relevance_score=0.0,
            confidence_score=0.99,
            reason_codes=[filter_result.reason_code],
            short_rationale=filter_result.rationale,
            used_image_understanding=False,
            image_summary="",
            model_family="hard-filter",
            model_version="phase8-v1",
            policy_version=str(validity_spec.get("spec_version") or "fallback"),
            cache_key=f"{validity_spec.get('spec_id', 'spec-fallback')}:{content_id}",
            provider_used="hard_filter",
            fallback_used=False,
            raw_response={"quality_flags": filter_result.quality_flags, "cleaned_text": filter_result.cleaned_text},
        )

    def _normalize_judge_result(
        self,
        *,
        validity_spec: dict[str, Any],
        content_id: str,
        response: dict[str, Any],
        used_image_understanding: bool,
        image_summary: str,
        provider_meta: dict[str, Any],
    ) -> JudgeResult:
        decision = str(response.get("decision") or "").upper().strip()
        relevance_score = self._clamp_score(response.get("relevance_score"))
        confidence_score = self._clamp_score(response.get("confidence_score"))
        if decision not in {"ACCEPTED", "REJECTED", "UNCERTAIN"}:
            if relevance_score >= 0.65:
                decision = "ACCEPTED"
            elif relevance_score <= 0.25:
                decision = "REJECTED"
            else:
                decision = "UNCERTAIN"
        reason_codes = response.get("reason_codes")
        if not isinstance(reason_codes, list) or not reason_codes:
            reason_codes = [f"decision_{decision.lower()}"]
        normalized = JudgeResult(
            spec_id=str(validity_spec.get("spec_id") or "spec-fallback"),
            content_id=content_id,
            decision=decision,
            relevance_score=relevance_score,
            confidence_score=confidence_score,
            reason_codes=[str(item).strip() for item in reason_codes if str(item).strip()],
            short_rationale=str(response.get("short_rationale") or "").strip()[:200],
            used_image_understanding=bool(response.get("used_image_understanding", used_image_understanding)),
            image_summary=str(response.get("image_summary") or image_summary).strip()[:500],
            model_family=str(response.get("model_family") or "api-judge"),
            model_version=str(response.get("model_version") or self._settings.content_judge_model),
            policy_version=str(response.get("policy_version") or validity_spec.get("spec_version") or "judge-policy-v1"),
            cache_key=str(response.get("cache_key") or f"{validity_spec.get('spec_id', 'spec-fallback')}:{content_id}"),
            provider_used=str(provider_meta.get("provider_used") or ""),
            fallback_used=bool(provider_meta.get("fallback_used", False)),
            raw_response=response,
        )
        return normalized

    def _extract_image_context(self, candidate: dict[str, Any]) -> dict[str, Any]:
        image_urls = candidate.get("image_urls") if isinstance(candidate.get("image_urls"), list) else []
        image_ocr_text = str(candidate.get("image_ocr_text") or "").strip()
        image_alt_text = str(candidate.get("image_alt_text") or "").strip()
        image_summary = str(candidate.get("image_summary") or "").strip()
        payload = {
            "image_urls": [str(item).strip() for item in image_urls if str(item).strip()][:3],
            "image_ocr_text": image_ocr_text,
            "image_alt_text": image_alt_text,
            "image_summary": image_summary,
        }
        if not payload["image_urls"] and not image_ocr_text and not image_alt_text and not image_summary:
            return {}
        return payload

    def _is_transactional_only_comment(self, normalized_content: str) -> bool:
        if not normalized_content:
            return True
        if any(pattern in normalized_content for pattern in TRANSACTIONAL_COMMENT_PATTERNS):
            tokens = normalized_content.split()
            if len(tokens) <= 8:
                return True
        return False

    def _clamp_score(self, value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return max(0.0, min(1.0, numeric))


class Phase8BatchHealthEvaluator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def evaluate(self, results: list[JudgeResult], validity_spec: dict[str, Any] | None = None) -> BatchHealthV2:
        total = max(1, len(results))
        accepted = [item for item in results if item.decision == "ACCEPTED"]
        uncertain = [item for item in results if item.decision == "UNCERTAIN"]
        rejected = [item for item in results if item.decision == "REJECTED"]
        high_conf_threshold = float(getattr(self._settings, "judge_high_confidence_threshold", 0.75) or 0.75)
        high_conf_accepts = [
            item
            for item in accepted
            if item.confidence_score >= high_conf_threshold and item.relevance_score >= item.confidence_score * 0.6
        ]
        batch_policy = (validity_spec or {}).get("batch_policy") or {}
        min_accept_ratio = float(batch_policy.get("min_accept_ratio", 0.15))
        min_high_conf_accept_ratio = float(batch_policy.get("min_high_conf_accept_ratio", 0.05))
        uncertain_floor = float(batch_policy.get("uncertain_reformulation_floor", 0.25))

        accepted_ratio = len(accepted) / total
        uncertain_ratio = len(uncertain) / total
        high_conf_accept_ratio = len(high_conf_accepts) / total
        mean_confidence = mean([item.confidence_score for item in results]) if results else 0.0

        if accepted_ratio >= min_accept_ratio or high_conf_accept_ratio >= min_high_conf_accept_ratio:
            decision = "continue"
        elif uncertain_ratio >= uncertain_floor:
            decision = "reformulate"
        else:
            decision = "weak"

        return BatchHealthV2(
            accepted_ratio=accepted_ratio,
            uncertain_ratio=uncertain_ratio,
            high_conf_accept_ratio=high_conf_accept_ratio,
            mean_confidence=mean_confidence,
            accepted_count=len(accepted),
            uncertain_count=len(uncertain),
            rejected_count=len(rejected),
            high_conf_accept_count=len(high_conf_accepts),
            decision=decision,
        )
