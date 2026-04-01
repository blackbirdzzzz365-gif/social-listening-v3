from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from uuid import uuid4

from sqlalchemy import func, select

from app.domain.action_registry import get_action_spec
from app.infra.ai_client import AIClient
from app.infra.browser_agent import BrowserAgent, BrowserStartupError, RawPost
from app.infrastructure.database import SessionLocal
from app.models.approval import ApprovalGrant
from app.models.crawled_post import CrawledPost
from app.models.plan import Plan, PlanStep
from app.models.product_context import ProductContext
from app.models.run import PlanRun, StepRun
from app.services.browser_run_admission import (
    BrowserRunAdmissionCancelled,
    BrowserRunAdmissionPaused,
    BrowserRunAdmissionService,
)
from app.services.health_monitor import HealthMonitorService, utc_now_iso
from app.services.label_job_service import LabelJobService, NO_ELIGIBLE_RECORDS_STATUS
from app.services.planner import get_public_step_id
from app.services.research_gating import ModelJudgeService, Phase8BatchHealthEvaluator
from app.services.retrieval_quality import DeterministicRelevanceEngine, RetrievalProfileBuilder


@dataclass
class RunControl:
    pause_requested: bool = False
    stop_requested: bool = False
    resume_event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self.resume_event.set()


class RunCancellationRequested(RuntimeError):
    pass


class StepActionTimeout(RuntimeError):
    def __init__(self, action_type: str, timeout_sec: float) -> None:
        super().__init__(f"{action_type} exceeded {timeout_sec:.0f}s timeout")
        self.action_type = action_type
        self.timeout_sec = timeout_sec


class RunnerService:
    def __init__(
        self,
        browser_agent: BrowserAgent,
        health_monitor: HealthMonitorService,
        ai_client: AIClient,
        label_job_service: LabelJobService | None = None,
        browser_admission_service: BrowserRunAdmissionService | None = None,
        settings: Any | None = None,
    ) -> None:
        self._browser_agent = browser_agent
        self._health_monitor = health_monitor
        self._label_job_service = label_job_service
        self._settings = settings
        self._browser_admission = browser_admission_service or BrowserRunAdmissionService()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._controls: dict[str, RunControl] = {}
        self._run_requires_browser: dict[str, bool] = {}
        self._subscribers: dict[str, list[asyncio.Queue[tuple[str, dict[str, Any]]]]] = {}
        self._history: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self._retrieval_profile_builder = RetrievalProfileBuilder()
        self._relevance_engine = DeterministicRelevanceEngine()
        self._model_judge = ModelJudgeService(ai_client, settings)
        self._batch_evaluator = Phase8BatchHealthEvaluator(settings)
        self._active_step_tasks: dict[str, asyncio.Task[Any]] = {}

    async def start_run(self, plan_id: str, grant_id: str) -> dict[str, Any]:
        run_id = f"run-{uuid4().hex[:10]}"
        started_at = utc_now_iso()
        with SessionLocal() as session:
            grant = session.get(ApprovalGrant, grant_id)
            plan = session.get(Plan, plan_id)
            if grant is None or plan is None:
                raise ValueError("plan or grant not found")
            if grant.plan_id != plan_id:
                raise ValueError("grant does not belong to plan")
            if grant.invalidated:
                raise ValueError("grant is invalidated")
            if grant.plan_version != plan.version:
                raise ValueError("grant version mismatch")

            approved_step_ids = json.loads(grant.approved_step_ids or "[]")
            db_steps = session.scalars(
                select(PlanStep)
                .where(
                    PlanStep.plan_id == plan_id,
                    PlanStep.plan_version == plan.version,
                )
                .order_by(PlanStep.step_order.asc())
            ).all()
            selected_steps = [step for step in db_steps if get_public_step_id(step.step_id) in approved_step_ids]
            if not selected_steps:
                raise ValueError("no approved steps found")
            requires_browser = any(self._step_requires_browser(step) for step in selected_steps)
            initial_status = "RUNNING"
            if requires_browser:
                initial_status = await self._browser_admission.register(run_id)

            run = PlanRun(
                run_id=run_id,
                plan_id=plan_id,
                plan_version=plan.version,
                grant_id=grant_id,
                status=initial_status,
                completion_reason=None,
                failure_class=None,
                answer_status=None,
                answer_generated_at=None,
                started_at=started_at,
                total_records=0,
            )
            session.add(run)
            for step in selected_steps:
                pending_checkpoint = json.dumps({"phase": "pending", "step_id": get_public_step_id(step.step_id)})
                session.add(
                    StepRun(
                        step_run_id=f"step-run-{uuid4().hex[:10]}",
                        run_id=run_id,
                        step_id=step.step_id,
                        status="PENDING",
                        checkpoint=pending_checkpoint,
                        checkpoint_json=pending_checkpoint,
                    )
                )
            session.commit()

        self._controls[run_id] = RunControl()
        self._run_requires_browser[run_id] = requires_browser
        await self._emit(
            run_id,
            "run_queued" if initial_status == "QUEUED" else "run_started",
            {"run_id": run_id, "plan_id": plan_id, "status": initial_status},
        )
        self._tasks[run_id] = asyncio.create_task(self._execute_run(run_id))
        return self.get_run(run_id)

    async def pause_run(self, run_id: str) -> dict[str, Any]:
        control = self._controls.get(run_id)
        if control is None:
            raise ValueError("run not found")
        control.pause_requested = True
        control.resume_event.clear()
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            if run.status not in {"DONE", "FAILED", "CANCELLED", "CANCELLING"}:
                run.status = "PAUSED"
                run.completion_reason = None
                session.add(run)
                session.commit()
        await self._browser_admission.notify()
        await self._emit(run_id, "run_paused", {"run_id": run_id})
        return self.get_run(run_id)

    async def resume_run(self, run_id: str) -> dict[str, Any]:
        control = self._controls.get(run_id)
        if control is None:
            raise ValueError("run not found")
        control.pause_requested = False
        control.resume_event.set()
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            if run.status not in {"DONE", "FAILED", "CANCELLED", "CANCELLING"}:
                snapshot = await self._browser_admission.snapshot()
                run.status = "RUNNING" if snapshot.owner_run_id == run_id else "QUEUED"
                run.completion_reason = None
                session.add(run)
                session.commit()
        await self._browser_admission.notify()
        await self._emit(run_id, "run_resumed", {"run_id": run_id})
        return self.get_run(run_id)

    async def stop_run(self, run_id: str) -> dict[str, Any]:
        control = self._controls.get(run_id)
        if control is None:
            raise ValueError("run not found")
        control.stop_requested = True
        control.resume_event.set()
        running_step_run_ids: list[str] = []
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            if run.status not in {"DONE", "FAILED", "CANCELLED"}:
                run.status = "CANCELLING"
                run.completion_reason = None
                run.ended_at = None
                session.add(run)
                running_step_run_ids = [
                    step_run_id
                    for step_run_id in session.scalars(
                        select(StepRun.step_run_id).where(
                            StepRun.run_id == run_id,
                            StepRun.status == "RUNNING",
                        )
                    ).all()
                ]
                session.commit()
        for step_run_id in running_step_run_ids:
            task = self._active_step_tasks.get(step_run_id)
            if task is not None and not task.done():
                task.cancel()
        await self._browser_admission.cancel(run_id)
        await self._browser_admission.notify()
        await self._emit(run_id, "run_cancelling", {"run_id": run_id, "status": "CANCELLING"})
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            step_runs = session.scalars(
                select(StepRun)
                .where(StepRun.run_id == run_id)
            ).all()
            step_map = {
                step.step_id: step
                for step in session.scalars(select(PlanStep).where(PlanStep.plan_id == run.plan_id)).all()
            }
            steps = []
            for step_run in step_runs:
                step = step_map.get(step_run.step_id)
                checkpoint_value = step_run.checkpoint or step_run.checkpoint_json
                steps.append(
                    {
                        "step_run_id": step_run.step_run_id,
                        "step_id": get_public_step_id(step_run.step_id),
                        "action_type": step.action_type if step else "UNKNOWN",
                        "status": step_run.status,
                        "started_at": step_run.started_at,
                        "ended_at": step_run.ended_at,
                        "read_or_write": step.read_or_write if step else "READ",
                        "target": step.target if step else "",
                        "actual_count": step_run.actual_count,
                        "error_message": step_run.error_message,
                        "checkpoint": json.loads(checkpoint_value) if checkpoint_value else None,
                    }
                )
            steps.sort(key=lambda item: (item["checkpoint"] or {}).get("step_id", item["step_id"]))
            return {
                "run_id": run.run_id,
                "plan_id": run.plan_id,
                "grant_id": run.grant_id,
                "plan_version": run.plan_version,
                "status": run.status,
                "completion_reason": run.completion_reason,
                "failure_class": run.failure_class,
                "answer_status": run.answer_status,
                "answer_generated_at": run.answer_generated_at,
                "started_at": run.started_at,
                "ended_at": run.ended_at,
                "total_records": run.total_records,
                "steps": steps,
            }

    def get_event_history(self, run_id: str) -> list[tuple[str, dict[str, Any]]]:
        return list(self._history.get(run_id, []))

    def subscribe(self, run_id: str) -> asyncio.Queue[tuple[str, dict[str, Any]]]:
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[tuple[str, dict[str, Any]]]) -> None:
        subscribers = self._subscribers.get(run_id, [])
        if queue in subscribers:
            subscribers.remove(queue)

    async def _execute_run(self, run_id: str) -> None:
        control = self._controls[run_id]
        current_step_run_id: str | None = None
        browser_slot_acquired = False
        try:
            if self._run_requires_browser.get(run_id, True):
                browser_slot_acquired = await self._await_browser_slot(run_id, control)
                if not browser_slot_acquired:
                    if control.stop_requested:
                        await self._finalize_cancelled_run(run_id, current_step_run_id)
                    return
            while True:
                await control.resume_event.wait()
                if control.stop_requested:
                    await self._finalize_cancelled_run(run_id, current_step_run_id)
                    return

                step_data = self._load_next_step(run_id)
                if step_data is None:
                    break

                step_run, step = step_data
                current_step_run_id = step_run.step_run_id
                await self._mark_step_running(run_id, step_run, step)
                result = await self._execute_step(run_id, step_run, step)
                await self._mark_step_done(run_id, step_run.step_run_id, result)
                current_step_run_id = None

                if control.stop_requested:
                    await self._finalize_cancelled_run(run_id, current_step_run_id)
                    return
                if control.pause_requested:
                    await control.resume_event.wait()

            completion_reason = "COMPLETED"
            emitted_status = "DONE"
            label_summary: dict[str, Any] | None = None
            closeout_summary: dict[str, Any] | None = None
            if self._label_job_service is not None:
                label_summary = await self._label_job_service.ensure_job_for_run(run_id, auto_start=True)
                if label_summary.get("status") == NO_ELIGIBLE_RECORDS_STATUS:
                    completion_reason = "NO_ELIGIBLE_RECORDS"
                    emitted_status = "DONE_NO_ELIGIBLE_RECORDS"
                else:
                    terminal = await self._label_job_service.wait_for_run(run_id)
                    label_summary = terminal.get("label_summary")
                    closeout_summary = terminal.get("closeout_summary")
                    answer_status = (closeout_summary or {}).get("answer_status")
                    if answer_status == "ANSWER_READY":
                        completion_reason = "ANSWER_READY"
                        emitted_status = "DONE_ANSWER_READY"
                    elif answer_status == "NO_ANSWER_CONTENT":
                        completion_reason = "LABELS_READY_NO_ANSWER"
                        emitted_status = "DONE_NO_ANSWER_CONTENT"
                    elif answer_status == "FAILED":
                        completion_reason = "ANSWER_CLOSEOUT_FAILED"
                        emitted_status = "DONE_CLOSEOUT_FAILED"

            with SessionLocal() as session:
                run = session.get(PlanRun, run_id)
                if run is not None and run.status != "CANCELLED":
                    run.status = "DONE"
                    run.completion_reason = completion_reason
                    run.failure_class = None
                    if completion_reason == "NO_ELIGIBLE_RECORDS":
                        run.answer_status = NO_ELIGIBLE_RECORDS_STATUS
                    run.ended_at = utc_now_iso()
                    session.add(run)
                    session.commit()
            await self._emit(
                run_id,
                "run_done",
                {
                    "run_id": run_id,
                    "status": emitted_status,
                    "completion_reason": completion_reason,
                    "label_status": None if label_summary is None else label_summary.get("status"),
                    "answer_status": None if closeout_summary is None else closeout_summary.get("answer_status"),
                },
            )
        except RunCancellationRequested:
            await self._finalize_cancelled_run(run_id, current_step_run_id)
        except Exception as exc:
            completion_reason, failure_class = self._classify_failure(exc, current_step_run_id)
            with SessionLocal() as session:
                run = session.get(PlanRun, run_id)
                if run is not None:
                    run.status = "FAILED"
                    run.completion_reason = completion_reason
                    run.failure_class = failure_class
                    run.ended_at = utc_now_iso()
                    session.add(run)
                    if current_step_run_id:
                        step_run = session.get(StepRun, current_step_run_id)
                        if step_run is not None:
                            step_run.status = "FAILED"
                            step_run.error_message = str(exc)
                            step_run.ended_at = utc_now_iso()
                            session.add(step_run)
                    session.commit()
            if current_step_run_id:
                await self._emit(
                    run_id,
                    "step_failed",
                    {
                        "run_id": run_id,
                        "error": str(exc),
                        "step_run_id": current_step_run_id,
                        "failure_class": failure_class,
                    },
                )
            await self._emit(
                run_id,
                "run_failed",
                {
                    "run_id": run_id,
                    "error": str(exc),
                    "completion_reason": completion_reason,
                    "failure_class": failure_class,
                    "failure_stage": "step" if current_step_run_id else "post_run",
                },
            )
        finally:
            if browser_slot_acquired:
                await self._browser_admission.release(run_id)
            self._run_requires_browser.pop(run_id, None)

    def _load_next_step(self, run_id: str) -> tuple[StepRun, PlanStep] | None:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None or run.status in {"CANCELLED", "CANCELLING"}:
                return None
            step_runs = session.scalars(select(StepRun).where(StepRun.run_id == run_id)).all()
            pending = []
            for step_run in step_runs:
                if step_run.status != "PENDING":
                    continue
                step = session.get(PlanStep, step_run.step_id)
                if step is None:
                    continue
                pending.append((step.step_order, step_run.step_run_id, step_run, step))
            if not pending:
                return None
            pending.sort(key=lambda item: (item[0], item[1]))
            step_run, step = pending[0][2], pending[0][3]
            session.expunge(step_run)
            session.expunge(step)
            return step_run, step

    async def _mark_step_running(self, run_id: str, step_run: StepRun, step: PlanStep) -> None:
        with SessionLocal() as session:
            db_step_run = session.get(StepRun, step_run.step_run_id)
            run = session.get(PlanRun, run_id)
            if db_step_run is None or run is None:
                raise ValueError("step run not found")
            db_step_run.status = "RUNNING"
            db_step_run.started_at = utc_now_iso()
            checkpoint = json.dumps(
                {
                    "phase": "running",
                    "step_id": get_public_step_id(step.step_id),
                    "started_at": db_step_run.started_at,
                    "heartbeat_at": db_step_run.started_at,
                    "progress": {
                        "activity": "step_started",
                        "action_type": step.action_type,
                    },
                }
            )
            db_step_run.checkpoint = checkpoint
            db_step_run.checkpoint_json = checkpoint
            run.status = "RUNNING"
            session.add(db_step_run)
            session.add(run)
            session.commit()
        await self._emit(
            run_id,
            "step_started",
            {"run_id": run_id, "step_id": get_public_step_id(step.step_id), "action_type": step.action_type},
        )

    async def _await_browser_slot(self, run_id: str, control: RunControl) -> bool:
        while True:
            if control.stop_requested:
                await self._browser_admission.cancel(run_id)
                return False
            await control.resume_event.wait()
            try:
                await self._browser_admission.acquire(
                    run_id,
                    is_paused=lambda: control.pause_requested,
                    should_cancel=lambda: control.stop_requested,
                )
                with SessionLocal() as session:
                    run = session.get(PlanRun, run_id)
                    if run is None or run.status in {"CANCELLED", "CANCELLING"}:
                        await self._browser_admission.release(run_id)
                        return False
                    run.status = "RUNNING"
                    run.completion_reason = None
                    run.failure_class = None
                    session.add(run)
                    session.commit()
                await self._emit(run_id, "run_admitted", {"run_id": run_id, "status": "RUNNING"})
                return True
            except BrowserRunAdmissionPaused:
                continue
            except BrowserRunAdmissionCancelled:
                return False

    async def _mark_step_done(self, run_id: str, step_run_id: str, result: dict[str, Any]) -> None:
        with SessionLocal() as session:
            step_run = session.get(StepRun, step_run_id)
            run = session.get(PlanRun, run_id)
            if step_run is None or run is None:
                raise ValueError("step run not found")
            checkpoint = json.dumps(result["checkpoint"])
            step_run.status = "DONE"
            step_run.ended_at = utc_now_iso()
            step_run.actual_count = result.get("actual_count")
            step_run.checkpoint = checkpoint
            step_run.checkpoint_json = checkpoint
            run.total_records = self._count_run_records(session, run_id)
            session.add(step_run)
            session.add(run)
            session.commit()
        await self._emit(
            run_id,
            "step_done",
            {
                "run_id": run_id,
                "step_run_id": step_run_id,
                "actual_count": result.get("actual_count"),
            },
        )

    def _count_run_records(self, session: Any, run_id: str) -> int:
        return int(
            session.scalar(
                select(func.count()).select_from(CrawledPost).where(CrawledPost.run_id == run_id)
            )
            or 0
        )

    def _resolve_action_timeout_sec(self, action_type: str) -> float:
        lookup = {
            "SEARCH_POSTS": "search_posts_timeout_sec",
            "SEARCH_IN_GROUP": "search_in_group_timeout_sec",
            "CRAWL_FEED": "crawl_feed_timeout_sec",
            "CRAWL_COMMENTS": "crawl_comments_timeout_sec",
            "SEARCH_GROUPS": "search_groups_timeout_sec",
            "JOIN_GROUP": "group_membership_timeout_sec",
            "CHECK_JOIN_STATUS": "group_membership_timeout_sec",
        }
        key = lookup.get(action_type)
        value = getattr(self._settings, key, None) if key else None
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    async def _update_step_progress(
        self,
        run_id: str,
        step_run_id: str,
        step: PlanStep,
        progress: dict[str, Any],
    ) -> None:
        heartbeat_at = utc_now_iso()
        payload: dict[str, Any] | None = None
        with SessionLocal() as session:
            db_step_run = session.get(StepRun, step_run_id)
            run = session.get(PlanRun, run_id)
            if db_step_run is None or run is None or db_step_run.status != "RUNNING":
                return
            checkpoint = json.loads(db_step_run.checkpoint or db_step_run.checkpoint_json or "{}")
            checkpoint["phase"] = "running"
            checkpoint["step_id"] = get_public_step_id(step.step_id)
            checkpoint["started_at"] = db_step_run.started_at
            checkpoint["heartbeat_at"] = heartbeat_at
            merged_progress = dict(checkpoint.get("progress") or {})
            merged_progress.update(progress)
            checkpoint["progress"] = merged_progress
            serialized = json.dumps(checkpoint)
            db_step_run.checkpoint = serialized
            db_step_run.checkpoint_json = serialized
            run.total_records = self._count_run_records(session, run_id)
            session.add(db_step_run)
            session.add(run)
            session.commit()
            payload = {
                "run_id": run_id,
                "step_run_id": step_run_id,
                "step_id": get_public_step_id(step.step_id),
                "action_type": step.action_type,
                "heartbeat_at": heartbeat_at,
                "progress": merged_progress,
                "total_records": run.total_records,
            }
        if payload is not None:
            await self._emit(run_id, "step_progress", payload)

    async def _finalize_cancelled_run(self, run_id: str, current_step_run_id: str | None) -> None:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None or run.status == "CANCELLED":
                return
            now = utc_now_iso()
            run.status = "CANCELLED"
            run.completion_reason = "USER_CANCELLED"
            run.failure_class = None
            run.ended_at = now
            run.total_records = self._count_run_records(session, run_id)
            step_runs = session.scalars(select(StepRun).where(StepRun.run_id == run_id)).all()
            for step_run in step_runs:
                if step_run.status == "RUNNING":
                    checkpoint = json.loads(step_run.checkpoint or step_run.checkpoint_json or "{}")
                    checkpoint["phase"] = "cancelled"
                    checkpoint["cancelled_at"] = now
                    checkpoint["step_id"] = get_public_step_id(step_run.step_id)
                    step_run.status = "SKIPPED"
                    step_run.error_message = "run cancelled by operator"
                    step_run.ended_at = now
                    serialized = json.dumps(checkpoint)
                    step_run.checkpoint = serialized
                    step_run.checkpoint_json = serialized
                    session.add(step_run)
                elif step_run.status == "PENDING":
                    checkpoint = json.loads(step_run.checkpoint or step_run.checkpoint_json or "{}")
                    checkpoint["phase"] = "cancelled"
                    checkpoint["cancelled_at"] = now
                    checkpoint["step_id"] = get_public_step_id(step_run.step_id)
                    step_run.status = "SKIPPED"
                    step_run.error_message = "skipped after run cancellation"
                    serialized = json.dumps(checkpoint)
                    step_run.checkpoint = serialized
                    step_run.checkpoint_json = serialized
                    session.add(step_run)
            session.add(run)
            session.commit()
        await self._emit(
            run_id,
            "run_cancelled",
            {
                "run_id": run_id,
                "status": "CANCELLED",
                "completion_reason": "USER_CANCELLED",
                "step_run_id": current_step_run_id,
            },
        )

    async def _run_browser_action(
        self,
        run_id: str,
        step_run: StepRun,
        step: PlanStep,
        action: Callable[[Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[Any]],
        *,
        activity: str,
    ) -> Any:
        control = self._controls[run_id]
        timeout_sec = self._resolve_action_timeout_sec(step.action_type)
        heartbeat_interval = float(getattr(self._settings, "step_heartbeat_interval_sec", 10.0) or 10.0)
        started = time.monotonic()

        async def progress_callback(progress: dict[str, Any]) -> None:
            enriched = dict(progress)
            enriched.setdefault("activity", activity)
            enriched["elapsed_sec"] = round(time.monotonic() - started, 1)
            await self._update_step_progress(run_id, step_run.step_run_id, step, enriched)

        task = asyncio.create_task(action(progress_callback))
        self._active_step_tasks[step_run.step_run_id] = task
        try:
            await self._update_step_progress(
                run_id,
                step_run.step_run_id,
                step,
                {"activity": activity, "elapsed_sec": 0.0},
            )
            while True:
                done, _pending = await asyncio.wait({task}, timeout=heartbeat_interval)
                if done:
                    try:
                        return task.result()
                    except asyncio.CancelledError as exc:
                        if control.stop_requested:
                            raise RunCancellationRequested(f"{step.action_type} cancelled") from exc
                        raise
                if control.stop_requested:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    raise RunCancellationRequested(f"{step.action_type} cancelled")
                elapsed = time.monotonic() - started
                await self._update_step_progress(
                    run_id,
                    step_run.step_run_id,
                    step,
                    {"activity": activity, "elapsed_sec": round(elapsed, 1)},
                )
                if timeout_sec > 0 and elapsed >= timeout_sec:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    raise StepActionTimeout(step.action_type, timeout_sec)
        finally:
            self._active_step_tasks.pop(step_run.step_run_id, None)

    async def _execute_step(self, run_id: str, step_run: StepRun, step: PlanStep) -> dict[str, Any]:
        action_spec = get_action_spec(step.action_type)
        if action_spec is None:
            raise ValueError(f"unsupported action_type: {step.action_type}")

        if step.read_or_write == "WRITE" and not self._health_monitor.is_write_allowed():
            raise PermissionError("Account not HEALTHY — write actions blocked")

        public_step_id = get_public_step_id(step.step_id)
        checkpoint = json.loads(step_run.checkpoint or step_run.checkpoint_json or "{}")
        control = self._controls[run_id]

        async def report_progress(progress: dict[str, Any]) -> None:
            await self._update_step_progress(run_id, step_run.step_run_id, step, progress)

        def should_stop() -> bool:
            return control.stop_requested

        if step.action_type == "SEARCH_GROUPS":
            result = await self._run_browser_action(
                run_id,
                step_run,
                step,
                lambda progress_callback: self._browser_agent.search_groups(
                    step.target,
                    target_count=step.estimated_count or 3,
                    progress_callback=progress_callback,
                ),
                activity="search_groups",
            )
            return {
                "actual_count": len(result["groups"]),
                "records_added": 0,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "groups": result["groups"],
                    "primary_group_id": result["primary_group_id"],
                },
            }

        if step.action_type == "CRAWL_FEED":
            group_ids = self._resolve_crawl_group_ids(run_id, step)
            if not group_ids:
                return {
                    "actual_count": 0,
                    "records_added": 0,
                    "checkpoint": {
                        "phase": "done",
                        "step_id": public_step_id,
                        "group_ids": [],
                        "collected_count": 0,
                        "persisted_count": 0,
                        "duplicate_count": 0,
                        "note": "no_accessible_groups_resolved",
                    },
                }

            remaining = min(step.estimated_count or 12, 12)
            all_posts: list[RawPost] = []
            crawled_group_ids: list[str] = []
            persisted_total = 0
            duplicate_total = 0
            all_checkpoint_posts: list[dict[str, Any]] = []
            all_batch_summaries: list[dict[str, Any]] = []
            for group_id in group_ids:
                if remaining <= 0:
                    break
                posts = await self._run_browser_action(
                    run_id,
                    step_run,
                    step,
                    lambda progress_callback, gid=group_id, target=remaining: self._browser_agent.crawl_feed(
                        group_id=gid,
                        target_count=target,
                        checkpoint=checkpoint,
                        progress_callback=progress_callback,
                    ),
                    activity="crawl_feed",
                )
                for post in posts:
                    post["source_group_id"] = group_id
                if posts:
                    crawled_group_ids.append(group_id)
                all_posts.extend(posts)
                processed = await self._process_candidates(
                    run_id=run_id,
                    step_run_id=step_run.step_run_id,
                    records=posts,
                    source_type=step.action_type,
                    query_text=step.target,
                    progress_callback=report_progress,
                    should_stop=should_stop,
                )
                persisted_count = processed["persisted_count"]
                duplicate_count = processed["duplicate_count"]
                persisted_total += persisted_count
                duplicate_total += duplicate_count
                all_checkpoint_posts.extend(processed["posts"])
                all_batch_summaries.extend(processed["batch_summaries"])
                remaining -= len(posts)
            return {
                "actual_count": len(all_posts),
                "records_added": persisted_total,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "group_ids": crawled_group_ids,
                    "collected_count": len(all_posts),
                    "persisted_count": persisted_total,
                    "duplicate_count": duplicate_total,
                    "batch_summaries": all_batch_summaries,
                    "posts": all_checkpoint_posts,
                },
            }

        if step.action_type == "JOIN_GROUP":
            group_ids = self._resolve_private_group_ids(run_id, step)
            join_results = []
            for group_id in group_ids[: step.estimated_count or len(group_ids)]:
                join_results.append(
                    await self._run_browser_action(
                        run_id,
                        step_run,
                        step,
                        lambda progress_callback, gid=group_id: self._browser_agent.join_group(
                            gid,
                            progress_callback=progress_callback,
                        ),
                        activity="join_group",
                    )
                )
            requested_group_ids = [
                item["group_id"]
                for item in join_results
                if item.get("confirmed")
            ]
            return {
                "actual_count": len(requested_group_ids),
                "records_added": 0,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "requested_group_ids": requested_group_ids,
                    "group_statuses": join_results,
                },
            }

        if step.action_type == "CHECK_JOIN_STATUS":
            group_ids = self._resolve_requested_group_ids(run_id, step)
            status_results = []
            approved_group_ids: list[str] = []
            pending_group_ids: list[str] = []
            blocked_group_ids: list[str] = []
            unanswered_group_ids: list[str] = []
            for group_id in group_ids[: step.estimated_count or len(group_ids)]:
                status = await self._run_browser_action(
                    run_id,
                    step_run,
                    step,
                    lambda progress_callback, gid=group_id: self._browser_agent.check_join_status(
                        gid,
                        progress_callback=progress_callback,
                    ),
                    activity="check_join_status",
                )
                status_results.append(status)
                if status.get("can_access"):
                    approved_group_ids.append(group_id)
                elif status.get("status") == "pending":
                    pending_group_ids.append(group_id)
                elif status.get("status") == "blocked":
                    blocked_group_ids.append(group_id)
                elif status.get("status") == "unanswered":
                    unanswered_group_ids.append(group_id)
            return {
                "actual_count": len(approved_group_ids),
                "records_added": 0,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "checked_group_ids": group_ids,
                    "approved_group_ids": approved_group_ids,
                    "pending_group_ids": pending_group_ids,
                    "blocked_group_ids": blocked_group_ids,
                    "unanswered_group_ids": unanswered_group_ids,
                    "group_statuses": status_results,
                },
            }

        if step.action_type == "SEARCH_POSTS":
            remaining = step.estimated_count or 10
            queries = list(self._resolve_search_queries(run_id, step))
            seen_queries = {self._normalize_query_key(query) for query in queries}
            all_posts: list[RawPost] = []
            all_checkpoint_posts: list[dict[str, Any]] = []
            all_batch_summaries: list[dict[str, Any]] = []
            discovered_groups: list[dict[str, Any]] = []
            query_attempts: list[dict[str, Any]] = []
            persisted_count = 0
            duplicate_count = 0
            accepted_total = 0

            query_index = 0
            while query_index < len(queries):
                query = queries[query_index]
                query_index += 1
                if remaining <= 0:
                    break
                result = await self._run_browser_action(
                    run_id,
                    step_run,
                    step,
                    lambda progress_callback, q=query, target=remaining: self._browser_agent.search_posts(
                        q,
                        target_count=target,
                        progress_callback=progress_callback,
                    ),
                    activity="search_posts",
                )
                posts_as_raw: list[RawPost] = []
                for p in result["posts"]:
                    posts_as_raw.append(
                        RawPost(
                            post_id=p["post_id"],
                            group_id_hash=(
                                self._browser_agent.hash_group_id(p["source_group_id"])
                                if p.get("source_group_id")
                                else self._browser_agent.hash_group_id(f"scope:{p['post_id']}")
                            ),
                            content=p["content"],
                            record_type="POST",
                            source_url=p.get("post_url"),
                            parent_post_id=None,
                            parent_post_url=None,
                            posted_at=p.get("posted_at"),
                            reaction_count=p.get("reaction_count", 0),
                            comment_count=p.get("comment_count", 0),
                            source_group_id=p.get("source_group_id"),
                        )
                    )
                processed = await self._process_candidates(
                    run_id=run_id,
                    step_run_id=step_run.step_run_id,
                    records=posts_as_raw,
                    source_type=step.action_type,
                    query_text=query,
                    progress_callback=report_progress,
                    should_stop=should_stop,
                )
                persisted_count += processed["persisted_count"]
                duplicate_count += processed["duplicate_count"]
                accepted_total += processed["accepted_count"]
                remaining -= len(result["posts"])
                all_posts.extend(posts_as_raw)
                all_checkpoint_posts.extend(processed["posts"])
                all_batch_summaries.extend(processed["batch_summaries"])
                query_attempts.append(
                    {
                        "query": query,
                        "collected_count": len(result["posts"]),
                        "accepted_count": processed["accepted_count"],
                        "stop_reason": processed["stop_reason"],
                        "reason_cluster": processed.get("reason_cluster"),
                        "reformulated_queries": processed.get("reformulated_queries", []),
                        "used_reformulation": query != queries[0],
                    }
                )
                for reformulated_query in processed.get("reformulated_queries", []):
                    normalized = self._normalize_query_key(reformulated_query)
                    if normalized in seen_queries:
                        continue
                    seen_queries.add(normalized)
                    queries.append(reformulated_query)
                for group in result["discovered_groups"]:
                    if not any(existing.get("group_id") == group.get("group_id") for existing in discovered_groups):
                        discovered_groups.append(group)
                if accepted_total > 0 or not processed["should_reformulate"]:
                    break

            accepted_group_ids = self._dedupe_keep_order(
                [
                    gid
                    for post in all_checkpoint_posts
                    for gid in [post.get("source_group_id")]
                    if gid and post.get("pre_ai_status") == "ACCEPTED"
                ]
            )
            return {
                "actual_count": len(all_posts),
                "records_added": persisted_count,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "posts": all_checkpoint_posts,
                    "discovered_groups": discovered_groups,
                    "accepted_group_ids": accepted_group_ids,
                    "batch_summaries": all_batch_summaries,
                    "query_attempts": query_attempts,
                    "persisted_count": persisted_count,
                    "duplicate_count": duplicate_count,
                },
            }

        if step.action_type == "CRAWL_COMMENTS":
            post_refs = self._resolve_post_refs(run_id, step)
            all_comments: list[RawPost] = []
            persisted_total = 0
            duplicate_total = 0
            all_checkpoint_comments: list[dict[str, Any]] = []
            all_batch_summaries: list[dict[str, Any]] = []
            per_post_limit = max(1, (step.estimated_count or 20) // max(len(post_refs), 1))
            for post_ref in post_refs:
                comments = await self._run_browser_action(
                    run_id,
                    step_run,
                    step,
                    lambda progress_callback, ref=post_ref, limit=per_post_limit: self._browser_agent.crawl_comments(
                        ref["post_url"],
                        target_count=limit,
                        parent_post_id=ref.get("post_id"),
                        source_group_id=ref.get("source_group_id"),
                        progress_callback=progress_callback,
                    ),
                    activity="crawl_comments",
                )
                all_comments.extend(comments)
                processed = await self._process_candidates(
                    run_id=run_id,
                    step_run_id=step_run.step_run_id,
                    records=comments,
                    source_type=step.action_type,
                    query_text=post_ref.get("query_text") or step.target,
                    progress_callback=report_progress,
                    should_stop=should_stop,
                )
                persisted = processed["persisted_count"]
                dupes = processed["duplicate_count"]
                persisted_total += persisted
                duplicate_total += dupes
                all_checkpoint_comments.extend(processed["posts"])
                all_batch_summaries.extend(processed["batch_summaries"])
            return {
                "actual_count": len(all_comments),
                "records_added": persisted_total,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "post_urls_crawled": [item["post_url"] for item in post_refs],
                    "collected_count": len(all_comments),
                    "persisted_count": persisted_total,
                    "duplicate_count": duplicate_total,
                    "posts": all_checkpoint_comments,
                    "batch_summaries": all_batch_summaries,
                },
            }

        if step.action_type == "SEARCH_IN_GROUP":
            group_ids = self._resolve_discovered_group_ids(run_id, step)
            queries = list(self._resolve_search_queries(run_id, step))
            seen_queries = {self._normalize_query_key(query) for query in queries}
            all_posts: list[RawPost] = []
            persisted_total = 0
            duplicate_total = 0
            all_checkpoint_posts: list[dict[str, Any]] = []
            all_batch_summaries: list[dict[str, Any]] = []
            query_attempts: list[dict[str, Any]] = []
            remaining = step.estimated_count or 10
            accepted_total = 0
            query_index = 0
            while query_index < len(queries):
                query = queries[query_index]
                query_index += 1
                query_accepted = 0
                query_collected = 0
                query_stop_reason: str | None = None
                should_reformulate = False
                reason_cluster: str | None = None
                reformulated_queries: list[str] = []
                for group_id in group_ids:
                    if remaining <= 0:
                        break
                    posts = await self._run_browser_action(
                        run_id,
                        step_run,
                        step,
                        lambda progress_callback, gid=group_id, q=query, target=remaining: self._browser_agent.search_in_group(
                            gid,
                            q,
                            target_count=target,
                            progress_callback=progress_callback,
                        ),
                        activity="search_in_group",
                    )
                    for post in posts:
                        post["source_group_id"] = group_id
                    all_posts.extend(posts)
                    processed = await self._process_candidates(
                        run_id=run_id,
                        step_run_id=step_run.step_run_id,
                        records=posts,
                        source_type=step.action_type,
                        query_text=query,
                        progress_callback=report_progress,
                        should_stop=should_stop,
                    )
                    persisted = processed["persisted_count"]
                    dupes = processed["duplicate_count"]
                    persisted_total += persisted
                    duplicate_total += dupes
                    query_accepted += processed["accepted_count"]
                    accepted_total += processed["accepted_count"]
                    query_collected += len(posts)
                    remaining -= len(posts)
                    all_checkpoint_posts.extend(processed["posts"])
                    all_batch_summaries.extend(processed["batch_summaries"])
                    query_stop_reason = processed["stop_reason"]
                    should_reformulate = processed["should_reformulate"]
                    reason_cluster = processed.get("reason_cluster")
                    reformulated_queries = processed.get("reformulated_queries", [])
                    if accepted_total > 0 or should_reformulate:
                        break
                query_attempts.append(
                    {
                        "query": query,
                        "collected_count": query_collected,
                        "accepted_count": query_accepted,
                        "stop_reason": query_stop_reason,
                        "reason_cluster": reason_cluster,
                        "reformulated_queries": reformulated_queries,
                        "used_reformulation": query != queries[0],
                    }
                )
                for reformulated_query in reformulated_queries:
                    normalized = self._normalize_query_key(reformulated_query)
                    if normalized in seen_queries:
                        continue
                    seen_queries.add(normalized)
                    queries.append(reformulated_query)
                if remaining <= 0 or accepted_total > 0 or not should_reformulate:
                    break
            return {
                "actual_count": len(all_posts),
                "records_added": persisted_total,
                "checkpoint": {
                    "phase": "done",
                    "step_id": public_step_id,
                    "group_ids_searched": [g for g in group_ids],
                    "search_query": queries[0] if queries else self._resolve_search_query(step),
                    "query_attempts": query_attempts,
                    "collected_count": len(all_posts),
                    "persisted_count": persisted_total,
                    "duplicate_count": duplicate_total,
                    "posts": all_checkpoint_posts,
                    "batch_summaries": all_batch_summaries,
                },
            }

        await asyncio.sleep(1)
        return {
            "actual_count": 0,
            "records_added": 0,
            "checkpoint": {"phase": "done", "step_id": public_step_id},
        }

    def _resolve_crawl_group_ids(self, run_id: str, step: PlanStep) -> list[str]:
        target = step.target.lower()
        payloads = self._get_step_payloads(run_id)
        step_refs = self._extract_step_refs(step)
        group_ids: list[str] = []

        if "approved-private" in target or "approved private" in target:
            for ref in step_refs:
                group_ids.extend(payloads.get(ref, {}).get("approved_group_ids", []))
        elif "public-group" in target or "public groups" in target:
            for ref in step_refs:
                payload = payloads.get(ref, {})
                for group in payload.get("groups", []):
                    if group.get("privacy") == "PUBLIC":
                        group_ids.append(group["group_id"])
                for group in payload.get("discovered_groups", []):
                    if group.get("privacy") == "PUBLIC":
                        group_ids.append(group["group_id"])
        else:
            for ref in step_refs:
                payload = payloads.get(ref, {})
                if payload.get("primary_group_id"):
                    group_ids.append(payload["primary_group_id"])
                for group in payload.get("discovered_groups", []):
                    group_ids.append(group["group_id"])

        if not group_ids:
            fallback = step.target.split(":")[0].lower().replace(" ", "-")
            if fallback:
                group_ids.append(fallback)
        return self._dedupe_keep_order(group_ids)

    def _step_requires_browser(self, step: PlanStep) -> bool:
        return step.action_type in {
            "SEARCH_GROUPS",
            "JOIN_GROUP",
            "CHECK_JOIN_STATUS",
            "CRAWL_FEED",
            "SEARCH_POSTS",
            "CRAWL_COMMENTS",
            "SEARCH_IN_GROUP",
        }

    def _classify_failure(self, exc: Exception, current_step_run_id: str | None) -> tuple[str, str]:
        if isinstance(exc, BrowserStartupError):
            return "INFRA_BROWSER_BOOT_FAILURE", "INFRA_BROWSER_BOOT_FAILURE"
        if isinstance(exc, StepActionTimeout):
            return "STEP_STUCK_TIMEOUT", "STEP_STUCK_TIMEOUT"
        if current_step_run_id:
            return "STEP_ERROR", "STEP_EXECUTION_ERROR"
        return "POST_RUN_ERROR", "POST_RUN_ERROR"

    def _normalize_query_key(self, query: str) -> str:
        return re.sub(r"\s+", " ", (query or "").strip().lower())

    def _resolve_private_group_ids(self, run_id: str, step: PlanStep) -> list[str]:
        payloads = self._get_step_payloads(run_id)
        group_ids: list[str] = []
        for ref in self._extract_step_refs(step):
            payload = payloads.get(ref, {})
            for group in payload.get("groups", []):
                if group.get("privacy") == "PRIVATE":
                    group_ids.append(group["group_id"])
            for group in payload.get("discovered_groups", []):
                if group.get("privacy") == "PRIVATE":
                    group_ids.append(group["group_id"])
        return self._dedupe_keep_order(group_ids)

    def _resolve_requested_group_ids(self, run_id: str, step: PlanStep) -> list[str]:
        payloads = self._get_step_payloads(run_id)
        group_ids: list[str] = []
        for ref in self._extract_step_refs(step):
            payload = payloads.get(ref, {})
            if payload.get("requested_group_ids"):
                group_ids.extend(payload["requested_group_ids"])
            elif payload.get("groups"):
                for group in payload["groups"]:
                    if group.get("privacy") == "PRIVATE":
                        group_ids.append(group["group_id"])
            elif payload.get("discovered_groups"):
                for group in payload["discovered_groups"]:
                    if group.get("privacy") == "PRIVATE" and group.get("status") in {"pending", "not_joined"}:
                        group_ids.append(group["group_id"])
        return self._dedupe_keep_order(group_ids)

    def _resolve_post_refs(self, run_id: str, step: PlanStep) -> list[dict[str, str]]:
        payloads = self._get_step_payloads(run_id)
        post_refs: list[dict[str, str]] = []
        allowed_statuses = {"ACCEPTED"}
        if self._allows_uncertain():
            allowed_statuses.add("UNCERTAIN")
        for ref in self._extract_step_refs(step):
            payload = payloads.get(ref, {})
            for post in payload.get("posts", []):
                url = post.get("post_url")
                status = post.get("pre_ai_status")
                if url and (status is None or status in allowed_statuses):
                    post_refs.append(
                        {
                            "post_id": post.get("post_id") or "",
                            "post_url": url,
                            "source_group_id": post.get("source_group_id") or "",
                            "query_text": post.get("query_text") or "",
                        }
                    )
        unique_refs: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for post_ref in post_refs:
            if post_ref["post_url"] in seen_urls:
                continue
            seen_urls.add(post_ref["post_url"])
            unique_refs.append(post_ref)
        return unique_refs

    def _resolve_discovered_group_ids(self, run_id: str, step: PlanStep) -> list[str]:
        payloads = self._get_step_payloads(run_id)
        group_ids: list[str] = []
        for ref in self._extract_step_refs(step):
            payload = payloads.get(ref, {})
            if payload.get("accepted_group_ids"):
                group_ids.extend(payload["accepted_group_ids"])
            for group in payload.get("discovered_groups", []):
                gid = group.get("group_id")
                if gid:
                    can_access = group.get("can_access")
                    status = group.get("status")
                    if can_access or status in {"approved", "already_member"}:
                        group_ids.append(gid)
            if payload.get("approved_group_ids"):
                group_ids.extend(payload["approved_group_ids"])
        return self._dedupe_keep_order(group_ids)

    def _resolve_search_query(self, step: PlanStep) -> str:
        target = step.target or ""
        match = re.match(r"keyword:\s*(.+?)\s+in\s+groups?\s+from\s+step-", target, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        if ":" in target:
            return target.split(":", 1)[1].strip().split(" in ")[0].strip()
        return target.split(" in ")[0].strip() or "research"

    def _resolve_search_queries(self, run_id: str, step: PlanStep) -> list[str]:
        primary_query = self._resolve_search_query(step)
        profile = self._get_retrieval_profile_for_run(run_id)
        validity_spec = self._get_validity_spec_for_run(run_id)
        max_variants = int(getattr(self._settings, "retrieval_max_query_variants", 2) or 2)
        return self._retrieval_profile_builder.suggest_queries(
            primary_query,
            profile,
            validity_spec=validity_spec,
            max_variants=max_variants,
        )

    def _get_step_payloads(self, run_id: str) -> dict[str, dict[str, Any]]:
        with SessionLocal() as session:
            step_runs = session.scalars(select(StepRun).where(StepRun.run_id == run_id)).all()
            payloads: dict[str, dict[str, Any]] = {}
            for step_run in step_runs:
                payload = json.loads(step_run.checkpoint or step_run.checkpoint_json or "{}")
                payloads[get_public_step_id(step_run.step_id)] = payload
            return payloads

    def _extract_step_refs(self, step: PlanStep) -> list[str]:
        dependency_ids = [
            get_public_step_id(item)
            for item in json.loads(step.dependency_step_ids or "[]")
        ]
        target_refs = re.findall(r"(write-step-\d+|step-\d+)", step.target.lower())
        return self._dedupe_keep_order([*dependency_ids, *target_refs])

    def _dedupe_keep_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _persist_posts(self, run_id: str, step_run_id: str, posts: list[dict[str, Any]]) -> tuple[int, int]:
        if not posts:
            return 0, 0

        with SessionLocal() as session:
            incoming_by_key: dict[str, dict[str, Any]] = {}
            duplicate_in_batch = 0
            for post in posts:
                dedupe_key = post.get("source_url") or post["post_id"]
                if dedupe_key in incoming_by_key:
                    duplicate_in_batch += 1
                    continue
                incoming_by_key[dedupe_key] = post

            existing_post_ids = set(
                session.scalars(
                    select(CrawledPost.post_id).where(
                        CrawledPost.post_id.in_([post["post_id"] for post in incoming_by_key.values()])
                    )
                ).all()
            )
            run_records = session.scalars(select(CrawledPost).where(CrawledPost.run_id == run_id)).all()
            run_source_map = {record.source_url: record.post_id for record in run_records if record.source_url}

            inserted_count = 0
            duplicate_in_run = 0
            post_id_aliases: dict[str, str] = {}
            for dedupe_key, post in incoming_by_key.items():
                if dedupe_key in run_source_map:
                    duplicate_in_run += 1
                    continue

                original_post_id = post["post_id"]
                post_id = original_post_id
                if post_id in existing_post_ids:
                    post_id = self._build_run_scoped_post_id(session, run_id, original_post_id)

                parent_post_id = post.get("parent_post_id")
                parent_post_url = post.get("parent_post_url")
                if parent_post_url and parent_post_url in run_source_map:
                    parent_post_id = run_source_map[parent_post_url]
                elif parent_post_id and parent_post_id in post_id_aliases:
                    parent_post_id = post_id_aliases[parent_post_id]

                session.add(
                    CrawledPost(
                        post_id=post_id,
                        run_id=run_id,
                        step_run_id=step_run_id,
                        group_id_hash=post["group_id_hash"],
                        content=post["content"],
                        content_masked=post["content"],
                        record_type=post.get("record_type", "POST"),
                        source_url=post.get("source_url"),
                        parent_post_id=parent_post_id,
                        parent_post_url=parent_post_url,
                        posted_at=post.get("posted_at"),
                        reaction_count=post.get("reaction_count", 0),
                        comment_count=post.get("comment_count", 0),
                        is_excluded=False,
                    )
                )
                if post.get("source_url"):
                    run_source_map[post["source_url"]] = post_id
                post_id_aliases[original_post_id] = post_id
                inserted_count += 1
            session.commit()
            duplicate_count = duplicate_in_batch + duplicate_in_run
            return inserted_count, duplicate_count

    async def _process_candidates(
        self,
        *,
        run_id: str,
        step_run_id: str,
        records: list[dict[str, Any]],
        source_type: str,
        query_text: str,
        progress_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        if not records:
            return {
                "persisted_count": 0,
                "duplicate_count": 0,
                "posts": [],
                "accepted_group_ids": [],
                "batch_summaries": [],
                "accepted_count": 0,
                "scanned_count": 0,
                "should_reformulate": False,
                "stop_reason": None,
            }

        batch_size = max(1, int(getattr(self._settings, "retrieval_batch_size", 20) or 20))
        profile = self._get_retrieval_profile_for_run(run_id)
        validity_spec = self._get_validity_spec_for_run(run_id)
        parent_context = self._load_parent_context_map(run_id) if any(r.get("record_type") == "COMMENT" for r in records) else {}
        persisted_total = 0
        duplicate_total = 0
        checkpoint_posts: list[dict[str, Any]] = []
        accepted_group_ids: list[str] = []
        batch_summaries: list[dict[str, Any]] = []
        consecutive_weak_batches = 0
        consecutive_zero_accept_batches = 0
        total_accepted = 0
        total_scanned = 0
        stop_reason: str | None = None
        reason_cluster: str | None = None
        reformulated_queries: list[str] = []

        for batch_index, start in enumerate(range(0, len(records), batch_size), start=1):
            if callable(should_stop) and should_stop():
                raise RunCancellationRequested("run cancelled before candidate scoring")
            raw_batch = records[start : start + batch_size]
            query_family = self._retrieval_profile_builder.infer_query_family(query_text, profile)
            if progress_callback is not None:
                await progress_callback(
                    {
                        "activity": "scoring_batch",
                        "query_text": query_text,
                        "query_family": query_family,
                        "batch_index": batch_index,
                        "batch_size": len(raw_batch),
                        "scanned_count": total_scanned,
                        "accepted_count": total_accepted,
                    }
                )
            scored_entries: list[dict[str, Any]] = []
            for raw in raw_batch:
                if callable(should_stop) and should_stop():
                    raise RunCancellationRequested("run cancelled during candidate scoring")
                raw["query_text"] = query_text
                record_type = str(raw.get("record_type") or "POST")
                parent_entry = parent_context.get(raw.get("parent_post_id") or "") or parent_context.get(raw.get("parent_post_url") or "")
                hard_filter = self._model_judge.hard_filter(
                    content=str(raw.get("content") or ""),
                    record_type=record_type,
                    validity_spec=validity_spec,
                )
                deterministic_score = self._relevance_engine.score(
                    content=str(raw.get("content") or ""),
                    retrieval_profile=profile,
                    record_type=record_type,
                    source_type=source_type,
                    query_family=query_family,
                    parent_text=(parent_entry or {}).get("content"),
                    parent_status=(parent_entry or {}).get("status"),
                )
                if hard_filter.rejected:
                    judge_result = self._model_judge.build_hard_reject_result(
                        validity_spec=validity_spec,
                        content_id=str(raw.get("post_id") or ""),
                        filter_result=hard_filter,
                    )
                else:
                    try:
                        judge_result = await self._model_judge.judge_text(
                            validity_spec=validity_spec,
                            content_id=str(raw.get("post_id") or ""),
                            content=hard_filter.cleaned_text,
                            record_type=record_type,
                            source_type=source_type,
                            source_url=raw.get("source_url"),
                            query_text=query_text,
                            query_family=query_family,
                            parent_context=parent_entry,
                        )
                        if self._model_judge.should_use_image_fallback(
                            candidate=raw,
                            initial_result=judge_result,
                            validity_spec=validity_spec,
                        ):
                            image_summary, _image_meta = await self._model_judge.build_image_summary(
                                candidate=raw,
                                validity_spec=validity_spec,
                            )
                            if image_summary:
                                judge_result = await self._model_judge.judge_text(
                                    validity_spec=validity_spec,
                                    content_id=str(raw.get("post_id") or ""),
                                    content=hard_filter.cleaned_text,
                                    record_type=record_type,
                                    source_type=source_type,
                                    source_url=raw.get("source_url"),
                                    query_text=query_text,
                                    query_family=query_family,
                                    parent_context=parent_entry,
                                    image_summary=image_summary,
                                    used_image_understanding=True,
                                )
                    except Exception:
                        judge_result = self._model_judge.fallback_from_retrieval_score(
                            validity_spec=validity_spec,
                            content_id=str(raw.get("post_id") or ""),
                            score=deterministic_score,
                            reason_prefix="model_judge_fallback",
                        )
                scored_entries.append(
                    {
                        "raw": raw,
                        "judge_result": judge_result,
                        "fallback_score": deterministic_score,
                        "cleaned_text": hard_filter.cleaned_text,
                        "quality_flags": hard_filter.quality_flags,
                        "query_family": query_family,
                    }
                )

            batch_health = self._batch_evaluator.evaluate(
                [entry["judge_result"] for entry in scored_entries],
                validity_spec,
            )
            total_accepted += batch_health.accepted_count
            total_scanned += len(raw_batch)
            if batch_health.decision == "weak":
                consecutive_weak_batches += 1
            else:
                consecutive_weak_batches = 0
            if batch_health.accepted_count == 0:
                consecutive_zero_accept_batches += 1
            else:
                consecutive_zero_accept_batches = 0

            batch_decision = "continue"
            if batch_health.decision == "reformulate" and total_accepted == 0:
                batch_decision = "reformulate"
                stop_reason = "uncertain_reformulation_triggered"
            if consecutive_weak_batches >= int(getattr(self._settings, "retrieval_max_consecutive_weak_batches", 2)):
                batch_decision = "stop"
                stop_reason = "weak_batches_exceeded"
            if (
                total_accepted == 0
                and consecutive_zero_accept_batches >= int(getattr(self._settings, "retrieval_max_zero_accept_batches", 2))
            ):
                batch_decision = "stop"
                stop_reason = "zero_accepted_batches_exceeded"
            if total_scanned >= int(getattr(self._settings, "retrieval_max_scanned_per_path", 60)) and total_accepted < int(getattr(self._settings, "retrieval_min_accepted_per_path", 3)):
                batch_decision = "stop"
                stop_reason = "min_accepts_not_reached"

            if total_accepted == 0 and batch_decision in {"stop", "reformulate"}:
                rejected_reason_codes = [
                    reason_code
                    for entry in scored_entries
                    for reason_code in entry["judge_result"].reason_codes
                    if entry["judge_result"].decision == "REJECTED"
                ]
                reason_cluster = self._retrieval_profile_builder.cluster_reject_reasons(
                    rejected_reason_codes,
                    query=query_text,
                    validity_spec=validity_spec,
                )
                reformulated_queries = self._retrieval_profile_builder.build_reformulations(
                    query_text,
                    profile,
                    validity_spec,
                    reason_cluster,
                    max_variants=max(1, int(getattr(self._settings, "retrieval_max_query_variants", 2) or 2)),
                )

            if callable(should_stop) and should_stop():
                raise RunCancellationRequested("run cancelled before candidate persistence")
            persisted_count, duplicate_count, persisted_refs = self._persist_scored_posts(
                run_id=run_id,
                step_run_id=step_run_id,
                scored_entries=scored_entries,
                source_type=source_type,
                batch_index=batch_index,
                batch_decision=batch_decision,
            )
            persisted_total += persisted_count
            duplicate_total += duplicate_count
            checkpoint_posts.extend(persisted_refs)
            accepted_group_ids.extend(
                ref["source_group_id"]
                for ref in persisted_refs
                if ref.get("source_group_id") and ref.get("pre_ai_status") == "ACCEPTED"
            )
            summary = {
                "batch_index": batch_index,
                **batch_health.as_dict(),
                "batch_size": len(raw_batch),
                "batch_decision": batch_decision,
                "reason_cluster": reason_cluster if batch_decision in {"stop", "reformulate"} else None,
                "stop_reason": stop_reason if batch_decision == "stop" else None,
            }
            batch_summaries.append(summary)
            if progress_callback is not None:
                await progress_callback(
                    {
                        "activity": "persisted_batch",
                        "query_text": query_text,
                        "query_family": query_family,
                        "batch_index": batch_index,
                        "batch_decision": batch_decision,
                        "persisted_count": persisted_total,
                        "accepted_count": total_accepted,
                        "scanned_count": total_scanned,
                        "reason_cluster": reason_cluster,
                    }
                )
            if batch_decision in {"stop", "reformulate"}:
                break

        return {
            "persisted_count": persisted_total,
            "duplicate_count": duplicate_total,
            "posts": checkpoint_posts,
            "accepted_group_ids": self._dedupe_keep_order(accepted_group_ids),
            "batch_summaries": batch_summaries,
            "accepted_count": total_accepted,
            "scanned_count": total_scanned,
            "should_reformulate": total_accepted == 0
            and bool(batch_summaries)
            and batch_summaries[-1]["batch_decision"] in {"stop", "reformulate"},
            "reason_cluster": reason_cluster,
            "reformulated_queries": reformulated_queries,
            "stop_reason": stop_reason,
        }

    def _persist_scored_posts(
        self,
        *,
        run_id: str,
        step_run_id: str,
        scored_entries: list[dict[str, Any]],
        source_type: str,
        batch_index: int,
        batch_decision: str,
    ) -> tuple[int, int, list[dict[str, Any]]]:
        if not scored_entries:
            return 0, 0, []

        with SessionLocal() as session:
            incoming_by_key: dict[str, dict[str, Any]] = {}
            duplicate_in_batch = 0
            for entry in scored_entries:
                raw = entry["raw"]
                dedupe_key = raw.get("source_url") or raw["post_id"]
                if dedupe_key in incoming_by_key:
                    duplicate_in_batch += 1
                    continue
                incoming_by_key[dedupe_key] = entry

            existing_post_ids = set(
                session.scalars(
                    select(CrawledPost.post_id).where(
                        CrawledPost.post_id.in_([entry["raw"]["post_id"] for entry in incoming_by_key.values()])
                    )
                ).all()
            )
            run_records = session.scalars(select(CrawledPost).where(CrawledPost.run_id == run_id)).all()
            run_source_map = {record.source_url: record.post_id for record in run_records if record.source_url}

            inserted_count = 0
            duplicate_in_run = 0
            post_id_aliases: dict[str, str] = {}
            persisted_refs: list[dict[str, Any]] = []
            for dedupe_key, entry in incoming_by_key.items():
                raw = entry["raw"]
                judge_result = entry["judge_result"]
                fallback_score = entry["fallback_score"]
                if dedupe_key in run_source_map:
                    duplicate_in_run += 1
                    continue

                original_post_id = raw["post_id"]
                post_id = original_post_id
                if post_id in existing_post_ids:
                    post_id = self._build_run_scoped_post_id(session, run_id, original_post_id)

                parent_post_id = raw.get("parent_post_id")
                parent_post_url = raw.get("parent_post_url")
                if parent_post_url and parent_post_url in run_source_map:
                    parent_post_id = run_source_map[parent_post_url]
                elif parent_post_id and parent_post_id in post_id_aliases:
                    parent_post_id = post_id_aliases[parent_post_id]

                processing_stage = (
                    "CLEAN_ACCEPTED"
                    if judge_result.decision in {"ACCEPTED", "UNCERTAIN"}
                    else "SCORED_REJECTED"
                )
                session.add(
                    CrawledPost(
                        post_id=post_id,
                        run_id=run_id,
                        step_run_id=step_run_id,
                        group_id_hash=raw["group_id_hash"],
                        content=raw["content"],
                        content_masked=entry.get("cleaned_text") or fallback_score.cleaned_text,
                        record_type=raw.get("record_type", "POST"),
                        source_url=raw.get("source_url"),
                        parent_post_id=parent_post_id,
                        parent_post_url=parent_post_url,
                        posted_at=raw.get("posted_at"),
                        reaction_count=raw.get("reaction_count", 0),
                        comment_count=raw.get("comment_count", 0),
                        processing_stage=processing_stage,
                        pre_ai_status=judge_result.decision,
                        pre_ai_score=judge_result.relevance_score,
                        pre_ai_reason=";".join(judge_result.reason_codes) or judge_result.short_rationale,
                        judge_decision=judge_result.decision,
                        judge_relevance_score=judge_result.relevance_score,
                        judge_confidence_score=judge_result.confidence_score,
                        judge_reason_codes_json=json.dumps(judge_result.reason_codes, ensure_ascii=False),
                        judge_rationale=judge_result.short_rationale,
                        judge_used_image_understanding=judge_result.used_image_understanding,
                        judge_image_summary=judge_result.image_summary,
                        judge_model_family=judge_result.model_family,
                        judge_model_version=judge_result.model_version,
                        judge_policy_version=judge_result.policy_version,
                        judge_cache_key=judge_result.cache_key,
                        score_breakdown_json=json.dumps(
                            {
                                "judge_reason_codes": judge_result.reason_codes,
                                "judge_raw": judge_result.raw_response,
                                "fallback_score_breakdown": fallback_score.score_breakdown,
                            },
                            ensure_ascii=False,
                        ),
                        quality_flags_json=json.dumps(
                            entry.get("quality_flags") or fallback_score.quality_flags,
                            ensure_ascii=False,
                        ),
                        query_family=entry.get("query_family") or fallback_score.query_family,
                        source_type=source_type,
                        source_batch_index=batch_index,
                        batch_decision=batch_decision,
                        provider_used=judge_result.provider_used,
                        fallback_used=judge_result.fallback_used,
                        is_excluded=judge_result.decision == "REJECTED",
                        exclude_reason=(";".join(judge_result.reason_codes) or judge_result.short_rationale)
                        if judge_result.decision == "REJECTED"
                        else None,
                    )
                )
                if raw.get("source_url"):
                    run_source_map[raw["source_url"]] = post_id
                post_id_aliases[original_post_id] = post_id
                inserted_count += 1
                persisted_refs.append(
                    {
                        "post_id": post_id,
                        "post_url": raw.get("source_url"),
                        "source_group_id": raw.get("source_group_id"),
                        "pre_ai_status": judge_result.decision,
                        "pre_ai_score": judge_result.relevance_score,
                        "judge_decision": judge_result.decision,
                        "judge_relevance_score": judge_result.relevance_score,
                        "judge_confidence_score": judge_result.confidence_score,
                        "judge_reason_codes": judge_result.reason_codes,
                        "query_family": entry.get("query_family") or fallback_score.query_family,
                        "query_text": raw.get("query_text") or "",
                    }
                )
            session.commit()
            duplicate_count = duplicate_in_batch + duplicate_in_run
            return inserted_count, duplicate_count, persisted_refs

    def _get_retrieval_profile_for_run(self, run_id: str) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                return {}
            plan = session.get(Plan, run.plan_id)
            if plan is None:
                return {}
            context = session.get(ProductContext, plan.context_id)
            if context is None or not context.retrieval_profile_json:
                return {}
            try:
                return json.loads(context.retrieval_profile_json)
            except json.JSONDecodeError:
                return {}

    def _get_validity_spec_for_run(self, run_id: str) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                return {}
            plan = session.get(Plan, run.plan_id)
            if plan is None:
                return {}
            context = session.get(ProductContext, plan.context_id)
            if context is None or not context.validity_spec_json:
                return {}
            try:
                return json.loads(context.validity_spec_json)
            except json.JSONDecodeError:
                return {}

    def _load_parent_context_map(self, run_id: str) -> dict[str, dict[str, str]]:
        with SessionLocal() as session:
            posts = session.scalars(select(CrawledPost).where(CrawledPost.run_id == run_id)).all()
        context_map: dict[str, dict[str, str]] = {}
        for post in posts:
            payload = {
                "content": post.content_masked or post.content,
                "status": post.judge_decision or post.pre_ai_status or "ACCEPTED",
            }
            context_map[post.post_id] = payload
            if post.source_url:
                context_map[post.source_url] = payload
        return context_map

    def _allows_uncertain(self) -> bool:
        return str(getattr(self._settings, "pre_ai_mode", "strict")).lower() == "balanced"

    def _build_run_scoped_post_id(self, session: Any, run_id: str, post_id: str) -> str:
        run_suffix = run_id.removeprefix("run-")[:10]
        candidate = f"{post_id}--{run_suffix}"
        attempt = 1
        while session.get(CrawledPost, candidate) is not None:
            candidate = f"{post_id}--{run_suffix}-{attempt}"
            attempt += 1
        return candidate

    async def _emit(self, run_id: str, event: str, payload: dict[str, Any]) -> None:
        self._history.setdefault(run_id, []).append((event, payload))
        for queue in list(self._subscribers.get(run_id, [])):
            await queue.put((event, payload))
