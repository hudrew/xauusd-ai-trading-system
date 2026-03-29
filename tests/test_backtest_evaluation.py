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
    SystemConfig = None
    run_in_out_sample_csv = None
    run_walk_forward_csv = None
else:
    from xauusd_ai_system.backtest.evaluation import (
        run_in_out_sample_csv,
        run_walk_forward_csv,
    )
    from xauusd_ai_system.config.schema import SystemConfig


@unittest.skipIf(pd is None or backtrader is None, "research dependencies are not installed")
class BacktestEvaluationTests(unittest.TestCase):
    def _build_history_frame(self, periods: int = 1800) -> pd.DataFrame:
        timestamps = pd.date_range("2026-03-01 09:00:00", periods=periods, freq="min")
        base = pd.Series(range(periods), dtype="float64")
        close = 3000.0 + base * 0.02 + (base % 24) * 0.015
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
                "session_tag": ["eu" if ts.hour < 14 else "us" for ts in timestamps],
                "news_flag": False,
            }
        )

    def test_run_in_out_sample_csv_returns_both_slices(self) -> None:
        frame = self._build_history_frame(periods=1500)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "history.csv"
            frame.to_csv(path, index=False)
            report = run_in_out_sample_csv(
                path,
                SystemConfig(),
                train_ratio=0.7,
                warmup_bars=120,
            )

        self.assertEqual(report.total_rows, 1500)
        self.assertEqual(report.in_sample.evaluation_rows, 1050)
        self.assertEqual(report.out_of_sample.warmup_rows, 120)
        self.assertEqual(report.out_of_sample.evaluation_rows, 450)
        self.assertGreater(report.in_sample.backtest.decision_summary.rows_processed, 0)
        self.assertGreater(
            report.out_of_sample.backtest.decision_summary.rows_processed,
            0,
        )
        self.assertLessEqual(
            report.in_sample.backtest.decision_summary.rows_processed,
            report.in_sample.evaluation_rows,
        )
        self.assertLessEqual(
            report.out_of_sample.backtest.decision_summary.rows_processed,
            report.out_of_sample.evaluation_rows,
        )
        self.assertIn("comparison", report.as_dict())

    def test_run_walk_forward_csv_returns_rolling_windows(self) -> None:
        frame = self._build_history_frame(periods=1200)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "history.csv"
            frame.to_csv(path, index=False)
            report = run_walk_forward_csv(
                path,
                SystemConfig(),
                train_bars=300,
                test_bars=150,
                step_bars=150,
                warmup_bars=90,
            )

        self.assertEqual(report.total_rows, 1200)
        self.assertEqual(report.summary.total_windows, 6)
        self.assertEqual(len(report.windows), 6)
        self.assertEqual(report.windows[0].train_rows, 300)
        self.assertEqual(report.windows[0].evaluation_rows, 150)
        self.assertEqual(report.windows[0].warmup_rows, 90)
        self.assertGreater(
            report.windows[0].backtest.decision_summary.rows_processed,
            0,
        )
        self.assertLessEqual(
            report.windows[0].backtest.decision_summary.rows_processed,
            150,
        )
        self.assertGreaterEqual(report.summary.positive_window_rate, 0.0)
        self.assertLessEqual(report.summary.positive_window_rate, 1.0)
        self.assertIn("windows", report.as_dict())


if __name__ == "__main__":
    unittest.main()
