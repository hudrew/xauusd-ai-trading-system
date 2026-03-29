from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import RoutingConfig, SystemConfig
from xauusd_ai_system.core.enums import MarketState
from xauusd_ai_system.core.models import AccountState, MarketSnapshot
from xauusd_ai_system.core.pipeline import TradingSystem


def _build_breakout_snapshot(*, session_tag: str = "us") -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime(2026, 3, 29, 15, 0),
        symbol="XAUUSD",
        bid=3062.8,
        ask=3063.0,
        open=3062.0,
        high=3063.1,
        low=3061.8,
        close=3062.9,
        session_tag=session_tag,
        features={
            "atr_m1_14": 0.8,
            "breakout_distance": 0.42,
            "ema20_m5": 3061.8,
            "ema60_m5": 3061.2,
            "ema_slope_20": 0.11,
            "false_break_count": 1,
            "spread_ratio": 1.38,
            "volatility_ratio": 1.28,
            "atr_expansion_ratio": 1.10,
            "breakout_retest_confirmed": True,
            "structural_stop_distance": 1.1,
            "tick_speed": 1.10,
            "breakout_pressure": 0.25,
        },
    )


class StrategyRoutingTests(unittest.TestCase):
    def test_disabled_strategy_blocks_candidate_signal_but_keeps_audit_context(self) -> None:
        system = TradingSystem(
            SystemConfig(routing=RoutingConfig(disabled_strategies=("breakout",)))
        )

        decision = system.evaluate(
            _build_breakout_snapshot(),
            AccountState(equity=10_000.0),
        )

        self.assertEqual(decision.state.state_label, MarketState.TREND_BREAKOUT)
        self.assertIsNotNone(decision.signal)
        self.assertEqual(decision.signal.strategy_name, "breakout")
        self.assertFalse(decision.risk.allowed)
        self.assertIn("STRATEGY_DISABLED", decision.risk.risk_reason)
        self.assertTrue(decision.state.blocked_by_risk)
        self.assertIn("STRATEGY_DISABLED", decision.state.reason_codes)
        self.assertEqual(decision.audit["routing"]["strategy_enabled"], False)

    def test_disallowed_session_blocks_candidate_signal(self) -> None:
        system = TradingSystem(
            SystemConfig(routing=RoutingConfig(allowed_sessions=("eu", "us")))
        )

        decision = system.evaluate(
            _build_breakout_snapshot(session_tag="asia"),
            AccountState(equity=10_000.0),
        )

        self.assertIsNotNone(decision.signal)
        self.assertFalse(decision.risk.allowed)
        self.assertIn("SESSION_NOT_ALLOWED", decision.risk.risk_reason)
        self.assertIn("SESSION_NOT_ALLOWED", decision.state.reason_codes)
        self.assertEqual(decision.audit["routing"]["session_tag"], "asia")
        self.assertEqual(decision.audit["routing"]["session_allowed"], False)

    def test_allowed_session_and_enabled_strategy_preserve_normal_signal_flow(self) -> None:
        system = TradingSystem(
            SystemConfig(
                routing=RoutingConfig(
                    enabled_strategies=("breakout",),
                    allowed_sessions=("us",),
                )
            )
        )

        decision = system.evaluate(
            _build_breakout_snapshot(session_tag="us"),
            AccountState(equity=10_000.0),
        )

        self.assertIsNotNone(decision.signal)
        self.assertTrue(decision.risk.allowed)
        self.assertFalse(decision.state.blocked_by_risk)
        self.assertEqual(decision.audit["routing"]["blocked_reasons"], [])


if __name__ == "__main__":
    unittest.main()
