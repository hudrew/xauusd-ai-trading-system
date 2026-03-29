from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import SystemConfig
from xauusd_ai_system.core.enums import MarketState, TradeSide
from xauusd_ai_system.core.models import AccountState, MarketSnapshot, StateDecision
from xauusd_ai_system.core.pipeline import TradingSystem


class PullbackStrategyTests(unittest.TestCase):
    def test_trading_system_routes_pullback_state_to_signal(self) -> None:
        system = TradingSystem(SystemConfig())
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.6,
            ask=3062.8,
            open=3062.4,
            high=3062.9,
            low=3062.1,
            close=3062.7,
            features={
                "atr_m1_14": 0.8,
                "atr_m5_14": 1.1,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 0.95,
                "pullback_depth": 0.24,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 0.35,
                "vwap_deviation": 0.22,
                "structural_stop_distance": 1.0,
                "recent_high_n": 3065.4,
                "recent_low_n": 3061.1,
                "atr_expansion_ratio": 1.05,
                "tick_speed": 1.01,
                "breakout_pressure": 0.0,
            },
        )

        decision = system.evaluate(snapshot, AccountState(equity=10_000.0))

        self.assertEqual(decision.state.state_label, MarketState.PULLBACK_CONTINUATION)
        self.assertIsNotNone(decision.signal)
        self.assertEqual(decision.signal.strategy_name, "pullback")
        self.assertEqual(decision.signal.side, TradeSide.BUY)
        self.assertGreater(decision.signal.take_profit, decision.signal.entry_price)

    def test_pullback_signal_is_not_emitted_when_price_is_too_extended(self) -> None:
        system = TradingSystem(SystemConfig())
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.6,
            ask=3062.8,
            open=3062.4,
            high=3062.9,
            low=3062.1,
            close=3062.7,
            features={
                "atr_m1_14": 0.8,
                "atr_m5_14": 1.1,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 0.95,
                "pullback_depth": 0.24,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 1.7,
                "vwap_deviation": 1.6,
                "structural_stop_distance": 1.0,
                "recent_high_n": 3065.4,
                "recent_low_n": 3061.1,
                "atr_expansion_ratio": 1.05,
                "tick_speed": 1.01,
                "breakout_pressure": 0.0,
            },
        )

        decision = system.evaluate(snapshot, AccountState(equity=10_000.0))

        self.assertEqual(decision.state.state_label, MarketState.PULLBACK_CONTINUATION)
        self.assertIsNone(decision.signal)

    def test_pullback_strategy_requires_reversal_confirmation_by_default(self) -> None:
        system = TradingSystem(SystemConfig())
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.6,
            ask=3062.8,
            open=3062.4,
            high=3062.9,
            low=3062.1,
            close=3062.7,
            features={
                "atr_m1_14": 0.8,
                "atr_m5_14": 1.1,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 0.95,
                "pullback_depth": 0.24,
                "structure_intact": True,
                "m1_reversal_confirmed": False,
                "price_distance_to_ema20": 0.35,
                "vwap_deviation": 0.22,
                "structural_stop_distance": 1.0,
                "recent_high_n": 3065.4,
                "recent_low_n": 3061.1,
                "atr_expansion_ratio": 1.05,
                "tick_speed": 1.01,
                "breakout_pressure": 0.0,
            },
        )

        decision = system.evaluate(snapshot, AccountState(equity=10_000.0))

        self.assertEqual(decision.state.state_label, MarketState.PULLBACK_CONTINUATION)
        self.assertIsNone(decision.signal)


if __name__ == "__main__":
    unittest.main()
