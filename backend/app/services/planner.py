from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select

from app.domain.action_registry import get_action_spec
from app.infra.ai_client import AIClient, ProviderExecutionError
from app.infrastructure.config import Settings
from app.infrastructure.database import SessionLocal
from app.models.approval import ApprovalGrant
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.services.research_gating import ValiditySpecBuilder
from app.services.retrieval_quality import RetrievalProfileBuilder


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "context"


def make_db_step_id(plan_id: str, public_step_id: str) -> str:
    return f"{plan_id}:{public_step_id}"


def get_public_step_id(step_id: str) -> str:
    if ":" not in step_id:
        return step_id
    return step_id.rsplit(":", 1)[-1]


@dataclass
class KeywordAnalysisResult:
    context_id: str
    topic: str
    status: str
    clarifying_questions: list[str] | None
    keywords: dict[str, list[str]] | None
    retrieval_profile: dict[str, object] | None
    validity_spec: dict[str, object] | None
    clarification_history: list[dict[str, str]]
    planning_meta: dict[str, Any] | None = None


class PlannerProviderUnavailableError(RuntimeError):
    def __init__(self, stage: str, message: str, meta: dict[str, Any]) -> None:
        super().__init__(message)
        self.stage = stage
        self.meta = meta


class PlannerService:
    def __init__(self, ai_client: AIClient, settings: Settings) -> None:
        self._ai_client = ai_client
        self._settings = settings
        self._retrieval_profile_builder = RetrievalProfileBuilder()
        self._validity_spec_builder = ValiditySpecBuilder(ai_client, settings)

    async def analyze_topic(self, topic: str, prompt: str) -> KeywordAnalysisResult:
        response, planning_meta = await self._call_planner_with_resilience(
            stage="analysis",
            model=self._settings.keyword_analysis_model,
            system_prompt=prompt,
            user_input=self._build_keyword_analysis_payload(topic, []),
            thinking=self._settings.keyword_analysis_thinking,
        )
        context_id = f"{slugify(topic)}-{uuid4().hex[:8]}"
        clarifying_questions = response.get("clarifying_questions") or None
        retrieval_profile = self._build_retrieval_profile(topic, response.get("keywords"))
        validity_spec = await self._build_validity_spec(
            topic=topic,
            clarification_history=[],
            keywords=response.get("keywords"),
            retrieval_profile=retrieval_profile,
        )
        with SessionLocal() as session:
            context = ProductContext(
                context_id=context_id,
                topic=topic,
                status=response["status"],
                keyword_json=json.dumps(response["keywords"]) if response.get("keywords") else None,
                retrieval_profile_json=json.dumps(retrieval_profile) if retrieval_profile else None,
                validity_spec_json=json.dumps(validity_spec) if validity_spec else None,
                clarifying_question_json=json.dumps(clarifying_questions) if clarifying_questions else None,
                clarification_history_json=json.dumps([]),
                planning_meta_json=json.dumps({"analysis": planning_meta}, ensure_ascii=False),
            )
            session.add(context)
            session.commit()
        return self._build_keyword_result(
            context_id=context_id,
            topic=topic,
            status=response["status"],
            clarifying_questions=clarifying_questions,
            keywords=response.get("keywords"),
            retrieval_profile=retrieval_profile,
            validity_spec=validity_spec,
            clarification_history=[],
            planning_meta={"analysis": planning_meta},
        )

    async def get_context_result(self, context_id: str, prompt: str | None = None) -> KeywordAnalysisResult:
        with SessionLocal() as session:
            context = session.get(ProductContext, context_id)
            if context is None:
                raise ValueError("context not found")
            if (
                context.status == "clarification_required"
                and not self._parse_json_list(context.clarifying_question_json)
                and prompt is not None
            ):
                history = self._parse_history(context.clarification_history_json)
                response, planning_meta = await self._call_planner_with_resilience(
                    stage="analysis_refresh",
                    model=self._settings.keyword_analysis_model,
                    system_prompt=prompt,
                    user_input=self._build_keyword_analysis_payload(context.topic, history),
                    thinking=self._settings.keyword_analysis_thinking,
                )
                clarifying_questions = response.get("clarifying_questions") or None
                retrieval_profile = self._build_retrieval_profile(context.topic, response.get("keywords"))
                validity_spec = await self._build_validity_spec(
                    topic=context.topic,
                    clarification_history=history,
                    keywords=response.get("keywords"),
                    retrieval_profile=retrieval_profile,
                )
                context.clarifying_question_json = (
                    json.dumps(clarifying_questions) if clarifying_questions else None
                )
                context.keyword_json = json.dumps(response["keywords"]) if response.get("keywords") else None
                context.retrieval_profile_json = json.dumps(retrieval_profile) if retrieval_profile else None
                context.validity_spec_json = json.dumps(validity_spec) if validity_spec else None
                context.status = response["status"]
                context.planning_meta_json = json.dumps(
                    self._merge_planning_meta(context.planning_meta_json, "analysis_refresh", planning_meta),
                    ensure_ascii=False,
                )
                session.add(context)
                session.commit()
                session.refresh(context)
            session.expunge(context)
        return self._result_from_context(context)

    async def submit_clarifications(
        self,
        context_id: str,
        answers: list[str],
        prompt: str,
    ) -> KeywordAnalysisResult:
        with SessionLocal() as session:
            context = session.get(ProductContext, context_id)
            if context is None:
                raise ValueError("context not found")
            questions = self._parse_json_list(context.clarifying_question_json)
            history = self._parse_history(context.clarification_history_json)
            if context.status != "clarification_required" or not questions:
                raise ValueError("context does not require clarification")
            topic = context.topic

        normalized_answers = [answer.strip() for answer in answers]
        if len(normalized_answers) != len(questions):
            raise ValueError("answers must match the outstanding clarification questions")
        if any(not answer for answer in normalized_answers):
            raise ValueError("clarification answers cannot be empty")

        new_turns = [
            {"question": question, "answer": answer}
            for question, answer in zip(questions, normalized_answers, strict=True)
        ]
        merged_history = history + new_turns

        response, planning_meta = await self._call_planner_with_resilience(
            stage="clarification",
            model=self._settings.keyword_analysis_model,
            system_prompt=prompt,
            user_input=self._build_keyword_analysis_payload(topic, merged_history),
            thinking=self._settings.keyword_analysis_thinking,
        )

        clarifying_questions = response.get("clarifying_questions") or None
        retrieval_profile = self._build_retrieval_profile(topic, response.get("keywords"))
        validity_spec = await self._build_validity_spec(
            topic=topic,
            clarification_history=merged_history,
            keywords=response.get("keywords"),
            retrieval_profile=retrieval_profile,
        )
        with SessionLocal() as session:
            context = session.get(ProductContext, context_id)
            if context is None:
                raise ValueError("context not found")
            context.status = response["status"]
            context.keyword_json = json.dumps(response["keywords"]) if response.get("keywords") else None
            context.retrieval_profile_json = json.dumps(retrieval_profile) if retrieval_profile else None
            context.validity_spec_json = json.dumps(validity_spec) if validity_spec else None
            context.clarifying_question_json = json.dumps(clarifying_questions) if clarifying_questions else None
            context.clarification_history_json = json.dumps(merged_history)
            context.planning_meta_json = json.dumps(
                self._merge_planning_meta(context.planning_meta_json, "clarification", planning_meta),
                ensure_ascii=False,
            )
            session.add(context)
            session.commit()
            session.refresh(context)
            session.expunge(context)
        return self._result_from_context(context)

    async def update_keywords(self, context_id: str, keywords: dict[str, list[str]]) -> KeywordAnalysisResult:
        with SessionLocal() as session:
            context = session.get(ProductContext, context_id)
            if context is None:
                raise ValueError("context not found")
            retrieval_profile = self._build_retrieval_profile(context.topic, keywords)
            validity_spec = await self._build_validity_spec(
                topic=context.topic,
                clarification_history=self._parse_history(context.clarification_history_json),
                keywords=keywords,
                retrieval_profile=retrieval_profile,
            )
            context.keyword_json = json.dumps(keywords)
            context.retrieval_profile_json = json.dumps(retrieval_profile)
            context.validity_spec_json = json.dumps(validity_spec) if validity_spec else None
            context.status = "keywords_ready"
            context.clarifying_question_json = None
            session.add(context)
            session.commit()
            session.refresh(context)
            session.expunge(context)
        return self._result_from_context(context)

    async def generate_plan(self, context_id: str, prompt: str) -> dict:
        with SessionLocal() as session:
            context = session.get(ProductContext, context_id)
            if context is None:
                raise ValueError("context not found")
            if context.status != "keywords_ready":
                raise ValueError("keywords are not ready")
            keywords = json.loads(context.keyword_json or "{}")
            retrieval_profile = json.loads(context.retrieval_profile_json or "{}")
            validity_spec = json.loads(context.validity_spec_json or "{}")

        ai_response, generation_meta = await self._call_planner_with_resilience(
            stage="plan_generation",
            model=self._settings.plan_generation_model,
            system_prompt=prompt,
            user_input=json.dumps(
                {
                    "topic": context.topic,
                    "keywords": keywords,
                    "retrieval_profile": retrieval_profile,
                    "validity_spec": validity_spec,
                }
            ),
            thinking=self._settings.plan_generation_thinking,
        )

        normalized_steps = self._normalize_plan_steps(
            ai_response,
            topic=context.topic,
            keywords=keywords,
        )
        plan_id = f"plan-{uuid4().hex[:8]}"
        with SessionLocal() as session:
            plan = Plan(
                plan_id=plan_id,
                context_id=context_id,
                version=1,
                status="ready",
                generation_meta_json=json.dumps(generation_meta, ensure_ascii=False),
            )
            session.add(plan)
            for step in normalized_steps:
                session.add(
                    PlanStep(
                        step_id=make_db_step_id(plan_id, step["step_id"]),
                        plan_id=plan_id,
                        plan_version=1,
                        step_order=step["step_order"],
                        action_type=step["action_type"],
                        read_or_write=step["read_or_write"],
                        target=step["target"],
                        estimated_count=step["estimated_count"],
                        estimated_duration_sec=step["estimated_duration_sec"],
                        risk_level=step["risk_level"],
                        dependency_step_ids=json.dumps(step["dependency_step_ids"]),
                    )
                )
            session.commit()

        return await self.get_plan(plan_id)

    async def refine_plan(self, plan_id: str, instruction: str, prompt: str) -> dict:
        plan = await self.get_plan(plan_id)
        ai_response, generation_meta = await self._call_planner_with_resilience(
            stage="plan_refinement",
            model=self._settings.plan_refinement_model,
            system_prompt=prompt,
            user_input=json.dumps(
                {
                    "instruction": instruction,
                    "steps": plan["steps"],
                }
            ),
            thinking=self._settings.plan_refinement_thinking,
        )
        normalized_steps = self._normalize_plan_steps(ai_response)
        new_version = plan["version"] + 1
        invalidated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        with SessionLocal() as session:
            db_plan = session.get(Plan, plan_id)
            if db_plan is None:
                raise ValueError("plan not found")
            db_plan.version = new_version
            db_plan.status = "ready"
            db_plan.generation_meta_json = json.dumps(generation_meta, ensure_ascii=False)
            session.execute(
                delete(PlanStep).where(
                    PlanStep.plan_id == plan_id,
                )
            )
            for step in normalized_steps:
                session.add(
                    PlanStep(
                        step_id=make_db_step_id(plan_id, step["step_id"]),
                        plan_id=plan_id,
                        plan_version=new_version,
                        step_order=step["step_order"],
                        action_type=step["action_type"],
                        read_or_write=step["read_or_write"],
                        target=step["target"],
                        estimated_count=step["estimated_count"],
                        estimated_duration_sec=step["estimated_duration_sec"],
                        risk_level=step["risk_level"],
                        dependency_step_ids=json.dumps(step["dependency_step_ids"]),
                    )
                )
            grants = session.scalars(
                select(ApprovalGrant).where(
                    ApprovalGrant.plan_id == plan_id,
                    ApprovalGrant.invalidated.is_(False),
                )
            ).all()
            for grant in grants:
                if grant.plan_version != new_version:
                    grant.invalidated = True
                    grant.invalidated_at = invalidated_at
                    grant.invalidated_reason = "plan_edited_after_approval"
                    session.add(grant)
            session.add(db_plan)
            session.commit()

        refined = await self.get_plan(plan_id)
        refined["diff_summary"] = ai_response.get("diff_summary")
        refined["warnings"] = ai_response.get("warnings", [])
        return refined

    def _normalize_plan_steps(
        self,
        ai_response: dict,
        *,
        topic: str | None = None,
        keywords: dict[str, list[str]] | None = None,
    ) -> list[dict]:
        raw_steps = ai_response.get("steps")
        if raw_steps is None and isinstance(ai_response.get("plan"), dict):
            raw_steps = ai_response["plan"].get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("plan response did not contain any steps")

        normalized_steps: list[dict] = []
        for index, raw_step in enumerate(raw_steps, start=1):
            action_type = (raw_step.get("action_type") or raw_step.get("action") or "").upper().strip()
            if not action_type:
                raise ValueError(f"plan step {index} missing action_type")
            action_spec = get_action_spec(action_type)
            if action_spec is None:
                continue

            parameters = raw_step.get("parameters") or {}
            parameter_keywords = parameters.get("keywords") or []
            target = raw_step.get("target")
            if not target:
                if action_type in ("SEARCH_GROUPS", "SEARCH_POSTS"):
                    target = parameter_keywords[0] if parameter_keywords else "research"
                else:
                    target = parameters.get("target_groups") or (
                        parameter_keywords[0] if parameter_keywords else "public-group"
                    )
            if action_type in ("SEARCH_GROUPS", "SEARCH_POSTS"):
                target = self._normalize_search_query_target(
                    raw_target=str(target),
                    parameters=parameters,
                    topic=topic,
                    keyword_map=keywords,
                )

            estimated_count = raw_step.get("estimated_count")
            if estimated_count is None:
                if action_type == "SEARCH_GROUPS":
                    estimated_count = parameters.get("max_groups") or 3
                elif action_type in {"SEARCH_POSTS", "SEARCH_IN_GROUP", "CRAWL_FEED", "CRAWL_COMMENTS"}:
                    estimated_count = parameters.get("max_posts_per_group") or 20
                else:
                    estimated_count = parameters.get("max_groups") or parameters.get("max_posts_per_group") or 10

            normalized_steps.append(
                {
                    "step_id": str(raw_step.get("step_id") or f"step-{index}").replace("_", "-").lower(),
                    "step_order": len(normalized_steps) + 1,
                    "action_type": action_spec.action_type,
                    "read_or_write": raw_step.get("read_or_write")
                    or action_spec.read_or_write,
                    "target": target,
                    "estimated_count": int(estimated_count),
                    "estimated_duration_sec": int(raw_step.get("estimated_duration_sec") or 300),
                    "risk_level": raw_step.get("risk_level") or action_spec.risk_level,
                    "dependency_step_ids": [
                        str(step_id).replace("_", "-").lower()
                        for step_id in (raw_step.get("dependency_step_ids") or [])
                    ],
                    "_original_dependency_step_ids": [
                        str(step_id).replace("_", "-").lower()
                        for step_id in (raw_step.get("dependency_step_ids") or [])
                    ],
                }
            )
        if not normalized_steps:
            raise ValueError("plan response did not contain supported actions")

        stable_steps = normalized_steps
        while True:
            valid_step_ids = {step["step_id"] for step in stable_steps}
            next_steps = [
                step
                for step in stable_steps
                if all(step_id in valid_step_ids for step_id in step["_original_dependency_step_ids"])
            ]
            if len(next_steps) == len(stable_steps):
                break
            stable_steps = next_steps

        for step_order, step in enumerate(stable_steps, start=1):
            step["step_order"] = step_order
            current_step_ids = {item["step_id"] for item in stable_steps}
            step["dependency_step_ids"] = [
                step_id for step_id in step["dependency_step_ids"] if step_id in current_step_ids
            ]
            step.pop("_original_dependency_step_ids", None)
        normalized_steps = stable_steps
        return normalized_steps

    def _normalize_search_query_target(
        self,
        *,
        raw_target: str,
        parameters: dict,
        topic: str | None,
        keyword_map: dict[str, list[str]] | None,
    ) -> str:
        keyword_group = self._extract_keyword_group(raw_target)
        candidate_sources: list[str] = []

        if keyword_group and keyword_map:
            candidate_sources.extend(keyword_map.get(keyword_group, []))
        if isinstance(parameters.get("keywords"), list):
            candidate_sources.extend(str(item) for item in parameters["keywords"] if item)
        candidate_sources.append(raw_target)
        if keyword_map:
            candidate_sources.extend(self._infer_related_keyword_candidates(raw_target, keyword_map))
        if topic:
            candidate_sources.append(topic)

        for source in candidate_sources:
            candidates = self._split_search_candidates(source)
            valid = [candidate for candidate in candidates if self._is_valid_search_query(candidate)]
            if valid:
                valid.sort(key=self._search_query_score, reverse=True)
                return valid[0]

        fallback_candidates = self._split_search_candidates(raw_target)
        fallback = fallback_candidates[0] if fallback_candidates else topic or "research"
        return self._truncate_search_query(fallback)

    def _extract_keyword_group(self, raw_target: str) -> str | None:
        if ":" not in raw_target:
            return None
        prefix = raw_target.split(":", 1)[0].strip().lower().replace(" ", "_")
        if prefix in {"brand", "pain_points", "sentiment", "behavior", "comparison"}:
            return prefix
        return None

    def _split_search_candidates(self, value: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", value).strip()
        if not normalized:
            return []

        prefix_group = self._extract_keyword_group(normalized)
        if prefix_group and ":" in normalized:
            normalized = normalized.split(":", 1)[1].strip()

        normalized = re.sub(r"\((.*?)\)", " ", normalized)
        parts = re.split(r"[,;|\n/]+", normalized)
        candidates: list[str] = []
        for part in parts:
            cleaned = re.sub(
                r"^(brand|pain[_ ]points|sentiment|behavior|comparison|keywords?)\s*:?\s*",
                "",
                part.strip(),
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
            if cleaned:
                candidates.append(cleaned)
        if not candidates:
            candidates.append(normalized)
        return self._dedupe_keep_order(candidates)

    def _is_valid_search_query(self, candidate: str) -> bool:
        lowered = candidate.lower().strip()
        if not lowered:
            return False
        if any(
            marker in lowered
            for marker in (
                "public-groups",
                "private-groups",
                "approved-private-groups",
                "join-requests",
                "from step-",
                "keyword",
                "comments from",
                "discovered from",
                "in groups from",
            )
        ):
            return False
        words = lowered.split()
        if len(words) > 5:
            return False
        if lowered in {"brand", "pain_points", "pain points", "sentiment", "behavior", "comparison"}:
            return False
        return True

    def _search_query_score(self, candidate: str) -> tuple[int, int, int]:
        words = candidate.split()
        lowered = candidate.lower()
        specificity_bonus = 1 if len(words) >= 2 else 0
        vietnamese_bonus = 1 if any(ord(char) > 127 for char in candidate) else 0
        return (
            specificity_bonus,
            min(len(words), 5),
            len(lowered),
        )

    def _truncate_search_query(self, value: str) -> str:
        words = re.sub(r"\s+", " ", value).strip().split()
        if not words:
            return "research"
        return " ".join(words[:5])

    def _infer_related_keyword_candidates(
        self,
        raw_target: str,
        keyword_map: dict[str, list[str]],
    ) -> list[str]:
        target_tokens = set(re.findall(r"\w+", raw_target.lower()))
        if not target_tokens:
            return []

        scored: list[tuple[int, str]] = []
        for keyword_list in keyword_map.values():
            for candidate in keyword_list:
                candidate_tokens = set(re.findall(r"\w+", candidate.lower()))
                overlap = len(target_tokens & candidate_tokens)
                if overlap == 0:
                    continue
                scored.append((overlap, candidate))
        scored.sort(key=lambda item: (item[0], self._search_query_score(item[1])), reverse=True)
        return self._dedupe_keep_order([candidate for _, candidate in scored[:5]])

    def _dedupe_keep_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            ordered.append(normalized)
        return ordered

    def _build_keyword_analysis_payload(
        self,
        topic: str,
        clarification_history: list[dict[str, str]],
    ) -> str:
        return json.dumps(
            {
                "topic": topic,
                "clarification_history": clarification_history,
            },
            ensure_ascii=False,
        )

    def _parse_json_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if str(item).strip()]

    def _parse_history(self, value: str | None) -> list[dict[str, str]]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []

        history: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if not question or not answer:
                continue
            history.append({"question": question, "answer": answer})
        return history

    def _build_keyword_result(
        self,
        *,
        context_id: str,
        topic: str,
        status: str,
        clarifying_questions: list[str] | None,
        keywords: dict[str, list[str]] | None,
        retrieval_profile: dict[str, object] | None,
        validity_spec: dict[str, object] | None,
        clarification_history: list[dict[str, str]],
        planning_meta: dict[str, Any] | None = None,
    ) -> KeywordAnalysisResult:
        return KeywordAnalysisResult(
            context_id=context_id,
            topic=topic,
            status=status,
            clarifying_questions=clarifying_questions,
            keywords=keywords,
            retrieval_profile=retrieval_profile,
            validity_spec=validity_spec,
            clarification_history=clarification_history,
            planning_meta=planning_meta,
        )

    def _result_from_context(self, context: ProductContext) -> KeywordAnalysisResult:
        keywords = json.loads(context.keyword_json) if context.keyword_json else None
        retrieval_profile = json.loads(context.retrieval_profile_json) if context.retrieval_profile_json else None
        validity_spec = json.loads(context.validity_spec_json) if context.validity_spec_json else None
        clarifying_questions = self._parse_json_list(context.clarifying_question_json) or None
        clarification_history = self._parse_history(context.clarification_history_json)
        planning_meta = self._parse_json_object(context.planning_meta_json)
        return self._build_keyword_result(
            context_id=context.context_id,
            topic=context.topic,
            status=context.status,
            clarifying_questions=clarifying_questions,
            keywords=keywords,
            retrieval_profile=retrieval_profile,
            validity_spec=validity_spec,
            clarification_history=clarification_history,
            planning_meta=planning_meta,
        )

    def _build_retrieval_profile(
        self,
        topic: str,
        keywords: dict[str, list[str]] | None,
    ) -> dict[str, object] | None:
        if not keywords:
            return None
        return self._retrieval_profile_builder.build(topic=topic, keyword_map=keywords)

    async def _build_validity_spec(
        self,
        *,
        topic: str,
        clarification_history: list[dict[str, str]],
        keywords: dict[str, list[str]] | None,
        retrieval_profile: dict[str, object] | None,
        plan_intent: str | None = None,
    ) -> dict[str, object] | None:
        if not keywords and not clarification_history and not topic.strip():
            return None
        return await self._validity_spec_builder.build(
            topic=topic,
            clarification_history=clarification_history,
            keywords=keywords,
            retrieval_profile=retrieval_profile,
            plan_intent=plan_intent,
        )

    async def explain_steps(self, plan: dict, prompt: str) -> dict[str, str]:
        topic = ""
        with SessionLocal() as session:
            context = session.get(ProductContext, plan.get("context_id", ""))
            if context:
                topic = context.topic or ""

        steps_for_ai = [
            {
                "step_id": s["step_id"],
                "action_type": s["action_type"],
                "target": s["target"],
                "estimated_count": s.get("estimated_count"),
                "risk_level": s.get("risk_level"),
                "dependency_step_ids": s.get("dependency_step_ids", []),
            }
            for s in plan.get("steps", [])
        ]
        response, _ = await self._call_planner_with_resilience(
            stage="step_explanation",
            model=self._settings.keyword_analysis_model,
            system_prompt=prompt,
            user_input=json.dumps({"topic": topic, "steps": steps_for_ai}, ensure_ascii=False),
        )
        return response.get("explanations", {})

    async def get_plan(self, plan_id: str) -> dict:
        with SessionLocal() as session:
            plan = session.get(Plan, plan_id)
            if plan is None:
                raise ValueError("plan not found")
            steps = session.scalars(
                select(PlanStep)
                .where(
                    PlanStep.plan_id == plan_id,
                    PlanStep.plan_version == plan.version,
                )
                .order_by(PlanStep.step_order.asc())
            ).all()
            return {
                "plan_id": plan.plan_id,
                "context_id": plan.context_id,
                "version": plan.version,
                "status": plan.status,
                "steps": [
                    {
                        "step_id": get_public_step_id(step.step_id),
                        "step_order": step.step_order,
                        "action_type": step.action_type,
                        "read_or_write": step.read_or_write,
                        "target": step.target,
                        "estimated_count": step.estimated_count,
                        "estimated_duration_sec": step.estimated_duration_sec,
                        "risk_level": step.risk_level,
                        "dependency_step_ids": json.loads(step.dependency_step_ids or "[]"),
                    }
                    for step in steps
                ],
                "estimated_total_duration_sec": sum(step.estimated_duration_sec or 0 for step in steps),
                "generation_meta": self._parse_json_object(plan.generation_meta_json),
                "warnings": [],
                "updated_at": getattr(plan, "created_at", None),
            }

    async def _call_planner_with_resilience(
        self,
        *,
        stage: str,
        model: str,
        system_prompt: str,
        user_input: str,
        thinking: bool = False,
        provider_slot: str = "default",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        max_attempts = max(1, int(self._settings.planner_retry_count) + 1)
        backoff_sec = max(0.0, float(self._settings.planner_retry_backoff_sec))
        attempt_history: list[dict[str, Any]] = []

        for attempt in range(1, max_attempts + 1):
            started_at = datetime.now().astimezone().isoformat(timespec="seconds")
            try:
                response = await self._ai_client.call(
                    model=model,
                    system_prompt=system_prompt,
                    user_input=user_input,
                    thinking=thinking,
                    provider_slot=provider_slot,
                )
                provider_meta = dict(response.get("_provider_meta") or {})
                attempt_history.append(
                    {
                        "attempt": attempt,
                        "started_at": started_at,
                        "status": "success",
                        "provider_used": provider_meta.get("provider_used"),
                        "fallback_used": bool(provider_meta.get("fallback_used", False)),
                        "failure_reason": provider_meta.get("failure_reason"),
                    }
                )
                planning_meta = {
                    "stage": stage,
                    "status": "success",
                    "attempt_count": attempt,
                    "provider_slot": provider_slot,
                    "provider_used": provider_meta.get("provider_used"),
                    "fallback_used": bool(provider_meta.get("fallback_used", False)),
                    "primary_model": provider_meta.get("primary_model", model),
                    "fallback_model": provider_meta.get("fallback_model"),
                    "failure_reason": provider_meta.get("failure_reason"),
                    "attempts": attempt_history,
                }
                return response, planning_meta
            except Exception as exc:
                classification = self._classify_planner_exception(exc)
                attempt_history.append(
                    {
                        "attempt": attempt,
                        "started_at": started_at,
                        "status": "error",
                        "retryable": classification["retryable"],
                        "provider_failure": classification["provider_failure"],
                        "error_type": exc.__class__.__name__,
                        "error_message": str(exc)[:240],
                    }
                )
                if classification["retryable"] and attempt < max_attempts:
                    if backoff_sec > 0:
                        await asyncio.sleep(backoff_sec * attempt)
                    continue
                if classification["provider_failure"]:
                    meta = {
                        "stage": stage,
                        "status": "provider_unavailable",
                        "attempt_count": attempt,
                        "provider_slot": provider_slot,
                        "provider_used": None,
                        "fallback_used": False,
                        "primary_model": model,
                        "fallback_model": getattr(self._settings, "anthropic_fallback_model", None),
                        "failure_reason": exc.__class__.__name__,
                        "attempts": attempt_history,
                    }
                    raise PlannerProviderUnavailableError(
                        stage,
                        f"planner stage '{stage}' is temporarily unavailable: {exc}",
                        meta,
                    ) from exc
                raise

        raise RuntimeError("planner resilience loop terminated unexpectedly")

    def _classify_planner_exception(self, exc: Exception) -> dict[str, bool]:
        if isinstance(exc, ProviderExecutionError):
            return {"provider_failure": True, "retryable": True}

        lowered_name = exc.__class__.__name__.lower()
        lowered_message = str(exc).lower()
        retryable_markers = (
            "overloaded",
            "timeout",
            "timed out",
            "temporarily unavailable",
            "rate limit",
            "rate-limited",
            "too many requests",
            "connection error",
            "transport",
            "service unavailable",
            " 529",
        )
        providerish_names = (
            "internalservererror",
            "apiconnectionerror",
            "apitimeouterror",
            "ratelimiterror",
            "servicenotavailableerror",
        )
        provider_failure = lowered_name in providerish_names or any(marker in lowered_message for marker in retryable_markers)
        retryable = provider_failure
        return {"provider_failure": provider_failure, "retryable": retryable}

    def _merge_planning_meta(
        self,
        existing_value: str | None,
        stage: str,
        planning_meta: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._parse_json_object(existing_value) or {}
        payload[stage] = planning_meta
        payload["latest_stage"] = stage
        return payload

    def _parse_json_object(self, value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
