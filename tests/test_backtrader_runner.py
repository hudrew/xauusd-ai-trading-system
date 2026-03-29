from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import backtrader  # noqa: F401
    import pandas as pd
except ImportError:
    backtrader = None
    pd = None
    run_backtrader_csv = None
    SystemConfig = None
else:
    from xauusd_ai_system.backtest.backtrader_runner import run_backtrader_csv
    from xauusd_ai_system.config.schema import SystemConfig


@unittest.skipIf(pd is None or backtrader is None, "research dependencies are not installed")
class BacktraderRunnerTests(unittest.TestCase):
    def _build_history_frame(self) -> pd.DataFrame:
        timestamps = pd.date_range("2026-03-29 09:00:00", periods=720, freq="min")
        base = pd.Series(range(720), dtype="float64")
        close = 3000.0 + base * 0.03 + (base % 20) * 0.01
        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": close - 0.05,
                "high": close + 0.35,
                "low": close - 0.35,
                "close": close,
                "bid": close - 0.10,
                "ask": close + 0.10,
                "volume": 1.0,
                "session_tag": "eu",
                "news_flag": False,
            }
        )

    def test_run_backtrader_csv_produces_structured_report(self) -> None:
        frame = self._build_history_frame()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "history.csv"
            frame.to_csv(path, index=False)
            report = run_backtrader_csv(path, SystemConfig())

        self.assertEqual(report.initial_cash, 10000.0)
        self.assertGreater(report.final_value, 0.0)
        self.assertEqual(report.total_decisions, report.decision_summary.rows_processed)
        self.assertGreater(report.orders_submitted, 0)
        self.assertGreaterEqual(report.orders_completed, report.closed_trades)
        self.assertGreaterEqual(report.closed_trades, report.won_trades + report.lost_trades)
        self.assertGreaterEqual(report.win_rate, 0.0)
        self.assertLessEqual(report.win_rate, 1.0)
        self.assertGreaterEqual(report.max_drawdown_pct, 0.0)
        self.assertGreaterEqual(report.average_hold_minutes, 0.0)
        self.assertEqual(
            sum(report.decision_summary.states_by_label.values()),
            report.decision_summary.rows_processed,
        )
        strategy_trade_total = sum(
            item.closed_trades
            for item in report.trade_segmentation.performance_by_strategy.values()
        )
        state_trade_total = sum(
            item.closed_trades
            for item in report.trade_segmentation.performance_by_state.values()
        )
        session_trade_total = sum(
            item.closed_trades
            for item in report.trade_segmentation.performance_by_session.values()
        )
        self.assertEqual(strategy_trade_total, report.closed_trades)
        self.assertEqual(state_trade_total, report.closed_trades)
        self.assertEqual(session_trade_total, report.closed_trades)
        self.assertIn("performance_by_close_month", report.trade_segmentation.as_dict())
        self.assertIn("decision_summary", report.as_dict())

    def test_cost_parameters_reduce_final_value(self) -> None:
        frame = self._build_history_frame()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "history.csv"
            frame.to_csv(path, index=False)
            zero_cost = run_backtrader_csv(
                path,
                SystemConfig(),
                commission=0.0,
                slippage_perc=0.0,
            )
            with_cost = run_backtrader_csv(
                path,
                SystemConfig(),
                commission=0.0005,
                slippage_perc=0.0001,
            )

        self.assertLessEqual(with_cost.final_value, zero_cost.final_value)
        self.assertGreaterEqual(with_cost.commission_paid, zero_cost.commission_paid)

    def test_slippage_parameters_are_mutually_exclusive(self) -> None:
        frame = self._build_history_frame()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "history.csv"
            frame.to_csv(path, index=False)
            with self.assertRaises(ValueError):
                run_backtrader_csv(
                    path,
                    SystemConfig(),
                    slippage_perc=0.0001,
                    slippage_fixed=0.10,
                )


if __name__ == "__main__":
    unittest.main()
