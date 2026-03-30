from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import delete, select

from app.domain.label_taxonomy import TAXONOMY_VERSION
from app.infra.ai_client import AIClient
from app.infra.pii_masker import PIIMasker
from app.infrastructure.config import Settings
from app.infrastructure.database import SessionLocal
from app.models.content_label import ContentLabel
from app.models.crawled_post import CrawledPost
from app.models.theme_result import ThemeResult
from app.services.audience_filter import AudienceFilterPolicy


class InsightService:
    def __init__(self, ai_client: AIClient, settings: Settings) -> None:
        self._ai_client = ai_client
        self._settings = settings
        self._pii_masker = PIIMasker()
        self._policy = AudienceFilterPolicy()

    async def analyze_themes(self, run_id: str, prompt: str, audience_filter: str | None = None) -> dict:
        normalized_filter = self._policy.normalize(audience_filter)
        with SessionLocal() as session:
            posts = session.scalars(
                select(CrawledPost).where(CrawledPost.run_id == run_id).order_by(CrawledPost.crawled_at.asc())
            ).all()
            labels = {
                label.label_id: label
                for label in session.scalars(
                    select(ContentLabel).where(ContentLabel.run_id == run_id, ContentLabel.is_current.is_(True))
                ).all()
            }
            if not posts:
                raise ValueError("run has no crawled posts")

        clean_posts, excluded_ids, excluded_breakdown = self._filter_records(posts, labels, normalized_filter)
        warning = "It hon 10 posts nen theme chi mang tinh dai dien." if len(clean_posts) < 10 else None
        ai_response = await self._ai_client.call(
            model=self._settings.theme_analysis_model,
            system_prompt=prompt,
            user_input=json.dumps({"posts": [post.content for post in clean_posts]}),
        )
        themes = ai_response.get("themes", [])

        with SessionLocal() as session:
            session.execute(delete(ThemeResult).where(ThemeResult.run_id == run_id))
            persisted = []
            for theme in themes:
                sample_quotes = [self._pii_masker.mask(quote) for quote in theme.get("sample_quotes", [])][:3]
                row = ThemeResult(
                    theme_id=f"theme-{uuid4().hex[:10]}",
                    run_id=run_id,
                    label=theme["label"],
                    dominant_sentiment=theme["dominant_sentiment"],
                    post_count=theme["post_count"],
                    sample_quotes=json.dumps(sample_quotes, ensure_ascii=False),
                )
                session.add(row)
                persisted.append(row)
            session.commit()
            for row in persisted:
                session.refresh(row)

        with SessionLocal() as session:
            persisted = session.scalars(
                select(ThemeResult).where(ThemeResult.run_id == run_id).order_by(ThemeResult.post_count.desc())
            ).all()
            posts = session.scalars(select(CrawledPost).where(CrawledPost.run_id == run_id)).all()
            labels = {
                label.label_id: label
                for label in session.scalars(
                    select(ContentLabel).where(ContentLabel.run_id == run_id, ContentLabel.is_current.is_(True))
                ).all()
            }
            response = self._build_response(
                run_id,
                posts,
                persisted,
                labels=labels,
                audience_filter=normalized_filter,
                excluded_ids=excluded_ids,
                excluded_breakdown=excluded_breakdown,
            )
            response["warning"] = warning
            return response

    def _filter_records(
        self,
        posts: list[CrawledPost],
        labels: dict[str, ContentLabel],
        audience_filter: str,
    ) -> tuple[list[CrawledPost], set[str], dict[str, int]]:
        clean_posts: list[CrawledPost] = []
        excluded_ids: set[str] = set()
        excluded_breakdown: dict[str, int] = {}
        for post in posts:
            if not self._is_theme_eligible(post):
                excluded_ids.add(post.post_id)
                excluded_breakdown["pre_ai_rejected"] = excluded_breakdown.get("pre_ai_rejected", 0) + 1
                continue
            label = labels.get(post.current_label_id or "")
            include, reason = self._policy.include(audience_filter, label)
            if not include:
                excluded_ids.add(post.post_id)
                key = reason or "excluded"
                excluded_breakdown[key] = excluded_breakdown.get(key, 0) + 1
                continue
            clean_posts.append(post)
        return clean_posts, excluded_ids, excluded_breakdown

    def _is_theme_eligible(self, post: CrawledPost) -> bool:
        status = (post.pre_ai_status or "").upper()
        if not status:
            return True
        if status == "ACCEPTED":
            return True
        if status == "UNCERTAIN":
            return self._settings.pre_ai_mode.lower() == "balanced"
        return False

    def _build_response(
        self,
        run_id: str,
        posts: list[CrawledPost],
        themes: list[ThemeResult],
        *,
        labels: dict[str, ContentLabel],
        audience_filter: str,
        excluded_ids: set[str],
        excluded_breakdown: dict[str, int],
    ) -> dict:
        excluded_count = len(excluded_ids)
        clean_count = len(posts)
        taxonomy_version = TAXONOMY_VERSION
        for label in labels.values():
            taxonomy_version = label.taxonomy_version
            break
        payload = {
            "run_id": run_id,
            "audience_filter": audience_filter,
            "taxonomy_version": taxonomy_version,
            "posts_crawled": clean_count,
            "posts_included": clean_count - excluded_count,
            "posts_excluded": excluded_count,
            "excluded_by_label_count": excluded_count,
            "excluded_breakdown": excluded_breakdown,
            "themes": [
                {
                    "theme_id": theme.theme_id,
                    "label": theme.label,
                    "dominant_sentiment": theme.dominant_sentiment,
                    "post_count": theme.post_count,
                    "sample_quotes": json.loads(theme.sample_quotes or "[]"),
                }
                for theme in themes
            ],
            "warning": None,
        }
        if clean_count - excluded_count < 10:
            payload["warning"] = "It hon 10 posts nen theme chi mang tinh dai dien."
        return payload
