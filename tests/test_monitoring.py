from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.cli import main
from xauusd_ai_system.core.enums import EntryType, MarketState, TradeSide, WarningLevel
from xauusd_ai_system.core.models import (
    AccountState,
    MarketSnapshot,
    RiskDecision,
    StateDecision,
    TradeSignal,
    TradingDecision,
    VolatilityAlert,
    VolatilityAssessment,
)
from xauusd_ai_system.execution.base import ExecutionOrder, ExecutionResult
from xauusd_ai_system.execution.base import ExecutionSyncResult
from xauusd_ai_system.monitoring.service import MonitoringSnapshotService
from xauusd_ai_system.storage.sqlite_repository import SQLiteAuditRepository


class MonitoringTests(unittest.TestCase):
    def test_snapshot_summarizes_recent_decisions_and_executions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            database_url = self._build_sample_database(Path(tmpdir) / "system.db")
            snapshot = MonitoringSnapshotService(database_url).build_snapshot(
                decision_limit=20,
                execution_limit=20,
                stale_after_seconds=300,
            )

            self.assertEqual(snapshot["runtime"]["status"], "healthy")
            self.assertEqual(snapshot["overview"]["decision_window_size"], 2)
            self.assertEqual(snapshot["overview"]["execution_window_size"], 2)
            self.assertEqual(snapshot["overview"]["warning_alerts"], 1)
            self.assertEqual(snapshot["overview"]["accepted_executions"], 1)
            self.assertEqual(snapshot["paper"]["candidate_signals"], 2)
            self.assertEqual(snapshot["paper"]["allowed_candidates"], 1)
            self.assertEqual(snapshot["paper"]["blocked_candidates"], 1)
            self.assertEqual(snapshot["pressure"]["risk_reasons"][0]["name"], "VOLATILITY_WARNING")
            self.assertEqual(snapshot["pressure"]["risk_advisories"][0]["name"], "reduce_risk")
            self.assertEqual(snapshot["pressure"]["execution_errors"][0]["name"], "broker_timeout")
            self.assertEqual(snapshot["execution_sync"]["latest_status"], "position_open")
            self.assertEqual(snapshot["execution_sync"]["latest_origin"], "submission")
            self.assertEqual(snapshot["execution_sync"]["latest_requested_price"], 3062.0)
            self.assertEqual(snapshot["execution_sync"]["latest_observed_price"], 3061.84)
            self.assertEqual(snapshot["execution_sync"]["latest_observed_price_source"], "position_open")
            self.assertEqual(snapshot["execution_sync"]["latest_history_order_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["latest_history_deal_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["latest_history_deal_ticket"], "81001")
            self.assertEqual(snapshot["execution_sync"]["latest_position_ticket"], "7001")
            self.assertEqual(snapshot["execution_sync"]["latest_position_identifier"], "99001")
            self.assertEqual(snapshot["execution_sync"]["latest_history_order_state"], "order_state_filled")
            self.assertEqual(snapshot["execution_sync"]["latest_history_deal_entry"], "deal_entry_in")
            self.assertEqual(snapshot["execution_sync"]["latest_history_deal_reason"], "deal_reason_expert")
            self.assertEqual(snapshot["execution_sync"]["latest_price_offset"], -0.16)
            self.assertEqual(snapshot["execution_sync"]["latest_adverse_slippage_points"], 16.0)
            self.assertEqual(snapshot["execution_sync"]["average_adverse_slippage_points"], 16.0)
            self.assertEqual(snapshot["execution_sync"]["max_adverse_slippage_points"], 16.0)
            self.assertEqual(snapshot["execution_sync"]["tracked_sync_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["recent_submission_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["recent_reconcile_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["recent_close_event_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["recent_tp_close_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["recent_sl_close_count"], 0)
            self.assertEqual(snapshot["execution_sync"]["recent_attention_count"], 0)
            self.assertEqual(snapshot["pressure"]["execution_sync_statuses"][0]["name"], "position_open")
            self.assertEqual(snapshot["pressure"]["execution_sync_origins"][0]["name"], "submission")
            self.assertEqual(
                self._find_mix(snapshot["pressure"]["execution_sync_close_statuses"], "position_closed_tp")["count"],
                1,
            )
            self.assertEqual(
                self._find_mix(snapshot["pressure"]["execution_sync_deal_reasons"], "deal_reason_tp")["count"],
                1,
            )
            self.assertEqual(snapshot["latest_decision"]["signal_strategy"], "pullback")
            self.assertEqual(snapshot["recent_alerts"][0]["volatility_level"], "warning")
            self.assertEqual(
                snapshot["recent_executions"][0]["strategy_name"],
                "pullback",
            )

        state_mix = self._find_mix(snapshot["mix"]["state_labels"], "pullback_continuation")
        self.assertIsNotNone(state_mix)

    def test_snapshot_recovers_slippage_fields_from_legacy_sync_raw_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "system.db"
            database_url = self._build_sample_database(db_path)

            connection = sqlite3.connect(db_path)
            row = connection.execute(
                "SELECT id, payload_json FROM execution_syncs LIMIT 1"
            ).fetchone()
            assert row is not None
            payload = json.loads(row[1])
            sync_result = payload["sync_result"]
            raw_response = sync_result.setdefault("raw_response", {})
            for key in (
                "requested_price",
                "observed_price",
                "observed_price_source",
                "price_offset",
                "adverse_slippage",
                "adverse_slippage_points",
            ):
                raw_response[key] = sync_result.pop(key)
            connection.execute(
                "UPDATE execution_syncs SET payload_json = ? WHERE id = ?",
                (json.dumps(payload, ensure_ascii=False), row[0]),
            )
            connection.commit()
            connection.close()

            snapshot = MonitoringSnapshotService(database_url).build_snapshot(
                decision_limit=20,
                execution_limit=20,
                stale_after_seconds=300,
            )

            self.assertEqual(snapshot["execution_sync"]["latest_requested_price"], 3062.0)
            self.assertEqual(snapshot["execution_sync"]["latest_observed_price"], 3061.84)
            self.assertEqual(snapshot["execution_sync"]["latest_observed_price_source"], "position_open")
            self.assertEqual(snapshot["execution_sync"]["latest_history_order_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["latest_history_deal_count"], 1)
            self.assertEqual(snapshot["execution_sync"]["latest_position_identifier"], "99001")
            self.assertEqual(snapshot["execution_sync"]["latest_price_offset"], -0.16)
            self.assertEqual(snapshot["execution_sync"]["latest_adverse_slippage_points"], 16.0)

    def test_cli_monitoring_snapshot_and_export_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            database_url = self._build_sample_database(tmp_path / "system.db")
            html_output = tmp_path / "dashboard" / "index.html"

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "monitoring",
                    "snapshot",
                    "--database-url",
                    database_url,
                    "--decision-limit",
                    "10",
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            snapshot_payload = json.loads(buffer.getvalue())
            self.assertEqual(snapshot_payload["overview"]["decision_window_size"], 2)
            self.assertEqual(snapshot_payload["runtime"]["status"], "healthy")

            export_buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "monitoring",
                    "export-html",
                    str(html_output),
                    "--database-url",
                    database_url,
                    "--title",
                    "Pullback Monitor",
                ],
            ):
                with redirect_stdout(export_buffer):
                    main()

            export_payload = json.loads(export_buffer.getvalue())
            self.assertTrue(export_payload["exported"])
            self.assertTrue(html_output.exists())
            html_text = html_output.read_text(encoding="utf-8")
            self.assertIn("Pullback Monitor", html_text)
            self.assertIn("Recent Decisions", html_text)
            self.assertIn("Paper Window", html_text)
            self.assertIn("Risk Block Reasons", html_text)
            self.assertIn("Execution Price Drift", html_text)
            self.assertIn("Execution Sync Origin", html_text)
            self.assertIn("Broker Close Status", html_text)
            self.assertIn("Broker Deal Reason", html_text)
            self.assertIn("Recent Execution Syncs", html_text)
            self.assertIn("Adverse Pts", html_text)
            self.assertIn("History Orders / Deals", html_text)
            self.assertIn("Latest Sync Origin", html_text)
            self.assertIn("Position Ticket / ID", html_text)
            self.assertIn("History Deal Entry / Reason", html_text)

    def _build_sample_database(self, database_path: Path) -> str:
        database_url = f"sqlite:///{database_path}"
        repository = SQLiteAuditRepository(database_url)
        try:
            now = datetime.now(timezone.utc).replace(microsecond=0)

            warning_snapshot = MarketSnapshot(
                timestamp=now - timedelta(seconds=30),
                symbol="XAUUSD",
                bid=3062.8,
                ask=3063.0,
                open=3062.0,
                high=3063.1,
                low=3061.8,
                close=3062.9,
                session_tag="us",
                news_flag=True,
                minutes_to_event=4,
                features={
                    "atr_expansion_ratio": 1.7,
                    "spread_ratio": 1.32,
                    "tick_speed": 1.28,
                    "breakout_pressure": 0.35,
                },
            )
            warning_decision = TradingDecision(
                state=StateDecision(
                    state_label=MarketState.PULLBACK_CONTINUATION,
                    confidence_score=0.82,
                    reason_codes=["MTF_ALIGNMENT_OK", "STRUCTURE_INTACT"],
                    bias=TradeSide.SELL,
                ),
                volatility=VolatilityAssessment(
                    primary_alert=VolatilityAlert(
                        warning_level=WarningLevel.WARNING,
                        forecast_horizon_minutes=15,
                        risk_score=0.76,
                        reason_codes=["ATR_EXPAND", "NEWS_NEAR"],
                        suggested_action="reduce_risk",
                    )
                ),
                signal=TradeSignal(
                    strategy_name="pullback",
                    side=TradeSide.SELL,
                    entry_type=EntryType.MARKET,
                    entry_price=3062.9,
                    stop_loss=3064.1,
                    take_profit=3060.7,
                    signal_reason=["PULLBACK_DEPTH_OK"],
                ),
                risk=RiskDecision(
                    allowed=False,
                    risk_reason=["VOLATILITY_WARNING"],
                    position_size=0.0,
                    advisory=["reduce_risk"],
                ),
            )
            repository.save_evaluation(
                warning_snapshot,
                AccountState(
                    equity=10020.0,
                    daily_pnl_pct=0.003,
                    drawdown_pct=0.001,
                    open_positions=0,
                ),
                warning_decision,
            )

            info_snapshot = MarketSnapshot(
                timestamp=now - timedelta(seconds=5),
                symbol="XAUUSD",
                bid=3061.9,
                ask=3062.1,
                open=3061.7,
                high=3062.3,
                low=3061.4,
                close=3062.0,
                session_tag="us",
                features={
                    "atr_expansion_ratio": 1.12,
                    "spread_ratio": 1.05,
                    "tick_speed": 1.02,
                },
            )
            info_decision = TradingDecision(
                state=StateDecision(
                    state_label=MarketState.PULLBACK_CONTINUATION,
                    confidence_score=0.79,
                    reason_codes=["MTF_ALIGNMENT_OK", "VOLATILITY_NOT_DEAD"],
                    bias=TradeSide.SELL,
                ),
                volatility=VolatilityAssessment(
                    primary_alert=VolatilityAlert(
                        warning_level=WarningLevel.INFO,
                        forecast_horizon_minutes=5,
                        risk_score=0.41,
                        reason_codes=["ACTIVE_SESSION"],
                        suggested_action="observe",
                    )
                ),
                signal=TradeSignal(
                    strategy_name="pullback",
                    side=TradeSide.SELL,
                    entry_type=EntryType.MARKET,
                    entry_price=3062.0,
                    stop_loss=3063.2,
                    take_profit=3059.8,
                    signal_reason=["PULLBACK_DEPTH_OK", "STRUCTURE_INTACT"],
                ),
                risk=RiskDecision(
                    allowed=True,
                    risk_reason=[],
                    position_size=0.25,
                    advisory=[],
                ),
            )
            repository.save_evaluation(
                info_snapshot,
                AccountState(
                    equity=10030.0,
                    daily_pnl_pct=0.004,
                    drawdown_pct=0.001,
                    open_positions=0,
                ),
                info_decision,
            )
            repository.save_execution_attempt(
                info_snapshot,
                info_decision,
                ExecutionOrder(
                    platform="mt5",
                    symbol="XAUUSD",
                    volume=0.25,
                    payload={
                        "side": "sell",
                        "type": "market",
                        "price": 3062.0,
                        "volume": 0.25,
                    },
                ),
                ExecutionResult(
                    accepted=True,
                    platform="mt5",
                    order_id="abc-001",
                    raw_response={"retcode": 10009},
                ),
            )
            repository.save_execution_attempt(
                MarketSnapshot(
                    timestamp=now - timedelta(seconds=2),
                    symbol="XAUUSD",
                    bid=3061.8,
                    ask=3062.0,
                    open=3061.6,
                    high=3062.1,
                    low=3061.2,
                    close=3061.9,
                    session_tag="us",
                    features={
                        "atr_expansion_ratio": 1.08,
                        "spread_ratio": 1.02,
                    },
                ),
                info_decision,
                ExecutionOrder(
                    platform="mt5",
                    symbol="XAUUSD",
                    volume=0.25,
                    payload={
                        "side": "sell",
                        "type": "market",
                        "price": 3061.9,
                        "volume": 0.25,
                    },
                ),
                ExecutionResult(
                    accepted=False,
                    platform="mt5",
                    order_id=None,
                    error_message="broker_timeout",
                    raw_response={"retcode": 10012},
                ),
            )
            repository.save_execution_sync(
                info_snapshot,
                ExecutionOrder(
                    platform="mt5",
                    symbol="XAUUSD",
                    volume=0.25,
                    payload={
                        "side": "sell",
                        "type": "market",
                        "price": 3062.0,
                        "volume": 0.25,
                    },
                ),
                ExecutionResult(
                    accepted=True,
                    platform="mt5",
                    order_id="abc-001",
                    raw_response={"retcode": 10009},
                ),
                ExecutionSyncResult(
                    platform="mt5",
                    symbol="XAUUSD",
                    requested_order_id="abc-001",
                    accepted=True,
                    sync_status="position_open",
                    requested_price=3062.0,
                    observed_price=3061.84,
                    observed_price_source="position_open",
                    position_ticket="7001",
                    position_identifier="99001",
                    history_order_state="order_state_filled",
                    history_deal_ticket="81001",
                    history_deal_entry="deal_entry_in",
                    history_deal_reason="deal_reason_expert",
                    price_offset=-0.16,
                    adverse_slippage=0.16,
                    adverse_slippage_points=16.0,
                    open_orders=[],
                    open_positions=[
                        {
                            "ticket": 7001,
                            "identifier": 99001,
                            "symbol": "XAUUSD",
                            "volume": 0.25,
                            "price_open": 3061.84,
                        }
                    ],
                    history_orders=[
                        {
                            "ticket": 7001,
                            "symbol": "XAUUSD",
                            "position_id": 99001,
                            "state": "order_state_filled",
                            "price_open": 3062.0,
                            "price_current": 3061.84,
                        }
                    ],
                    history_deals=[
                        {
                            "ticket": 81001,
                            "order": "abc-001",
                            "symbol": "XAUUSD",
                            "position_id": 99001,
                            "entry": "deal_entry_in",
                            "reason": "deal_reason_expert",
                            "price": 3061.84,
                            "volume": 0.25,
                        }
                    ],
                ),
            )
            repository.save_execution_sync(
                MarketSnapshot(
                    timestamp=now - timedelta(seconds=20),
                    symbol="XAUUSD",
                    bid=3059.7,
                    ask=3059.9,
                    open=3060.5,
                    high=3060.8,
                    low=3059.6,
                    close=3059.8,
                    session_tag="us",
                    features={},
                ),
                None,
                None,
                ExecutionSyncResult(
                    platform="mt5",
                    symbol="XAUUSD",
                    requested_order_id="abc-001",
                    accepted=True,
                    sync_status="position_closed_tp",
                    sync_origin="reconcile",
                    observed_price=3059.8,
                    observed_price_source="history_deal",
                    position_identifier="99001",
                    history_order_state="order_state_filled",
                    history_deal_ticket="81002",
                    history_deal_entry="deal_entry_out",
                    history_deal_reason="deal_reason_tp",
                    open_orders=[],
                    open_positions=[],
                    history_orders=[
                        {
                            "ticket": 7001,
                            "symbol": "XAUUSD",
                            "position_id": 99001,
                            "state": "order_state_filled",
                        }
                    ],
                    history_deals=[
                        {
                            "ticket": 81002,
                            "order": "abc-001",
                            "symbol": "XAUUSD",
                            "position_id": 99001,
                            "entry": "deal_entry_out",
                            "reason": "deal_reason_tp",
                            "price": 3059.8,
                            "volume": 0.25,
                        }
                    ],
                ),
            )
        finally:
            repository.close()

        return database_url

    @staticmethod
    def _find_mix(
        rows: list[dict[str, object]],
        name: str,
    ) -> dict[str, object] | None:
        for row in rows:
            if row["name"] == name:
                return row
        return None


if __name__ == "__main__":
    unittest.main()
