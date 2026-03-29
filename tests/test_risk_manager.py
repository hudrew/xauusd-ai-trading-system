from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import RiskConfig
from xauusd_ai_system.core.enums import EntryType, TradeSide
from xauusd_ai_system.core.models import AccountState, MarketSnapshot, TradeSignal
from xauusd_ai_system.risk.manager import RiskManager


class RiskManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = RiskManager(RiskConfig())
        self.snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.8,
            ask=3063.0,
            open=3062.0,
            high=3063.1,
            low=3061.8,
            close=3062.9,
            features={"spread_ratio": 1.1},
        )
        self.signal = TradeSignal(
            strategy_name="breakout",
            side=TradeSide.BUY,
            entry_type=EntryType.MARKET,
            entry_price=3063.0,
            stop_loss=3061.5,
            take_profit=3066.0,
        )

    def test_allows_signal_when_risk_budget_is_available(self) -> None:
        account_state = AccountState(equity=10_000.0)
        decision = self.manager.assess(self.snapshot, self.signal, account_state)

        self.assertTrue(decision.allowed)
        self.assertGreater(decision.position_size, 0.0)

    def test_blocks_signal_after_daily_loss_limit(self) -> None:
        account_state = AccountState(equity=10_000.0, daily_pnl_pct=-0.03)
        decision = self.manager.assess(self.snapshot, self.signal, account_state)

        self.assertFalse(decision.allowed)
        self.assertIn("DAILY_LOSS_LIMIT_REACHED", decision.risk_reason)

    def test_reduces_position_when_higher_timeframe_alignment_is_partial(self) -> None:
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.8,
            ask=3063.0,
            open=3062.0,
            high=3063.1,
            low=3061.8,
            close=3062.9,
            features={
                "spread_ratio": 1.1,
                "ema20_m5": 3061.8,
                "ema60_m5": 3061.2,
                "ema_slope_20": 0.11,
                "ema20_m15": 3061.6,
                "ema60_m15": 3061.8,
                "ema_slope_20_m15": -0.04,
            },
        )

        decision = self.manager.assess(snapshot, self.signal, AccountState(equity=10_000.0))

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.position_scale, 0.7)
        self.assertIn("MTF_PARTIAL_ALIGNMENT", decision.advisory)

    def test_blocks_trend_signal_when_all_timeframes_conflict(self) -> None:
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.8,
            ask=3063.0,
            open=3062.0,
            high=3063.1,
            low=3061.8,
            close=3062.9,
            features={
                "spread_ratio": 1.1,
                "ema20_m5": 3061.0,
                "ema60_m5": 3061.7,
                "ema_slope_20": -0.09,
                "ema20_m15": 3060.6,
                "ema60_m15": 3061.4,
                "ema_slope_20_m15": -0.05,
            },
        )

        decision = self.manager.assess(snapshot, self.signal, AccountState(equity=10_000.0))

        self.assertFalse(decision.allowed)
        self.assertIn("MTF_TREND_MISMATCH", decision.risk_reason)


if __name__ == "__main__":
    unittest.main()
