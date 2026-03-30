from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.alerts.notifier import AlertNotifier
from xauusd_ai_system.config.schema import NotificationConfig, SystemConfig
from xauusd_ai_system.core.enums import MarketState
from xauusd_ai_system.core.models import AccountState, MarketSnapshot, RiskDecision, StateDecision
from xauusd_ai_system.core.models import TradingDecision
from xauusd_ai_system.core.pipeline import TradingSystem
from xauusd_ai_system.execution.base import (
    ExecutionOrder,
    ExecutionResult,
    ExecutionSyncResult,
)
from xauusd_ai_system.runtime.service import TradingRuntimeService
from xauusd_ai_system.storage.sqlite_repository import SQLiteAuditRepository


class StubExecutionService:
    def __init__(self, *, reconcile_result: ExecutionSyncResult | None = None) -> None:
        self.reconcile_result = reconcile_result
        self.reconcile_calls: list[str] = []

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

    def sync_execution_state(self, *, order, execution_result):
        return ExecutionSyncResult(
            platform="mt5",
            symbol=order.symbol,
            requested_order_id=execution_result.order_id,
            accepted=execution_result.accepted,
            sync_status="position_open",
            requested_price=3062.90,
            observed_price=3062.84,
            observed_price_source="position_open",
            position_ticket="90001",
            position_identifier="880001",
            history_order_state="order_state_filled",
            history_deal_ticket="777001",
            history_deal_entry="deal_entry_in",
            history_deal_reason="deal_reason_expert",
            price_offset=-0.06,
            adverse_slippage=0.06,
            adverse_slippage_points=6.0,
            open_orders=[],
            open_positions=[
                {
                    "ticket": 90001,
                    "symbol": order.symbol,
                    "volume": order.volume,
                }
            ],
            history_orders=[
                {
                    "ticket": execution_result.order_id,
                    "symbol": order.symbol,
                    "price_open": 3062.90,
                }
            ],
            history_deals=[
                {
                    "ticket": 777001,
                    "order": execution_result.order_id,
                    "symbol": order.symbol,
                    "price": 3062.84,
                }
            ],
        )

    def reconcile_execution_state(self, *, symbol):
        self.reconcile_calls.append(symbol)
        return self.reconcile_result


class StubNoSignalSystem:
    def evaluate(self, snapshot, account_state):
        return TradingDecision(
            state=StateDecision(
                state_label=MarketState.NO_TRADE,
                confidence_score=1.0,
                reason_codes=["RECONCILE_ONLY"],
            ),
            volatility=None,
            signal=None,
            risk=RiskDecision(
                allowed=False,
                risk_reason=["RECONCILE_ONLY"],
                position_size=0.0,
            ),
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
            sync_row = connection.execute(
                """
                SELECT
                    symbol,
                    platform,
                    accepted,
                    requested_order_id,
                    sync_status,
                    open_position_count,
                    payload_json
                FROM execution_syncs
                """
            ).fetchone()
            connection.close()

            self.assertEqual(row[0], "XAUUSD")
            self.assertEqual(row[1], "mt5")
            self.assertEqual(row[2], 1)
            self.assertEqual(row[3], "123456")
            self.assertEqual(sync_row[0], "XAUUSD")
            self.assertEqual(sync_row[1], "mt5")
            self.assertEqual(sync_row[2], 1)
            self.assertEqual(sync_row[3], "123456")
            self.assertEqual(sync_row[4], "position_open")
            self.assertEqual(sync_row[5], 1)
            payload = json.loads(sync_row[6])
            self.assertEqual(payload["sync_result"]["requested_price"], 3062.9)
            self.assertEqual(payload["sync_result"]["observed_price"], 3062.84)
            self.assertEqual(payload["sync_result"]["observed_price_source"], "position_open")
            self.assertEqual(payload["sync_result"]["position_ticket"], "90001")
            self.assertEqual(payload["sync_result"]["position_identifier"], "880001")
            self.assertEqual(payload["sync_result"]["history_order_state"], "order_state_filled")
            self.assertEqual(payload["sync_result"]["history_deal_ticket"], "777001")
            self.assertEqual(payload["sync_result"]["history_deal_entry"], "deal_entry_in")
            self.assertEqual(payload["sync_result"]["history_deal_reason"], "deal_reason_expert")
            self.assertEqual(payload["sync_result"]["price_offset"], -0.06)
            self.assertEqual(payload["sync_result"]["adverse_slippage"], 0.06)
            self.assertEqual(payload["sync_result"]["adverse_slippage_points"], 6.0)
            self.assertEqual(len(payload["sync_result"]["history_orders"]), 1)
            self.assertEqual(len(payload["sync_result"]["history_deals"]), 1)

    def test_process_snapshot_persists_reconcile_sync_once_per_state_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "audit.db"
            repo = SQLiteAuditRepository(f"sqlite:///{db_path}")
            execution_service = StubExecutionService(
                reconcile_result=ExecutionSyncResult(
                    platform="mt5",
                    symbol="XAUUSD",
                    requested_order_id="123456",
                    accepted=True,
                    sync_status="position_closed_tp",
                    sync_origin="reconcile",
                    observed_price=3059.8,
                    observed_price_source="history_deal",
                    position_identifier="880001",
                    history_order_state="order_state_filled",
                    history_deal_ticket="777002",
                    history_deal_entry="deal_entry_out",
                    history_deal_reason="deal_reason_tp",
                    open_orders=[],
                    open_positions=[],
                    history_orders=[
                        {
                            "ticket": 123456,
                            "symbol": "XAUUSD",
                            "position_id": 880001,
                            "state": "order_state_filled",
                        }
                    ],
                    history_deals=[
                        {
                            "ticket": 777002,
                            "order": 123456,
                            "symbol": "XAUUSD",
                            "position_id": 880001,
                            "entry": "deal_entry_out",
                            "reason": "deal_reason_tp",
                            "price": 3059.8,
                        }
                    ],
                )
            )
            service = TradingRuntimeService(
                StubNoSignalSystem(),
                repo,
                AlertNotifier(),
                NotificationConfig(enabled=False),
                execution_service=execution_service,
                dry_run=False,
            )

            snapshot = MarketSnapshot(
                timestamp=datetime(2026, 3, 29, 15, 5),
                symbol="XAUUSD",
                bid=3060.0,
                ask=3060.2,
                open=3060.1,
                high=3060.4,
                low=3059.7,
                close=3060.0,
                session_tag="us",
                features={},
            )
            account_state = AccountState(equity=10_000.0)

            service.process_snapshot(snapshot, account_state)
            service.process_snapshot(snapshot, account_state)
            service.shutdown()

            connection = sqlite3.connect(db_path)
            sync_rows = connection.execute(
                """
                SELECT sync_status, payload_json
                FROM execution_syncs
                ORDER BY id
                """
            ).fetchall()
            execution_attempt_count = connection.execute(
                "SELECT COUNT(*) FROM execution_attempts"
            ).fetchone()[0]
            connection.close()

            self.assertEqual(execution_service.reconcile_calls, ["XAUUSD", "XAUUSD"])
            self.assertEqual(execution_attempt_count, 0)
            self.assertEqual(len(sync_rows), 1)
            self.assertEqual(sync_rows[0][0], "position_closed_tp")
            payload = json.loads(sync_rows[0][1])
            self.assertIsNone(payload["order"])
            self.assertIsNone(payload["execution_result"])
            self.assertEqual(payload["sync_result"]["sync_origin"], "reconcile")
            self.assertEqual(payload["sync_result"]["history_deal_reason"], "deal_reason_tp")


if __name__ == "__main__":
    unittest.main()
