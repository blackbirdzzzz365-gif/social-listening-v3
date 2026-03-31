from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.infrastructure.config import Settings
from app.infrastructure.database import SessionLocal
from app.models.run import PlanRun
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
                "theme_count": int(theme_count),
            }

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
                session.add(run)
                session.commit()

        return {
            "run_id": run_id,
            "answer_status": answer_status,
            "answer_generated_at": generated_at,
            "theme_count": len(themes),
            "warning": result.get("warning"),
        }
