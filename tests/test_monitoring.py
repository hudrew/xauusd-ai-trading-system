from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
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
            self.assertEqual(snapshot["overview"]["execution_window_size"], 1)
            self.assertEqual(snapshot["overview"]["warning_alerts"], 1)
            self.assertEqual(snapshot["overview"]["accepted_executions"], 1)
            self.assertEqual(snapshot["latest_decision"]["signal_strategy"], "pullback")
            self.assertEqual(snapshot["recent_alerts"][0]["volatility_level"], "warning")
            self.assertEqual(
                snapshot["recent_executions"][0]["strategy_name"],
                "pullback",
            )

        def _find_mix(rows: list[dict[str, object]], name: str) -> dict[str, object] | None:
            for row in rows:
                if row["name"] == name:
                    return row
            return None

        state_mix = _find_mix(snapshot["mix"]["state_labels"], "pullback_continuation")
        self.assertIsNotNone(state_mix)

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
        finally:
            repository.close()

        return database_url


if __name__ == "__main__":
    unittest.main()
