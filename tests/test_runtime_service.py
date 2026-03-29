from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.alerts.notifier import AlertNotifier
from xauusd_ai_system.config.schema import NotificationConfig, SystemConfig
from xauusd_ai_system.core.models import AccountState, MarketSnapshot
from xauusd_ai_system.core.pipeline import TradingSystem
from xauusd_ai_system.execution.base import ExecutionOrder, ExecutionResult
from xauusd_ai_system.runtime.service import TradingRuntimeService
from xauusd_ai_system.storage.sqlite_repository import SQLiteAuditRepository


class StubExecutionService:
    def build_order(self, signal, risk):
        return ExecutionOrder(
            platform="mt5",
            symbol="XAUUSD",
            volume=risk.position_size,
            payload={"symbol": "XAUUSD", "volume": risk.position_size},
        )

    def submit_order(self, order):
        return ExecutionResult(
            accepted=True,
            platform="mt5",
            order_id="123456",
            raw_response={"retcode": "DONE"},
        )


class RuntimeServiceTests(unittest.TestCase):
    def test_process_snapshot_persists_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "audit.db"
            repo = SQLiteAuditRepository(f"sqlite:///{db_path}")
            service = TradingRuntimeService(
                TradingSystem(SystemConfig()),
                repo,
                AlertNotifier(),
                NotificationConfig(enabled=False),
            )

            snapshot = MarketSnapshot(
                timestamp=datetime(2026, 3, 29, 15, 0),
                symbol="XAUUSD",
                bid=3062.8,
                ask=3063.0,
                open=3062.0,
                high=3063.1,
                low=3061.8,
                close=3062.9,
                session_tag="us",
                features={
                    "atr_m1_14": 0.8,
                    "breakout_distance": 0.42,
                    "ema20_m5": 3061.8,
                    "ema60_m5": 3061.2,
                    "ema_slope_20": 0.11,
                    "false_break_count": 1,
                    "spread_ratio": 1.38,
                    "volatility_ratio": 1.28,
                    "atr_expansion_ratio": 1.42,
                    "breakout_retest_confirmed": True,
                    "structural_stop_distance": 1.1,
                    "tick_speed": 1.24,
                    "breakout_pressure": 0.33,
                },
            )
            account_state = AccountState(equity=10_000.0)

            decision = service.process_snapshot(snapshot, account_state)
            service.shutdown()

            connection = sqlite3.connect(db_path)
            row = connection.execute(
                "SELECT symbol, state_label, volatility_level, risk_allowed FROM evaluations"
            ).fetchone()
            connection.close()

            self.assertEqual(row[0], "XAUUSD")
            self.assertEqual(row[1], "trend_breakout")
            self.assertIsNotNone(row[2])
            self.assertEqual(row[3], int(decision.risk.allowed))

    def test_process_snapshot_persists_execution_attempt_when_live_execution_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "audit.db"
            repo = SQLiteAuditRepository(f"sqlite:///{db_path}")
            service = TradingRuntimeService(
                TradingSystem(SystemConfig()),
                repo,
                AlertNotifier(),
                NotificationConfig(enabled=False),
                execution_service=StubExecutionService(),
                dry_run=False,
            )

            snapshot = MarketSnapshot(
                timestamp=datetime(2026, 3, 29, 15, 0),
                symbol="XAUUSD",
                bid=3062.8,
                ask=3063.0,
                open=3062.0,
                high=3063.1,
                low=3061.8,
                close=3062.9,
                session_tag="us",
                features={
                    "atr_m1_14": 0.8,
                    "breakout_distance": 0.42,
                    "ema20_m5": 3061.8,
                    "ema60_m5": 3061.2,
                    "ema_slope_20": 0.11,
                    "false_break_count": 1,
                    "spread_ratio": 1.38,
                    "volatility_ratio": 1.28,
                    "atr_expansion_ratio": 1.42,
                    "breakout_retest_confirmed": True,
                    "structural_stop_distance": 1.1,
                    "tick_speed": 1.24,
                    "breakout_pressure": 0.33,
                },
            )
            account_state = AccountState(equity=10_000.0)

            service.process_snapshot(snapshot, account_state)
            service.shutdown()

            connection = sqlite3.connect(db_path)
            row = connection.execute(
                """
                SELECT symbol, platform, accepted, order_id
                FROM execution_attempts
                """
            ).fetchone()
            connection.close()

            self.assertEqual(row[0], "XAUUSD")
            self.assertEqual(row[1], "mt5")
            self.assertEqual(row[2], 1)
            self.assertEqual(row[3], "123456")


if __name__ == "__main__":
    unittest.main()
