from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select

from app.infrastructure.config import Settings
from app.infrastructure.database import SessionLocal
from app.models.content_label import ContentLabel
from app.models.crawled_post import CrawledPost
from app.models.label_job import LabelJob
from app.models.run import PlanRun
from app.services.content_labeling import ContentLabelingService
from app.services.health_monitor import utc_now_iso
from app.services.run_closeout import RunCloseoutService

NO_ELIGIBLE_RECORDS_STATUS = "NO_ELIGIBLE_RECORDS"


class LabelJobService:
    def __init__(
        self,
        content_labeling_service: ContentLabelingService,
        settings: Settings,
        closeout_service: RunCloseoutService | None = None,
    ) -> None:
        self._content_labeling_service = content_labeling_service
        self._settings = settings
        self._closeout_service = closeout_service
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def ensure_job_for_run(self, run_id: str, *, auto_start: bool = False) -> dict[str, Any]:
        should_closeout_no_eligible = False
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            total_records = self.count_eligible_records(run_id, session=session)
            if total_records == 0:
                if self._closeout_service is None:
                    run.answer_status = NO_ELIGIBLE_RECORDS_STATUS
                    run.answer_generated_at = None
                    session.add(run)
                    session.commit()
                else:
                    should_closeout_no_eligible = True
        if should_closeout_no_eligible:
            await self._closeout_service.ensure_no_answer_closeout_for_run(
                run_id,
                outcome_type=NO_ELIGIBLE_RECORDS_STATUS,
                warning="No eligible records remained after pre-AI gating. Labeling was skipped.",
            )
            return self._build_no_eligible_summary(run_id)
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            total_records = self.count_eligible_records(run_id, session=session)
            job = session.scalars(
                select(LabelJob)
                .where(
                    LabelJob.run_id == run_id,
                    LabelJob.taxonomy_version == self._settings.label_taxonomy_version,
                )
                .order_by(LabelJob.created_at.desc())
            ).first()
            if job is None:
                job = LabelJob(
                    label_job_id=f"label-job-{uuid4().hex[:10]}",
                    run_id=run_id,
                    taxonomy_version=self._settings.label_taxonomy_version,
                    model_name=self._settings.content_labeling_model,
                    status="PENDING",
                    records_total=total_records,
                )
                session.add(job)
                session.commit()
            label_job_id = job.label_job_id
        if auto_start:
            await self.start_job(label_job_id)
        return self.get_summary(run_id)

    async def start_job(self, label_job_id: str) -> dict[str, Any]:
        with SessionLocal() as session:
            job = session.get(LabelJob, label_job_id)
            if job is None:
                raise ValueError("label job not found")
            if job.status == "RUNNING" and label_job_id in self._tasks:
                return self.get_summary(job.run_id)
            if job.status in {"DONE", "PARTIAL"}:
                return self.get_summary(job.run_id)
            job.status = "PENDING"
            session.add(job)
            session.commit()
            run_id = job.run_id

        task = asyncio.create_task(self._run_job(label_job_id))
        self._tasks[label_job_id] = task
        return self.get_summary(run_id)

    def get_summary(self, run_id: str) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            total_records = self.count_eligible_records(run_id, session=session)
            latest_job = session.scalars(
                select(LabelJob).where(LabelJob.run_id == run_id).order_by(LabelJob.created_at.desc())
            ).first()
            if latest_job is None and total_records == 0:
                return self._build_no_eligible_summary(run_id)
            current_labels = session.scalars(
                select(ContentLabel)
                .join(CrawledPost, CrawledPost.current_label_id == ContentLabel.label_id)
                .where(CrawledPost.run_id == run_id)
            ).all()

        counts = Counter(label.author_role for label in current_labels)
        payload = {
            "run_id": run_id,
            "label_job_id": latest_job.label_job_id if latest_job else None,
            "status": latest_job.status if latest_job else "NOT_STARTED",
            "taxonomy_version": latest_job.taxonomy_version if latest_job else self._settings.label_taxonomy_version,
            "records_total": latest_job.records_total if latest_job else total_records,
            "records_labeled": latest_job.records_labeled if latest_job else 0,
            "records_fallback": latest_job.records_fallback if latest_job else 0,
            "records_failed": latest_job.records_failed if latest_job else 0,
            "counts_by_author_role": dict(counts),
            "warning": None,
        }
        if payload["status"] in {"RUNNING", "PENDING"}:
            payload["warning"] = "Labeling is still in progress. Theme filters may shift as more records are classified."
        return payload

    def get_closeout_summary(self, run_id: str) -> dict[str, Any] | None:
        if self._closeout_service is None:
            return None
        return self._closeout_service.get_summary(run_id)

    async def wait_for_run(self, run_id: str) -> dict[str, Any]:
        summary = self.get_summary(run_id)
        label_job_id = summary.get("label_job_id")
        if label_job_id and label_job_id in self._tasks:
            await self._tasks[label_job_id]
            summary = self.get_summary(run_id)
        return {
            "label_summary": summary,
            "closeout_summary": self.get_closeout_summary(run_id),
        }

    def count_eligible_records(self, run_id: str, *, session=None) -> int:
        if session is not None:
            return session.scalar(
                select(func.count()).select_from(CrawledPost).where(
                    CrawledPost.run_id == run_id,
                    self._eligible_condition(),
                )
            ) or 0
        with SessionLocal() as local_session:
            return self.count_eligible_records(run_id, session=local_session)

    def _build_no_eligible_summary(self, run_id: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "label_job_id": None,
            "status": NO_ELIGIBLE_RECORDS_STATUS,
            "taxonomy_version": self._settings.label_taxonomy_version,
            "records_total": 0,
            "records_labeled": 0,
            "records_fallback": 0,
            "records_failed": 0,
            "counts_by_author_role": {},
            "warning": "No eligible records remained after pre-AI gating. Labeling was skipped.",
        }

    def get_record_samples(self, run_id: str, *, label_filter: str | None = None, limit: int = 20) -> dict[str, Any]:
        with SessionLocal() as session:
            run = session.get(PlanRun, run_id)
            if run is None:
                raise ValueError("run not found")
            posts = session.scalars(
                select(CrawledPost)
                .where(CrawledPost.run_id == run_id)
                .order_by(CrawledPost.crawled_at.asc())
            ).all()
            labels = {
                label.label_id: label
                for label in session.scalars(
                    select(ContentLabel).where(ContentLabel.run_id == run_id, ContentLabel.is_current.is_(True))
                ).all()
            }

        samples = []
        for post in posts:
            label = labels.get(post.current_label_id or "")
            if label_filter and label_filter != "excluded" and (label is None or label.author_role != label_filter):
                continue
            if label_filter == "excluded" and (
                label is None or (label.author_role == "end_user" and label.user_feedback_relevance != "low")
            ):
                continue
            samples.append(
                {
                    "post_id": post.post_id,
                    "record_type": post.record_type,
                    "content": post.content_masked,
                    "source_url": post.source_url,
                    "label": None
                    if label is None
                    else {
                        "author_role": label.author_role,
                        "content_intent": label.content_intent,
                        "commerciality_level": label.commerciality_level,
                        "user_feedback_relevance": label.user_feedback_relevance,
                        "label_confidence": label.label_confidence,
                        "label_reason": label.label_reason,
                        "label_source": label.label_source,
                    },
                }
            )
            if len(samples) >= max(1, min(limit, 50)):
                break
        return {"run_id": run_id, "label_filter": label_filter, "records": samples}

    def _eligible_condition(self):
        judge_status = func.coalesce(CrawledPost.judge_decision, CrawledPost.pre_ai_status)
        if self._settings.pre_ai_mode.lower() == "balanced":
            return or_(
                judge_status.is_(None),
                judge_status.in_(("ACCEPTED", "UNCERTAIN")),
            )
        return or_(
            judge_status.is_(None),
            judge_status == "ACCEPTED",
        )

    async def resume_incomplete_jobs(self) -> None:
        with SessionLocal() as session:
            pending_job_ids = [
                job_id
                for job_id in session.scalars(
                    select(LabelJob.label_job_id).where(LabelJob.status.in_(("PENDING", "RUNNING")))
                ).all()
            ]
        for label_job_id in pending_job_ids:
            await self.start_job(label_job_id)

    async def _run_job(self, label_job_id: str) -> None:
        try:
            run_id: str | None = None
            with SessionLocal() as session:
                job = session.get(LabelJob, label_job_id)
                if job is None:
                    return
                run_id = job.run_id
                job.status = "RUNNING"
                job.started_at = job.started_at or utc_now_iso()
                session.add(job)
                session.commit()
            await self._content_labeling_service.process_job(label_job_id)
            if self._closeout_service is not None and run_id:
                with SessionLocal() as session:
                    job = session.get(LabelJob, label_job_id)
                    if job is not None and job.status in {"DONE", "PARTIAL"}:
                        await self._closeout_service.ensure_closeout_for_run(run_id)
        finally:
            self._tasks.pop(label_job_id, None)
