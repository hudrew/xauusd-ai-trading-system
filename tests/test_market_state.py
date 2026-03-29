from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import StateThresholds
from xauusd_ai_system.core.enums import MarketState, TradeSide
from xauusd_ai_system.core.models import MarketSnapshot
from xauusd_ai_system.market_state.rule_classifier import RuleBasedMarketStateClassifier


class MarketStateClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = RuleBasedMarketStateClassifier(StateThresholds())

    def test_classifies_bullish_breakout(self) -> None:
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
                "atr_m1_14": 0.8,
                "breakout_distance": 0.42,
                "ema20_m5": 3061.8,
                "ema60_m5": 3061.2,
                "ema_slope_20": 0.11,
                "ema20_m15": 3061.6,
                "ema60_m15": 3061.0,
                "ema_slope_20_m15": 0.09,
                "ema20_h1": 3060.9,
                "ema60_h1": 3060.1,
                "ema_slope_20_h1": 0.07,
                "false_break_count": 1,
                "spread_ratio": 1.1,
                "volatility_ratio": 1.3,
            },
        )

        decision = self.classifier.classify(snapshot)
        self.assertEqual(decision.state_label, MarketState.TREND_BREAKOUT)
        self.assertEqual(decision.bias, TradeSide.BUY)
        self.assertIn("M15_ALIGNMENT_OK", decision.reason_codes)
        self.assertIn("H1_ALIGNMENT_OK", decision.reason_codes)

    def test_news_window_forces_no_trade(self) -> None:
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 15, 0),
            symbol="XAUUSD",
            bid=3062.8,
            ask=3063.0,
            open=3062.0,
            high=3063.1,
            low=3061.8,
            close=3062.9,
            news_flag=True,
            features={
                "atr_m1_14": 0.8,
                "breakout_distance": 0.42,
                "ema20_m5": 3061.8,
                "ema60_m5": 3061.2,
                "ema_slope_20": 0.11,
                "false_break_count": 1,
                "spread_ratio": 1.1,
                "volatility_ratio": 1.3,
            },
        )

        decision = self.classifier.classify(snapshot)
        self.assertEqual(decision.state_label, MarketState.NO_TRADE)
        self.assertIn("NEWS_BLOCK", decision.reason_codes)

    def test_classifies_pullback_continuation(self) -> None:
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
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "ema20_m15": 3061.9,
                "ema60_m15": 3061.1,
                "ema_slope_20_m15": 0.08,
                "ema20_h1": 3061.0,
                "ema60_h1": 3060.2,
                "ema_slope_20_h1": 0.06,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 0.95,
                "pullback_depth": 0.24,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
            },
        )

        decision = self.classifier.classify(snapshot)
        self.assertEqual(decision.state_label, MarketState.PULLBACK_CONTINUATION)
        self.assertEqual(decision.bias, TradeSide.BUY)

    def test_opposing_higher_timeframe_blocks_breakout_bias(self) -> None:
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
                "atr_m1_14": 0.8,
                "breakout_distance": 0.42,
                "ema20_m5": 3061.8,
                "ema60_m5": 3061.2,
                "ema_slope_20": 0.11,
                "ema20_m15": 3061.6,
                "ema60_m15": 3061.0,
                "ema_slope_20_m15": 0.09,
                "ema20_h1": 3060.1,
                "ema60_h1": 3060.8,
                "ema_slope_20_h1": -0.05,
                "false_break_count": 1,
                "spread_ratio": 1.1,
                "volatility_ratio": 1.3,
            },
        )

        decision = self.classifier.classify(snapshot)
        self.assertEqual(decision.state_label, MarketState.NO_TRADE)
        self.assertIn("STATE_UNCLEAR", decision.reason_codes)


if __name__ == "__main__":
    unittest.main()
