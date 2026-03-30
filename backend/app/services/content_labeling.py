from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.domain.label_taxonomy import TAXONOMY_VERSION, coerce_label_payload
from app.infra.ai_client import AIClient
from app.infrastructure.config import Settings
from app.infrastructure.database import SessionLocal
from app.models.content_label import ContentLabel
from app.models.crawled_post import CrawledPost
from app.models.label_job import LabelJob
from app.services.health_monitor import utc_now_iso
from app.services.labeling_heuristics import classify_content, fallback_label


class ContentLabelingService:
    def __init__(self, ai_client: AIClient, settings: Settings) -> None:
        self._ai_client = ai_client
        self._settings = settings
        self._prompt_path = Path(__file__).resolve().parents[1] / "skills" / "content_labeling.md"

    async def process_job(self, label_job_id: str) -> None:
        with SessionLocal() as session:
            job = session.get(LabelJob, label_job_id)
            if job is None:
                raise ValueError("label job not found")
            db_posts = session.scalars(
                select(CrawledPost)
                .where(CrawledPost.run_id == job.run_id)
                    .order_by(CrawledPost.crawled_at.asc(), CrawledPost.post_id.asc())
            ).all()
            db_posts = [post for post in db_posts if self._is_ai_eligible(post)]
            posts = [
                {
                    "post_id": post.post_id,
                    "record_type": post.record_type,
                    "content": post.content,
                    "content_masked": post.content_masked,
                    "source_url": post.source_url,
                    "parent_post_id": post.parent_post_id,
                    "crawled_at": post.crawled_at,
                }
                for post in db_posts
            ]
            if not posts:
                job.status = "FAILED"
                job.error_message = "run has no crawled posts"
                job.ended_at = utc_now_iso()
                session.add(job)
                session.commit()
                return
            job.status = "RUNNING"
            job.started_at = job.started_at or utc_now_iso()
            job.records_total = len(posts)
            session.add(job)
            session.commit()

        parent_map = self._build_parent_map(posts)
        totals = {"labeled": 0, "fallback": 0, "failed": 0}
        prompt = self._prompt_path.read_text(encoding="utf-8")
        batch_size = max(1, int(self._settings.label_batch_size))

        try:
            for offset in range(0, len(posts), batch_size):
                batch = posts[offset : offset + batch_size]
                prepared = []
                direct_labels: dict[str, dict[str, object]] = {}
                ai_candidates = []

                for post in batch:
                    parent_summary = parent_map.get(str(post.get("parent_post_id") or ""))
                    heuristic = classify_content(
                        record_type=str(post["record_type"]),
                        content=str(post.get("content_masked") or post.get("content") or ""),
                        parent_summary=parent_summary,
                        source_url=str(post.get("source_url") or ""),
                    )
                    prepared.append((post, parent_summary))
                    if heuristic.should_skip_ai:
                        direct_labels[str(post["post_id"])] = dict(heuristic.payload)
                    else:
                        ai_candidates.append(
                            {
                                "post_id": post["post_id"],
                                "record_type": post["record_type"],
                                "content": str(post.get("content_masked") or post.get("content") or "")[:900],
                                "source_url": post.get("source_url"),
                                "parent_post_id": post.get("parent_post_id"),
                                "parent_post_summary": parent_summary,
                                "signals": heuristic.signals,
                                "heuristic_prior": heuristic.payload,
                            }
                        )

                ai_labels = await self._label_with_ai(prompt, ai_candidates) if ai_candidates else {}

                with SessionLocal() as session:
                    job = session.get(LabelJob, label_job_id)
                    if job is None:
                        raise ValueError("label job not found")
                    for post, _parent_summary in prepared:
                        post_id = str(post["post_id"])
                        raw_payload = direct_labels.get(post_id) or ai_labels.get(post_id)
                        if raw_payload is None:
                            raw_payload = fallback_label("ai_missing_record_output")
                        payload = coerce_label_payload(raw_payload)
                        if payload["taxonomy_version"] != job.taxonomy_version:
                            payload["taxonomy_version"] = job.taxonomy_version
                        label_source = str(payload["label_source"])
                        self._persist_label(session, job, post_id, payload)
                        totals["labeled"] += 1
                        if label_source == "fallback":
                            totals["fallback"] += 1
                    job.records_labeled = totals["labeled"]
                    job.records_fallback = totals["fallback"]
                    job.records_failed = totals["failed"]
                    session.add(job)
                    session.commit()
        except Exception as exc:
            with SessionLocal() as session:
                job = session.get(LabelJob, label_job_id)
                if job is not None:
                    job.status = "FAILED"
                    job.error_message = str(exc)
                    job.ended_at = utc_now_iso()
                    job.records_labeled = totals["labeled"]
                    job.records_fallback = totals["fallback"]
                    job.records_failed = totals["failed"]
                    session.add(job)
                    session.commit()
            raise

        with SessionLocal() as session:
            job = session.get(LabelJob, label_job_id)
            if job is None:
                raise ValueError("label job not found")
            job.ended_at = utc_now_iso()
            job.records_labeled = totals["labeled"]
            job.records_fallback = totals["fallback"]
            job.records_failed = totals["failed"]
            job.status = "PARTIAL" if totals["failed"] > 0 or totals["fallback"] > 0 else "DONE"
            session.add(job)
            session.commit()

    async def _label_with_ai(self, prompt: str, records: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        if not records:
            return {}
        response = await self._ai_client.call(
            model=self._settings.content_labeling_model,
            system_prompt=prompt,
            user_input=json.dumps(
                {
                    "taxonomy_version": self._settings.label_taxonomy_version or TAXONOMY_VERSION,
                    "records": records,
                },
                ensure_ascii=False,
            ),
        )
        labeled_records = response.get("records")
        if not isinstance(labeled_records, list):
            return {}
        results: dict[str, dict[str, object]] = {}
        provider_meta = response.get("_provider_meta") if isinstance(response, dict) else None
        for item in labeled_records:
            if not isinstance(item, dict):
                continue
            post_id = str(item.get("post_id") or "").strip()
            if post_id:
                if provider_meta and not item.get("model_name"):
                    item["model_name"] = str(provider_meta.get("provider_used") or self._settings.content_labeling_model)
                results[post_id] = item
        return results

    def _is_ai_eligible(self, post: CrawledPost) -> bool:
        status = (post.pre_ai_status or "").upper()
        if not status:
            return True
        if status == "ACCEPTED":
            return True
        if status == "UNCERTAIN":
            return self._settings.pre_ai_mode.lower() == "balanced"
        return False

    def _persist_label(self, session, job: LabelJob, post_id: str, payload: dict[str, object]) -> None:
        post = session.get(CrawledPost, post_id)
        if post is None:
            return
        if post.current_label_id:
            current = session.get(ContentLabel, post.current_label_id)
            if current is not None:
                current.is_current = False
                session.add(current)

        label_id = f"label-{uuid4().hex[:12]}"
        label = ContentLabel(
            label_id=label_id,
            post_id=post_id,
            run_id=job.run_id,
            label_job_id=job.label_job_id,
            taxonomy_version=str(payload["taxonomy_version"]),
            author_role=str(payload["author_role"]),
            content_intent=str(payload["content_intent"]),
            commerciality_level=str(payload["commerciality_level"]),
            user_feedback_relevance=str(payload["user_feedback_relevance"]),
            label_confidence=float(payload["label_confidence"]),
            label_reason=str(payload["label_reason"]),
            label_source=str(payload["label_source"]),
            model_name=str(payload["model_name"]) if payload.get("model_name") else None,
            model_version=str(payload["model_version"]) if payload.get("model_version") else None,
            is_current=True,
        )
        session.add(label)
        post.current_label_id = label_id
        post.label_status = "FALLBACK" if label.label_source == "fallback" else "LABELED"
        session.add(post)

    def _build_parent_map(self, posts: list[dict[str, str | None]]) -> dict[str, str]:
        parent_map: dict[str, str] = {}
        for post in posts:
            if post["record_type"] == "POST":
                parent_map[str(post["post_id"])] = str(post.get("content_masked") or post.get("content") or "")[:240]
        return parent_map
