from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infra.event_bus import EventBus, HealthSignal
from app.models import Base
from app.models.health import AccountHealthState
from app.services.health_monitor import HealthMonitorService


class HealthMonitorPhase13Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "phase13-health.db"
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_session_expired_never_remains_healthy_and_runnable(self) -> None:
        service = HealthMonitorService(asyncio.Queue(), EventBus())
        with patch("app.services.health_monitor.SessionLocal", self.session_local):
            with self.session_local() as session:
                session.add(
                    AccountHealthState(
                        id=1,
                        status="HEALTHY",
                        session_status="VALID",
                        account_id_hash="account",
                    )
                )
                session.commit()

            await service.process_signal(HealthSignal(signal_type="SESSION_EXPIRED"))
            browser_state = service.get_browser_runtime_state()

        self.assertEqual(browser_state.session_status, "EXPIRED")
        self.assertEqual(browser_state.health_status, "CAUTION")
        self.assertFalse(browser_state.runnable)
        self.assertEqual(browser_state.action_required, "REAUTH_REQUIRED")

