from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import MeanReversionStrategyConfig
from xauusd_ai_system.core.enums import MarketState
from xauusd_ai_system.core.models import MarketSnapshot, StateDecision
from xauusd_ai_system.strategies.mean_reversion import MeanReversionStrategy


class MeanReversionStrategyTests(unittest.TestCase):
    def _snapshot(self, **features: float | bool) -> MarketSnapshot:
        base_features = {
            "range_position": 0.1,
            "rejection_up": True,
            "rejection_down": False,
            "atr_m1_14": 2.0,
            "range_boundary_buffer": 0.5,
            "midline_target_distance": 4.0,
            "m1_reversal_confirmed": True,
            "breakout_distance": 0.0,
            "price_distance_to_ema20": 1.0,
        }
        base_features.update(features)
        return MarketSnapshot(
            timestamp=datetime(2026, 3, 30, 10, 0),
            symbol="XAUUSD",
            bid=3000.0,
            ask=3000.2,
            open=3000.1,
            high=3000.4,
            low=2999.8,
            close=3000.0,
            features=base_features,
        )

    def test_emits_signal_for_valid_range_buy(self) -> None:
        strategy = MeanReversionStrategy(MeanReversionStrategyConfig())
        signal = strategy.generate_signal(
            self._snapshot(),
            StateDecision(
                state_label=MarketState.RANGE_MEAN_REVERSION,
                confidence_score=0.86,
            ),
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal.strategy_name, "mean_reversion")

    def test_can_require_m1_reversal_confirmation(self) -> None:
        strategy = MeanReversionStrategy(
            MeanReversionStrategyConfig(require_m1_reversal_confirmation=True)
        )
        signal = strategy.generate_signal(
            self._snapshot(m1_reversal_confirmed=False),
            StateDecision(
                state_label=MarketState.RANGE_MEAN_REVERSION,
                confidence_score=0.86,
            ),
        )

        self.assertIsNone(signal)

    def test_rejects_breakout_that_is_too_large_for_range_entry(self) -> None:
        strategy = MeanReversionStrategy(
            MeanReversionStrategyConfig(max_breakout_distance_atr=0.2)
        )
        signal = strategy.generate_signal(
            self._snapshot(breakout_distance=0.6),
            StateDecision(
                state_label=MarketState.RANGE_MEAN_REVERSION,
                confidence_score=0.86,
            ),
        )

        self.assertIsNone(signal)

    def test_rejects_entry_too_far_from_ema(self) -> None:
        strategy = MeanReversionStrategy(
            MeanReversionStrategyConfig(max_price_distance_to_ema20_atr=0.5)
        )
        signal = strategy.generate_signal(
            self._snapshot(price_distance_to_ema20=1.5),
            StateDecision(
                state_label=MarketState.RANGE_MEAN_REVERSION,
                confidence_score=0.86,
            ),
        )

        self.assertIsNone(signal)


if __name__ == "__main__":
    unittest.main()
