from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.backtest.reporting import TradePerformanceCollector


class TradePerformanceCollectorTests(unittest.TestCase):
    def test_build_summary_aggregates_by_month_strategy_state_and_session(self) -> None:
        collector = TradePerformanceCollector()

        collector.record(
            {
                "strategy_name": "breakout",
                "state_label": "trend_breakout",
                "session_tag": "eu",
                "side": "buy",
            },
            close_timestamp=datetime(2026, 3, 29, 10, 0),
            net_pnl=120.0,
            commission_paid=4.0,
            hold_bars=15,
            hold_minutes=15.0,
        )
        collector.record(
            {
                "strategy_name": "pullback",
                "state_label": "pullback_continuation",
                "session_tag": "us",
                "side": "sell",
            },
            close_timestamp=datetime(2026, 4, 2, 16, 0),
            net_pnl=-45.0,
            commission_paid=2.5,
            hold_bars=8,
            hold_minutes=8.0,
        )

        summary = collector.build_summary()

        self.assertEqual(
            summary.performance_by_close_month["2026-03"].net_pnl,
            120.0,
        )
        self.assertEqual(
            summary.performance_by_close_month["2026-04"].net_pnl,
            -45.0,
        )
        self.assertEqual(
            summary.performance_by_strategy["breakout"].closed_trades,
            1,
        )
        self.assertEqual(
            summary.performance_by_state["pullback_continuation"].lost_trades,
            1,
        )
        self.assertEqual(
            summary.performance_by_session["eu"].average_hold_minutes,
            15.0,
        )
        self.assertEqual(summary.performance_by_side["sell"].gross_loss, 45.0)
        self.assertEqual(
            summary.as_dict()["performance_by_strategy"]["pullback"]["commission_paid"],
            2.5,
        )


if __name__ == "__main__":
    unittest.main()
