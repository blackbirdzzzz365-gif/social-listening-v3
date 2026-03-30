from __future__ import annotations

import asyncio
import json
import re
import socket
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import anthropic

from app.infrastructure.config import Settings


class MarketplaceTimeoutError(TimeoutError):
    pass


class ProviderExecutionError(RuntimeError):
    pass


class ProviderTimeoutError(ProviderExecutionError):
    pass


class ProviderTransportError(ProviderExecutionError):
    pass


class ProviderRateLimitError(ProviderExecutionError):
    pass


class ProviderServerError(ProviderExecutionError):
    pass


class ProviderEnvelopeError(ProviderExecutionError):
    pass


class AIClient:
    def __init__(self, settings: Settings) -> None:
        self._marketplace_api_key = settings.openai_compatible_api_key.strip()
        self._marketplace_base_url = settings.openai_compatible_base_url.rstrip("/")
        self._marketplace_timeout_sec = max(1.0, float(settings.openai_compatible_timeout_sec))
        self._fallback_model = settings.anthropic_fallback_model
        self._anthropic_api_key = settings.anthropic_api_key.strip()
        self._retry_count = max(0, int(settings.ai_provider_retry_count))
        self._anthropic_client = (
            anthropic.AsyncAnthropic(api_key=self._anthropic_api_key) if self._anthropic_api_key else None
        )

    async def call(
        self,
        model: str,
        system_prompt: str,
        user_input: str,
        *,
        stream: bool = False,
        thinking: bool = False,
    ) -> dict[str, Any]:
        try:
            content, provider_meta = await self._request_text(
                model=model,
                system_prompt=system_prompt,
                user_input=user_input,
                thinking=thinking,
                stream=stream,
            )
        except RuntimeError:
            response = self._mock_response(system_prompt=system_prompt, user_input=user_input)
            response["_provider_meta"] = {
                "provider_used": "mock",
                "fallback_used": False,
                "primary_model": model,
                "fallback_model": self._fallback_model,
                "attempt_count": 0,
                "failure_reason": "no_provider_configured",
            }
            return response

        try:
            parsed = self._parse_json_response(content)
            parsed["_provider_meta"] = provider_meta
            return parsed
        except ValueError as parse_error:
            repaired, repair_meta = await self._repair_json_response(model=model, malformed_content=content)
            try:
                parsed = self._parse_json_response(repaired)
                repair_meta["repair_used"] = True
                parsed["_provider_meta"] = repair_meta
                return parsed
            except ValueError as repair_error:
                raise ValueError(str(repair_error)) from parse_error

    async def _request_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_input: str,
        thinking: bool,
        stream: bool,
    ) -> tuple[str, dict[str, Any]]:
        if self._marketplace_api_key:
            primary_attempts = 0
            last_error: Exception | None = None
            for primary_attempts in range(1, self._retry_count + 2):
                try:
                    text = await self._request_marketplace_text(
                        model=model,
                        system_prompt=system_prompt,
                        user_input=user_input,
                        stream=stream,
                    )
                    return text, {
                        "provider_used": "chiasegpu",
                        "fallback_used": False,
                        "primary_model": model,
                        "fallback_model": self._fallback_model,
                        "attempt_count": primary_attempts,
                        "failure_reason": None,
                    }
                except ProviderExecutionError as exc:
                    last_error = exc
                    if primary_attempts <= self._retry_count and self._should_retry(exc):
                        continue
                    break

            if last_error is not None and self._should_failover(last_error) and self._anthropic_client is not None:
                text = await self._request_anthropic_text(
                    model=self._fallback_model,
                    system_prompt=system_prompt,
                    user_input=user_input,
                    thinking=thinking,
                    stream=stream,
                )
                return text, {
                    "provider_used": "anthropic",
                    "fallback_used": True,
                    "primary_model": model,
                    "fallback_model": self._fallback_model,
                    "attempt_count": primary_attempts + 1,
                    "failure_reason": last_error.__class__.__name__,
                }
            if last_error is not None:
                raise last_error

        if self._anthropic_client is not None:
            text = await self._request_anthropic_text(
                model=self._fallback_model,
                system_prompt=system_prompt,
                user_input=user_input,
                thinking=thinking,
                stream=stream,
            )
            return text, {
                "provider_used": "anthropic",
                "fallback_used": False,
                "primary_model": model,
                "fallback_model": self._fallback_model,
                "attempt_count": 1,
                "failure_reason": None,
            }

        raise RuntimeError("No AI providers configured")

    async def _request_marketplace_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_input: str,
        stream: bool,
    ) -> str:
        if stream:
            raise ValueError("Streaming is not supported for marketplace requests")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            "stream": False,
        }
        raw_response = await asyncio.to_thread(self._post_marketplace_completion, payload)
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ProviderEnvelopeError("Marketplace response was not valid JSON") from exc
        choices = parsed.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderEnvelopeError("Marketplace response did not include choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ProviderEnvelopeError("Marketplace response did not include a message")
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text") or ""))
            if parts:
                return "\n".join(parts)
        raise ProviderEnvelopeError("Marketplace response did not include text content")

    def _post_marketplace_completion(self, payload: dict[str, Any]) -> str:
        request = urllib_request.Request(
            url=f"{self._marketplace_base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._marketplace_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=self._marketplace_timeout_sec) as response:
                return response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            if exc.code == 429:
                raise ProviderRateLimitError("Marketplace rate limited") from exc
            if exc.code >= 500:
                raise ProviderServerError(f"Marketplace server error: {exc.code}") from exc
            raise
        except urllib_error.URLError as exc:
            if self._is_timeout_error(exc.reason):
                raise ProviderTimeoutError("Marketplace request timed out") from exc
            raise ProviderTransportError("Marketplace transport failure") from exc
        except socket.timeout as exc:
            raise ProviderTimeoutError("Marketplace request timed out") from exc
        except TimeoutError as exc:
            raise ProviderTimeoutError("Marketplace request timed out") from exc

    def _is_timeout_error(self, error: object) -> bool:
        if isinstance(error, (TimeoutError, socket.timeout)):
            return True
        if isinstance(error, str):
            return "timed out" in error.lower()
        return False

    async def _request_anthropic_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_input: str,
        thinking: bool,
        stream: bool,
    ) -> str:
        assert self._anthropic_client is not None
        message = await self._anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_input}],
            thinking={
                "type": "enabled",
                "budget_tokens": 2048,
            }
            if thinking
            else anthropic.NOT_GIVEN,
            stream=stream,
        )
        text_blocks = [block.text for block in message.content if getattr(block, "type", "") == "text"]
        return "\n".join(text_blocks)

    async def _repair_json_response(self, *, model: str, malformed_content: str) -> tuple[str, dict[str, Any]]:
        repair_prompt = (
            "JSON_REPAIR\n"
            "You convert malformed JSON-like output into one strict JSON object.\n"
            "Rules:\n"
            "- Return valid JSON only.\n"
            "- No markdown fences.\n"
            "- Preserve the original meaning and keys when possible.\n"
            "- If a value is ambiguous, keep the closest safe interpretation.\n"
        )
        return await self._request_text(
            model=model,
            system_prompt=repair_prompt,
            user_input=malformed_content,
            thinking=False,
            stream=False,
        )

    def _should_retry(self, exc: Exception) -> bool:
        return isinstance(exc, (ProviderTimeoutError, ProviderTransportError, ProviderRateLimitError, ProviderServerError, ProviderEnvelopeError))

    def _should_failover(self, exc: Exception) -> bool:
        return self._should_retry(exc)

    def _mock_response(self, *, system_prompt: str, user_input: str) -> dict[str, Any]:
        if "KEYWORD_ANALYSIS" in system_prompt:
            return self._mock_keyword_response(user_input)
        if "PLAN_GENERATION" in system_prompt:
            payload = json.loads(user_input)
            return self._mock_plan_response(payload)
        if "PLAN_REFINEMENT" in system_prompt:
            payload = json.loads(user_input)
            return self._mock_plan_refinement(payload)
        if "CONTENT_LABELING" in system_prompt:
            payload = json.loads(user_input)
            return self._mock_content_labeling(payload)
        if "THEME_CLASSIFICATION" in system_prompt:
            payload = json.loads(user_input)
            return self._mock_theme_classification(payload)
        if "STEP_EXPLAIN" in system_prompt:
            payload = json.loads(user_input)
            return self._mock_step_explain(payload)
        return {}

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        normalized = content.strip()
        if not normalized:
            raise ValueError("Empty AI response")

        fenced_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", normalized, flags=re.DOTALL)
        if fenced_match:
            normalized = fenced_match.group(1).strip()

        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = normalized.find("{")
        end = normalized.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = normalized[start : end + 1]
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("AI response was not valid JSON")

    def _mock_keyword_response(self, user_input: str) -> dict[str, Any]:
        topic = user_input
        clarification_history: list[dict[str, str]] = []
        try:
            payload = json.loads(user_input)
        except json.JSONDecodeError:
            payload = None

        if isinstance(payload, dict):
            topic = str(payload.get("topic", "")).strip()
            history_payload = payload.get("clarification_history") or []
            if isinstance(history_payload, list):
                clarification_history = [
                    {
                        "question": str(item.get("question", "")).strip(),
                        "answer": str(item.get("answer", "")).strip(),
                    }
                    for item in history_payload
                    if isinstance(item, dict)
                ]

        normalized = self._normalize_text(topic)
        normalized_answers = " ".join(
            self._normalize_text(item.get("answer", "")) for item in clarification_history if item.get("answer")
        )
        if normalized in {"ban hang", "bán hàng", "marketing", "nghien cuu"} and not clarification_history:
            return {
                "status": "clarification_required",
                "clarifying_questions": [
                    "Ban dang nghien cuu san pham hay nganh hang cu the nao?",
                    "Doi tuong khach hang muc tieu cua ban la ai?",
                ],
                "keywords": None,
            }
        if clarification_history and any(
            marker in normalized_answers
            for marker in (
                "khach hang",
                "nguoi dung",
                "me bim",
                "tre em",
                "so sinh",
                "lam dep",
                "thien nhien",
                "my pham",
                "san pham",
                "tai viet nam",
                "viet nam",
            )
        ):
            topic = f"{topic} {' '.join(item['answer'] for item in clarification_history if item.get('answer'))}".strip()
        elif clarification_history:
            return {
                "status": "clarification_required",
                "clarifying_questions": [
                    "Ban co the mo ta ro hon khach hang muc tieu cu the la ai?",
                    "Ban muon tap trung vao san pham, tinh huong su dung, hay van de nao?",
                ],
                "keywords": None,
            }

        keywords = self._build_keyword_map(topic)
        return {
            "status": "keywords_ready",
            "clarifying_questions": None,
            "keywords": keywords,
        }

    def _build_keyword_map(self, topic: str) -> dict[str, list[str]]:
        normalized = self._normalize_text(topic)
        ascii_topic = self._strip_diacritics(topic)
        brand = []
        if "tpbank evo" in normalized:
            brand = ["TPBank EVO", "tpbank evo", "TPBank", "EVO"]
        elif "skincare" in normalized or "cerave" in normalized:
            brand = ["skincare", "skin care", "CeraVe", "La Roche-Posay"]
        else:
            main = topic.strip().title()
            brand = [main, ascii_topic.lower(), "thuong hieu", "thương hiệu"]

        pain_points = ["phi cao", "phí cao", "dich vu cham", "dịch vụ chậm", "da nhon", "da nhờn"]
        sentiment = ["hai long", "hài lòng", "khong hai long", "không hài lòng", "thich", "thích"]
        behavior = ["ib minh nhe", "ib mình nhé", "ship khong", "ship không", "con hang khong", "còn hàng không"]
        comparison = ["so sanh", "so sánh", "vs", "tot hon", "tốt hơn"]
        return {
            "brand": brand,
            "pain_points": pain_points,
            "sentiment": sentiment,
            "behavior": behavior,
            "comparison": comparison,
        }

    def _mock_plan_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        topic = payload.get("topic", "")
        keywords = payload.get("keywords", {})
        brand_kw = (keywords.get("brand") or [topic or "research"])[0]
        pain_kw = (keywords.get("pain_points") or ["phí cao"])[0]
        steps = [
            {
                "step_id": "step-1",
                "action_type": "SEARCH_POSTS",
                "read_or_write": "READ",
                "target": brand_kw,
                "estimated_count": 10,
                "estimated_duration_sec": 300,
                "risk_level": "LOW",
                "dependency_step_ids": [],
            },
            {
                "step_id": "step-2",
                "action_type": "CRAWL_COMMENTS",
                "read_or_write": "READ",
                "target": "comments from posts in step-1",
                "estimated_count": 20,
                "estimated_duration_sec": 400,
                "risk_level": "LOW",
                "dependency_step_ids": ["step-1"],
            },
            {
                "step_id": "step-3",
                "action_type": "JOIN_GROUP",
                "read_or_write": "WRITE",
                "target": "private-groups discovered from step-1",
                "estimated_count": 3,
                "estimated_duration_sec": 90,
                "risk_level": "HIGH",
                "dependency_step_ids": ["step-1"],
            },
            {
                "step_id": "step-4",
                "action_type": "CHECK_JOIN_STATUS",
                "read_or_write": "READ",
                "target": "join-requests from step-3",
                "estimated_count": 3,
                "estimated_duration_sec": 120,
                "risk_level": "LOW",
                "dependency_step_ids": ["step-3"],
            },
            {
                "step_id": "step-5",
                "action_type": "SEARCH_IN_GROUP",
                "read_or_write": "READ",
                "target": f"keyword:{brand_kw} in groups from step-1",
                "estimated_count": 10,
                "estimated_duration_sec": 400,
                "risk_level": "LOW",
                "dependency_step_ids": ["step-1", "step-4"],
            },
            {
                "step_id": "step-6",
                "action_type": "SEARCH_POSTS",
                "read_or_write": "READ",
                "target": pain_kw,
                "estimated_count": 10,
                "estimated_duration_sec": 300,
                "risk_level": "LOW",
                "dependency_step_ids": [],
            },
            {
                "step_id": "step-7",
                "action_type": "CRAWL_COMMENTS",
                "read_or_write": "READ",
                "target": "comments from posts in step-6",
                "estimated_count": 20,
                "estimated_duration_sec": 400,
                "risk_level": "LOW",
                "dependency_step_ids": ["step-6"],
            },
            {
                "step_id": "step-8",
                "action_type": "JOIN_GROUP",
                "read_or_write": "WRITE",
                "target": "private-groups discovered from step-6",
                "estimated_count": 3,
                "estimated_duration_sec": 90,
                "risk_level": "HIGH",
                "dependency_step_ids": ["step-6"],
            },
            {
                "step_id": "step-9",
                "action_type": "CHECK_JOIN_STATUS",
                "read_or_write": "READ",
                "target": "join-requests from step-8",
                "estimated_count": 3,
                "estimated_duration_sec": 120,
                "risk_level": "LOW",
                "dependency_step_ids": ["step-8"],
            },
            {
                "step_id": "step-10",
                "action_type": "SEARCH_IN_GROUP",
                "read_or_write": "READ",
                "target": f"keyword:{pain_kw} in groups from step-6",
                "estimated_count": 10,
                "estimated_duration_sec": 400,
                "risk_level": "LOW",
                "dependency_step_ids": ["step-6", "step-9"],
            },
        ]
        return {
            "steps": steps,
            "warnings": [
                "JOIN_GROUP is a WRITE action — private groups require moderator approval.",
                "SEARCH_IN_GROUP requires group access. Unapproved private groups will be skipped.",
            ],
            "estimated_total_duration_sec": sum(step["estimated_duration_sec"] for step in steps),
            "diff_summary": None,
        }

    def _mock_plan_refinement(self, payload: dict[str, Any]) -> dict[str, Any]:
        steps = payload.get("steps", [])
        instruction = self._normalize_text(payload.get("instruction", ""))
        updated = [dict(step) for step in steps]
        warnings: list[str] = []

        if "chi crawl 2 group" in instruction or "2 groups" in instruction:
            updated = updated[:2]
            for idx, step in enumerate(updated, start=1):
                step["step_order"] = idx
            warnings.append("Plan reduced to the first 2 steps as requested.")
        elif "bo step cuoi" in instruction:
            updated = updated[:-1]
            for idx, step in enumerate(updated, start=1):
                step["step_order"] = idx
            warnings.append("The last step was removed.")

        return {
            "steps": updated,
            "warnings": warnings,
            "estimated_total_duration_sec": sum(step["estimated_duration_sec"] for step in updated),
            "diff_summary": warnings[0] if warnings else "Plan refined.",
        }

    def _mock_step_explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        topic = payload.get("topic", "")
        steps = payload.get("steps", [])
        templates: dict[str, str] = {
            "SEARCH_POSTS": "Tim kiem bai viet gan day ve '{target}' tren Facebook.",
            "CRAWL_COMMENTS": "Thu thap binh luan tu cac bai viet da tim duoc o buoc truoc.",
            "JOIN_GROUP": "Gui yeu cau tham gia cac nhom rieng tu da phat hien. Can duoc phe duyet.",
            "CHECK_JOIN_STATUS": "Kiem tra xem cac nhom rieng tu da chap nhan yeu cau tham gia chua.",
            "SEARCH_IN_GROUP": "Tim kiem sau hon trong cac nhom da tham gia voi tu khoa lien quan.",
            "SEARCH_GROUPS": "Tim kiem nhom Facebook lien quan den '{target}'.",
            "CRAWL_FEED": "Doc cac bai viet tu nhom da tham gia.",
        }
        explanations: dict[str, str] = {}
        for step in steps:
            action = step.get("action_type", "")
            target = step.get("target", "")
            template = templates.get(action, f"Thuc hien {action} voi muc tieu: {target}")
            explanations[step["step_id"]] = template.format(target=target, topic=topic)
        return {"explanations": explanations}

    def _mock_content_labeling(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = payload.get("records") or []
        results = []
        for record in records:
            text = json.dumps(record, ensure_ascii=False).lower()
            if any(marker in text for marker in ("ib", "zalo", "đăng ký", "dang ky", "mở thẻ", "mo the")):
                author_role = "seller_affiliate"
                content_intent = "promotion"
                commerciality_level = "high"
                relevance = "low"
                reason = "promotion_markers_detected"
            elif any(marker in text for marker in ("official", "cskh", "fanpage", "thông báo", "thong bao")):
                author_role = "brand_official"
                content_intent = "support_answer"
                commerciality_level = "medium"
                relevance = "low"
                reason = "official_markers_detected"
            elif any(marker in text for marker in ("cho em hỏi", "cho em hoi", "co ai", "có ai", "trải nghiệm", "trai nghiem", "mình", "minh")):
                author_role = "end_user"
                content_intent = "question" if "?" in text or "hỏi" in text or "hoi" in text else "experience"
                commerciality_level = "low"
                relevance = "high"
                reason = "end_user_markers_detected"
            else:
                author_role = "unknown"
                content_intent = "other"
                commerciality_level = "medium"
                relevance = "low"
                reason = "insufficient_context"
            results.append(
                {
                    "post_id": record["post_id"],
                    "author_role": author_role,
                    "content_intent": content_intent,
                    "commerciality_level": commerciality_level,
                    "user_feedback_relevance": relevance,
                    "label_confidence": 0.78 if author_role != "unknown" else 0.45,
                    "label_reason": reason,
                    "label_source": "ai",
                    "model_name": "mock",
                    "model_version": "mock-v1",
                    "taxonomy_version": payload.get("taxonomy_version", "v1"),
                }
            )
        return {"records": results}

    def _mock_theme_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        posts = payload.get("posts", [])
        grouped: dict[str, dict[str, Any]] = {}

        for post in posts:
            text = post if isinstance(post, str) else post.get("content", "")
            lowered = self._normalize_text(text)
            label = "other"
            sentiment = "neutral"

            if "so voi" in lowered or "tot hon" in lowered or "hơn" in lowered:
                label = "comparison"
                sentiment = "neutral"
            elif "?" in text or "co ai" in lowered or lowered.startswith("hoi") or "khong" in lowered:
                label = "question"
                sentiment = "neutral"
            elif any(token in lowered for token in ["phi", "cham", "cao qua", "khong on", "lỗi", "loi"]):
                label = "pain_point"
                sentiment = "negative"
            elif any(token in lowered for token in ["thich", "tot", "on", "nhanh", "hai long"]):
                label = "positive_feedback"
                sentiment = "positive"

            bucket = grouped.setdefault(
                label,
                {
                    "label": label,
                    "dominant_sentiment": sentiment,
                    "post_count": 0,
                    "sample_quotes": [],
                },
            )
            bucket["post_count"] += 1
            if len(bucket["sample_quotes"]) < 3:
                bucket["sample_quotes"].append(text[:200])
            if bucket["dominant_sentiment"] != sentiment and bucket["dominant_sentiment"] != "negative":
                bucket["dominant_sentiment"] = sentiment

        themes = [
            {
                "label": item["label"],
                "dominant_sentiment": item["dominant_sentiment"],
                "post_count": item["post_count"],
                "sample_quotes": item["sample_quotes"],
            }
            for item in grouped.values()
        ]
        themes.sort(key=lambda item: item["post_count"], reverse=True)
        return {"themes": themes}

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    def _strip_diacritics(self, value: str) -> str:
        replacements = str.maketrans(
            {
                "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
                "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
                "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
                "đ": "d",
                "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
                "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
                "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
                "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
                "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
                "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
                "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
                "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
                "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
                "À": "A", "Á": "A", "Ả": "A", "Ã": "A", "Ạ": "A",
                "Ă": "A", "Ắ": "A", "Ằ": "A", "Ẳ": "A", "Ẵ": "A", "Ặ": "A",
                "Â": "A", "Ấ": "A", "Ầ": "A", "Ẩ": "A", "Ẫ": "A", "Ậ": "A",
                "Đ": "D",
                "È": "E", "É": "E", "Ẻ": "E", "Ẽ": "E", "Ẹ": "E",
                "Ê": "E", "Ế": "E", "Ề": "E", "Ể": "E", "Ễ": "E", "Ệ": "E",
                "Ì": "I", "Í": "I", "Ỉ": "I", "Ĩ": "I", "Ị": "I",
                "Ò": "O", "Ó": "O", "Ỏ": "O", "Õ": "O", "Ọ": "O",
                "Ô": "O", "Ố": "O", "Ồ": "O", "Ổ": "O", "Ỗ": "O", "Ộ": "O",
                "Ơ": "O", "Ớ": "O", "Ờ": "O", "Ở": "O", "Ỡ": "O", "Ợ": "O",
                "Ù": "U", "Ú": "U", "Ủ": "U", "Ũ": "U", "Ụ": "U",
                "Ư": "U", "Ứ": "U", "Ừ": "U", "Ử": "U", "Ữ": "U", "Ự": "U",
                "Ỳ": "Y", "Ý": "Y", "Ỷ": "Y", "Ỹ": "Y", "Ỵ": "Y",
            }
        )
        return value.translate(replacements)
