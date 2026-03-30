import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.browser import BrowserSetupHub
from app.infra.pii_masker import PIIMasker
from app.infra.ai_client import AIClient
from app.infra.browser_agent import BrowserAgent
from app.infra.event_bus import EventBus, HealthSignal
from app.infrastructure.config import Settings
from app.services.approval import ApprovalService
from app.services.content_labeling import ContentLabelingService
from app.services.health_monitor import HealthMonitorService
from app.services.insight import InsightService
from app.services.label_job_service import LabelJobService
from app.services.planner import PlannerService
from app.services.runner import RunnerService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_factory(app: FastAPI, settings: Settings) -> AsyncIterator[None]:
    logger.info(
        "Starting %s %s in %s",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    browser_event_queue: asyncio.Queue[HealthSignal] = asyncio.Queue()
    app.state.event_bus = EventBus()
    app.state.browser_setup_hub = BrowserSetupHub()
    app.state.browser_event_queue = browser_event_queue
    app.state.browser_agent = BrowserAgent(browser_event_queue, settings)
    app.state.health_monitor = HealthMonitorService(browser_event_queue, app.state.event_bus)
    app.state.ai_client = AIClient(settings)
    app.state.pii_masker = PIIMasker()
    app.state.planner_service = PlannerService(app.state.ai_client, settings)
    app.state.approval_service = ApprovalService(app.state.health_monitor)
    app.state.content_labeling_service = ContentLabelingService(app.state.ai_client, settings)
    app.state.label_job_service = LabelJobService(app.state.content_labeling_service, settings)
    app.state.runner_service = RunnerService(
        app.state.browser_agent,
        app.state.health_monitor,
        app.state.label_job_service,
        settings,
    )
    app.state.insight_service = InsightService(app.state.ai_client, settings)
    app.state.browser_setup_task = None
    await app.state.health_monitor.start()
    await app.state.label_job_service.resume_incomplete_jobs()
    persisted_account_hash = app.state.browser_agent.load_persisted_account_hash()
    if persisted_account_hash:
        app.state.health_monitor.mark_session_valid(persisted_account_hash)
    yield
    await app.state.browser_agent.stop()
    await app.state.health_monitor.stop()
    logger.info("Stopping %s", settings.app_name)


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with lifespan_factory(app, settings):
            yield

    return lifespan
