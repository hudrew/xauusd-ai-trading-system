from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import PullbackStrategyConfig, SystemConfig
from xauusd_ai_system.core.enums import MarketState, TradeSide
from xauusd_ai_system.core.models import AccountState, MarketSnapshot, StateDecision
from xauusd_ai_system.core.pipeline import TradingSystem


class PullbackStrategyTests(unittest.TestCase):
    @staticmethod
    def _strict_pullback_system() -> TradingSystem:
        return TradingSystem(
            SystemConfig(
                pullback=PullbackStrategyConfig(
                    required_state_reasons=(
                        "MTF_ALIGNMENT_OK",
                        "PULLBACK_DEPTH_OK",
                        "STRUCTURE_INTACT",
                        "VOLATILITY_NOT_DEAD",
                    )
                )
            )
        )

    @staticmethod
    def _directional_extension_system() -> TradingSystem:
        return TradingSystem(
            SystemConfig(
                pullback=PullbackStrategyConfig(
                    max_directional_extension_atr=0.80,
                    edge_position_threshold=0.80,
                )
            )
        )

    @staticmethod
    def _minimum_quality_system() -> TradingSystem:
        return TradingSystem(
            SystemConfig(
                pullback=PullbackStrategyConfig(
                    min_pullback_depth=0.30,
                    min_atr_m1=1.00,
                    min_atr_m5=1.50,
                    min_volatility_ratio=0.90,
                    min_directional_distance_to_ema20_atr=0.30,
                )
            )
        )

    @staticmethod
    def _sell_only_system() -> TradingSystem:
        return TradingSystem(
            SystemConfig(
                pullback=PullbackStrategyConfig(
                    allowed_sides=("sell",),
                )
            )
        )

    @staticmethod
    def _time_window_system() -> TradingSystem:
        return TradingSystem(
            SystemConfig(
                pullback=PullbackStrategyConfig(
                    min_entry_hour=20,
                    max_entry_hour=22,
                )
            )
        )

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

    def test_pullback_signal_is_not_emitted_when_minimum_quality_filters_fail(self) -> None:
        system = self._minimum_quality_system()
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
                "volatility_ratio": 0.85,
                "pullback_depth": 0.24,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 0.25,
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

    def test_pullback_signal_is_emitted_when_minimum_quality_filters_pass(self) -> None:
        system = self._minimum_quality_system()
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
                "atr_m1_14": 1.4,
                "atr_m5_14": 2.0,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 1.05,
                "pullback_depth": 0.34,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 0.7,
                "vwap_deviation": 0.5,
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

    def test_pullback_buy_signal_is_not_emitted_when_side_is_not_allowed(self) -> None:
        system = self._sell_only_system()
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
                "atr_m1_14": 1.4,
                "atr_m5_14": 2.0,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 1.05,
                "pullback_depth": 0.34,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 0.7,
                "vwap_deviation": 0.5,
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

    def test_pullback_signal_is_not_emitted_outside_allowed_entry_hours(self) -> None:
        system = self._time_window_system()
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 19, 0),
            symbol="XAUUSD",
            bid=3062.6,
            ask=3062.8,
            open=3062.4,
            high=3062.9,
            low=3062.1,
            close=3062.7,
            features={
                "atr_m1_14": 1.4,
                "atr_m5_14": 2.0,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 1.05,
                "pullback_depth": 0.34,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 0.7,
                "vwap_deviation": 0.5,
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

    def test_pullback_signal_is_emitted_inside_allowed_entry_hours(self) -> None:
        system = self._time_window_system()
        snapshot = MarketSnapshot(
            timestamp=datetime(2026, 3, 29, 21, 0),
            symbol="XAUUSD",
            bid=3062.6,
            ask=3062.8,
            open=3062.4,
            high=3062.9,
            low=3062.1,
            close=3062.7,
            features={
                "atr_m1_14": 1.4,
                "atr_m5_14": 2.0,
                "breakout_distance": 0.0,
                "ema20_m5": 3062.0,
                "ema60_m5": 3061.4,
                "ema_slope_20": 0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 1.05,
                "pullback_depth": 0.34,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": 0.7,
                "vwap_deviation": 0.5,
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

    def test_pullback_signal_is_not_emitted_when_structure_check_failed(self) -> None:
        system = self._strict_pullback_system()
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
                "structure_intact": False,
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
        self.assertNotIn("STRUCTURE_INTACT", decision.state.reason_codes)
        self.assertIsNone(decision.signal)

    def test_pullback_signal_is_not_emitted_when_pullback_depth_check_failed(self) -> None:
        system = self._strict_pullback_system()
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
                "ema20_m15": 3061.9,
                "ema60_m15": 3061.1,
                "ema_slope_20_m15": 0.08,
                "ema20_h1": 3061.0,
                "ema60_h1": 3060.2,
                "ema_slope_20_h1": 0.06,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 0.95,
                "pullback_depth": 0.72,
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
        self.assertNotIn("PULLBACK_DEPTH_OK", decision.state.reason_codes)
        self.assertIsNone(decision.signal)

    def test_pullback_buy_signal_is_not_emitted_when_entry_is_too_high(self) -> None:
        system = self._directional_extension_system()
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
                "price_distance_to_ema20": 1.0,
                "vwap_deviation": 0.95,
                "range_position": 0.91,
                "bollinger_position": 0.84,
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

    def test_pullback_sell_signal_is_not_emitted_when_entry_is_too_low(self) -> None:
        system = self._directional_extension_system()
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
                "ema20_m5": 3061.4,
                "ema60_m5": 3062.0,
                "ema_slope_20": -0.10,
                "false_break_count": 1,
                "spread_ratio": 1.08,
                "volatility_ratio": 0.95,
                "pullback_depth": 0.24,
                "structure_intact": True,
                "m1_reversal_confirmed": True,
                "price_distance_to_ema20": -1.0,
                "vwap_deviation": -0.95,
                "range_position": 0.12,
                "bollinger_position": 0.16,
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
