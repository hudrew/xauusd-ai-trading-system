from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import load_system_config


class ConfigSchemaEnvOverrideTests(unittest.TestCase):
    def test_default_research_backtest_config_is_conservative(self) -> None:
        config = load_system_config()

        self.assertGreater(config.backtest.commission, 0.0)
        self.assertGreater(config.backtest.slippage_perc, 0.0)
        self.assertGreaterEqual(config.backtest.fill_delay_bars, 1)
        self.assertGreater(config.backtest.stop_loss_slippage_perc, 0.0)
        self.assertGreater(config.backtest.take_profit_slippage_perc, 0.0)
        self.assertGreater(config.backtest.timed_exit_slippage_perc, 0.0)
        self.assertTrue(config.backtest.reset_consecutive_losses_on_session_change)

    def test_runtime_tuning_overrides_apply_from_environment(self) -> None:
        env = {
            "XAUUSD_AI_MT5_DEVIATION": "35",
            "XAUUSD_AI_MT5_MAGIC": "2026040101",
            "XAUUSD_AI_RISK_CONTRACT_SIZE": "100",
            "XAUUSD_AI_RISK_MAX_SPREAD_RATIO": "1.33",
            "XAUUSD_AI_STATE_SPREAD_RATIO_MAX": "1.44",
            "XAUUSD_AI_VOLATILITY_SPREAD_RATIO_TRIGGER": "1.17",
            "XAUUSD_AI_ENABLED_STRATEGIES": "pullback,mean_reversion",
            "XAUUSD_AI_DISABLED_STRATEGIES": "breakout",
            "XAUUSD_AI_ALLOWED_SESSIONS": "eu, overlap, us",
            "XAUUSD_AI_BLOCKED_SESSIONS": "asia",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_system_config()

        self.assertEqual(config.execution.mt5.deviation, 35)
        self.assertEqual(config.execution.mt5.magic, 2026040101)
        self.assertEqual(config.risk.contract_size, 100.0)
        self.assertEqual(config.risk.max_spread_ratio, 1.33)
        self.assertEqual(config.state_thresholds.spread_ratio_max, 1.44)
        self.assertEqual(config.volatility_monitor.spread_ratio_trigger, 1.17)
        self.assertEqual(config.routing.enabled_strategies, ("pullback", "mean_reversion"))
        self.assertEqual(config.routing.disabled_strategies, ("breakout",))
        self.assertEqual(config.routing.allowed_sessions, ("eu", "overlap", "us"))
        self.assertEqual(config.routing.blocked_sessions, ("asia",))

    def test_environment_tuning_overrides_yaml_values(self) -> None:
        config_text = textwrap.dedent(
            """
            state_thresholds:
              spread_ratio_max: 1.60
            risk:
              max_spread_ratio: 1.50
            volatility_monitor:
              spread_ratio_trigger: 1.30
            routing:
              enabled_strategies: ["breakout", "pullback"]
              allowed_sessions: ["us"]
            execution:
              mt5:
                deviation: 20
                magic: 2026032901
            """
        )

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(config_text)
            config_path = handle.name

        env = {
            "XAUUSD_AI_MT5_DEVIATION": "28",
            "XAUUSD_AI_MT5_MAGIC": "2026040102",
            "XAUUSD_AI_RISK_CONTRACT_SIZE": "120",
            "XAUUSD_AI_RISK_MAX_SPREAD_RATIO": "1.39",
            "XAUUSD_AI_STATE_SPREAD_RATIO_MAX": "1.48",
            "XAUUSD_AI_VOLATILITY_SPREAD_RATIO_TRIGGER": "1.19",
            "XAUUSD_AI_ENABLED_STRATEGIES": "pullback,mean_reversion",
            "XAUUSD_AI_DISABLED_STRATEGIES": "breakout",
            "XAUUSD_AI_ALLOWED_SESSIONS": "eu,us",
            "XAUUSD_AI_BLOCKED_SESSIONS": "asia",
        }

        try:
            with patch.dict(os.environ, env, clear=True):
                config = load_system_config(config_path)
        finally:
            os.unlink(config_path)

        self.assertEqual(config.execution.mt5.deviation, 28)
        self.assertEqual(config.execution.mt5.magic, 2026040102)
        self.assertEqual(config.risk.contract_size, 120.0)
        self.assertEqual(config.risk.max_spread_ratio, 1.39)
        self.assertEqual(config.state_thresholds.spread_ratio_max, 1.48)
        self.assertEqual(config.volatility_monitor.spread_ratio_trigger, 1.19)
        self.assertEqual(config.routing.enabled_strategies, ("pullback", "mean_reversion"))
        self.assertEqual(config.routing.disabled_strategies, ("breakout",))
        self.assertEqual(config.routing.allowed_sessions, ("eu", "us"))
        self.assertEqual(config.routing.blocked_sessions, ("asia",))


if __name__ == "__main__":
    unittest.main()
