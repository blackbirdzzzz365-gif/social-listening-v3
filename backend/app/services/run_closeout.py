from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.models.crawled_post import CrawledPost
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.infrastructure.config import Settings
from app.infrastructure.database import SessionLocal
from app.models.run import PlanRun, StepRun
from app.models.theme_result import ThemeResult
from app.services.health_monitor import utc_now_iso
from app.services.insight import InsightService


class RunCloseoutService:
    def __init__(self, insight_service: InsightService, settings: Settings) -> None:
        self._insight_service = insight_service
        self._settings = settings
        self._prompt_path = Path(__file__).resolve().parents[1] / "skills" / "theme_classification.md"

    def get_summary(self, run_id: str) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            theme_count = (
                session.scalar(
                    select(func.count()).select_from(ThemeResult).where(ThemeResult.run_id == run_id)
                )
                or 0
            )
            return {
                "run_id": run_id,
                "answer_status": run.answer_status or "NOT_STARTED",
                "answer_generated_at": run.answer_generated_at,
                "answer_payload": self._load_json(run.answer_payload_json),
                "theme_count": int(theme_count),
            }

    async def ensure_no_answer_closeout_for_run(
        self,
        run_id: str,
        *,
        outcome_type: str,
        warning: str | None = None,
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            if run.answer_status == outcome_type and run.answer_payload_json:
                return self.get_summary(run_id)
            payload = self._build_no_answer_payload(session, run_id, outcome_type=outcome_type, warning=warning)
            run.answer_status = outcome_type
            run.answer_generated_at = utc_now_iso()
            run.answer_payload_json = json.dumps(payload, ensure_ascii=False)
            session.add(run)
            session.commit()
        return self.get_summary(run_id)

    async def ensure_closeout_for_run(
        self,
        run_id: str,
        *,
        audience_filter: str = "end_user_only",
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            if run.answer_status == "ANSWER_READY":
                return self.get_summary(run_id)
            if run.answer_status == "NO_ANSWER_CONTENT" and run.answer_payload_json:
                return self.get_summary(run_id)
            run.answer_status = "SYNTHESIZING"
            session.add(run)
            session.commit()

        try:
            prompt = self._prompt_path.read_text(encoding="utf-8")
            result = await self._insight_service.analyze_themes(run_id, prompt, audience_filter)
        except Exception as exc:
            with SessionLocal() as session:
                run = session.get(PlanRun, run_id)
                if run is not None:
                    run.answer_status = "FAILED"
                    session.add(run)
                    session.commit()
            return {
                "run_id": run_id,
                "answer_status": "FAILED",
                "answer_generated_at": None,
                "theme_count": 0,
                "error": str(exc),
            }

        themes = result.get("themes", [])
        generated_at = utc_now_iso() if themes else None
        answer_status = "ANSWER_READY" if themes else "NO_ANSWER_CONTENT"
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is not None:
                run.answer_status = answer_status
                run.answer_generated_at = generated_at
                if themes:
                    run.answer_payload_json = None
                else:
                    run.answer_payload_json = json.dumps(
                        self._build_no_answer_payload(
                            session,
                            run_id,
                            outcome_type=answer_status,
                            warning=result.get("warning"),
                        ),
                        ensure_ascii=False,
                    )
                session.add(run)
                session.commit()

        return {
            "run_id": run_id,
            "answer_status": answer_status,
            "answer_generated_at": generated_at,
            "answer_payload": None if themes else self.get_summary(run_id).get("answer_payload"),
            "theme_count": len(themes),
            "warning": result.get("warning"),
        }

    @staticmethod
    def _load_json(value: str | None, default: Any = None) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def _build_no_answer_payload(
        self,
        session: Any,
        run_id: str,
        *,
        outcome_type: str,
        warning: str | None = None,
    ) -> dict[str, Any]:
        run = session.get(PlanRun, run_id)
        if run is None:
            raise ValueError("run not found")
        plan = session.get(Plan, run.plan_id)
        context = session.get(ProductContext, plan.context_id) if plan is not None else None
        step_map = {
            step.step_id: step
            for step in session.scalars(select(PlanStep).where(PlanStep.plan_id == run.plan_id)).all()
        }
        step_runs = session.scalars(
            select(StepRun).where(StepRun.run_id == run_id).order_by(StepRun.started_at.asc(), StepRun.step_run_id.asc())
        ).all()
        posts = session.scalars(select(CrawledPost).where(CrawledPost.run_id == run_id)).all()
        theme_count = (
            session.scalar(
                select(func.count()).select_from(ThemeResult).where(ThemeResult.run_id == run_id)
            )
            or 0
        )

        decision_counter: Counter[str] = Counter()
        reason_counter: Counter[str] = Counter()
        near_miss_candidates: list[dict[str, Any]] = []
        image_record_count = 0
        for post in posts:
            decision = post.judge_decision or post.pre_ai_status or "UNKNOWN"
            decision_counter[decision] += 1
            if post.judge_used_image_understanding or post.judge_image_summary:
                image_record_count += 1
            for reason_code in self._load_json(post.judge_reason_codes_json, []):
                reason_counter[str(reason_code)] += 1
            if decision == "ACCEPTED":
                continue
            near_miss_candidates.append(
                {
                    "post_id": post.post_id,
                    "record_type": post.record_type,
                    "score": float(post.judge_relevance_score or post.pre_ai_score or 0.0),
                    "reason_codes": self._load_json(post.judge_reason_codes_json, []),
                    "content": (post.content_masked or post.content or "")[:180],
                    "source_url": post.source_url,
                }
            )
        near_miss_candidates.sort(key=lambda item: item["score"], reverse=True)

        attempted_queries: list[dict[str, Any]] = []
        cluster_counter: Counter[str] = Counter()
        search_steps_completed = 0
        search_steps_skipped = 0
        goal_aware_summary: dict[str, Any] | None = None
        for step_run in step_runs:
            step = step_map.get(step_run.step_id)
            checkpoint = self._load_json(step_run.checkpoint or step_run.checkpoint_json, {})
            if step_run.status == "SKIPPED" and checkpoint.get("skip_reason") == "goal_aware_exhaustion":
                search_steps_skipped += 1
                if goal_aware_summary is None and checkpoint.get("exhaustion_summary"):
                    goal_aware_summary = checkpoint.get("exhaustion_summary")
            if step is None or step.action_type not in {"SEARCH_POSTS", "SEARCH_IN_GROUP", "CRAWL_FEED"}:
                continue
            if step_run.status != "DONE":
                continue
            search_steps_completed += 1
            step_attempts = checkpoint.get("query_attempts") or []
            if not step_attempts:
                step_attempts = [
                    {
                        "query": step.target,
                        "collected_count": int(checkpoint.get("collected_count") or step_run.actual_count or 0),
                        "accepted_count": sum(
                            int(batch.get("accepted_count") or 0)
                            for batch in checkpoint.get("batch_summaries") or []
                        ),
                        "stop_reason": next(
                            (
                                batch.get("stop_reason")
                                for batch in checkpoint.get("batch_summaries") or []
                                if batch.get("stop_reason")
                            ),
                            None,
                        ),
                        "reason_cluster": next(
                            (
                                batch.get("reason_cluster")
                                for batch in checkpoint.get("batch_summaries") or []
                                if batch.get("reason_cluster")
                            ),
                            None,
                        ),
                        "used_reformulation": False,
                    }
                ]
            for attempt in step_attempts:
                payload = {
                    "step_id": checkpoint.get("step_id") or (step.step_id.split(":")[-1] if step else None),
                    "action_type": step.action_type,
                    "query": attempt.get("query") or step.target,
                    "collected_count": int(attempt.get("collected_count") or 0),
                    "accepted_count": int(attempt.get("accepted_count") or 0),
                    "stop_reason": attempt.get("stop_reason"),
                    "reason_cluster": attempt.get("reason_cluster"),
                    "used_reformulation": bool(attempt.get("used_reformulation")),
                }
                attempted_queries.append(payload)
                if payload["reason_cluster"]:
                    cluster_counter[str(payload["reason_cluster"])] += 1

        dominant_reject_reasons = [
            {"reason_code": reason_code, "count": count}
            for reason_code, count in reason_counter.most_common(5)
        ]
        reason_clusters = [{"cluster": cluster, "count": count} for cluster, count in cluster_counter.most_common(5)]
        payload = {
            "outcome_type": outcome_type,
            "title": self._build_no_answer_title(outcome_type),
            "summary": self._build_no_answer_summary(
                outcome_type=outcome_type,
                topic=context.topic if context is not None else None,
                total_records=len(posts),
                search_steps_completed=search_steps_completed,
                goal_aware_summary=goal_aware_summary,
            ),
            "warning": warning,
            "topic": context.topic if context is not None else None,
            "evidence_stats": {
                "total_records": len(posts),
                "accepted_count": int(decision_counter.get("ACCEPTED", 0)),
                "rejected_count": int(decision_counter.get("REJECTED", 0)),
                "uncertain_count": int(decision_counter.get("UNCERTAIN", 0)),
                "theme_count": int(theme_count),
                "search_steps_completed": search_steps_completed,
                "search_steps_skipped": search_steps_skipped,
                "image_record_count": image_record_count,
                "goal_aware_exhausted": goal_aware_summary is not None,
            },
            "dominant_reject_reasons": dominant_reject_reasons,
            "reason_clusters": reason_clusters,
            "attempted_queries": attempted_queries[:12],
            "near_miss_records": near_miss_candidates[:3],
            "recommended_next_actions": self._recommend_next_actions(
                outcome_type=outcome_type,
                dominant_cluster=reason_clusters[0]["cluster"] if reason_clusters else None,
                dominant_reason=dominant_reject_reasons[0]["reason_code"] if dominant_reject_reasons else None,
                goal_aware_exhausted=goal_aware_summary is not None,
            ),
            "termination_reason": None if goal_aware_summary is None else "GOAL_AWARE_EXHAUSTION",
            "goal_aware_exhaustion": goal_aware_summary,
        }
        return payload

    @staticmethod
    def _build_no_answer_title(outcome_type: str) -> str:
        if outcome_type == "NO_ANSWER_CONTENT":
            return "Accepted records did not converge into a final answer"
        return "Run completed without usable evidence"

    @staticmethod
    def _build_no_answer_summary(
        *,
        outcome_type: str,
        topic: str | None,
        total_records: int,
        search_steps_completed: int,
        goal_aware_summary: dict[str, Any] | None,
    ) -> str:
        topic_part = f" for '{topic}'" if topic else ""
        if outcome_type == "NO_ANSWER_CONTENT":
            return (
                f"The run found candidate evidence{topic_part}, but the accepted set still did not form a stable theme answer "
                f"after labeling and synthesis."
            )
        if goal_aware_summary is not None:
            return (
                f"No eligible evidence was found{topic_part} after {search_steps_completed} search steps and {total_records} persisted records. "
                "The run exhausted repeated weak search paths and stopped the remaining tail early."
            )
        return (
            f"No eligible evidence was found{topic_part} after {search_steps_completed} search steps and {total_records} persisted records. "
            "Labeling and theme synthesis were skipped."
        )

    @staticmethod
    def _recommend_next_actions(
        *,
        outcome_type: str,
        dominant_cluster: str | None,
        dominant_reason: str | None,
        goal_aware_exhausted: bool,
    ) -> list[str]:
        actions: list[str] = []
        if goal_aware_exhausted:
            actions.append(
                "Switch the next run to broader category, symptom, competitor, or trust/complaint language instead of repeating the same weak search path."
            )
        if dominant_cluster in {"generic_weak", "target_weak"}:
            actions.append(
                "Broaden the retrieval profile beyond exact product terms and add adjacent intent terms that match how real users describe the problem."
            )
        if dominant_cluster == "promo_noise" or dominant_reason in {"commercial_noise", "seller_cta"}:
            actions.append(
                "Deprioritize promotional groups/pages and strengthen negative or commercial filters before rerunning."
            )
        if outcome_type == "NO_ANSWER_CONTENT":
            actions.append(
                "Review whether the answer contract is too strict for the available evidence, then rerun only if the operator accepts a broader synthesis scope."
            )
        if not actions:
            actions.append("Review the validity spec and query families before rerunning this context.")
        deduped: list[str] = []
        seen: set[str] = set()
        for action in actions:
            if action in seen:
                continue
            seen.add(action)
            deduped.append(action)
        return deduped[:3]
