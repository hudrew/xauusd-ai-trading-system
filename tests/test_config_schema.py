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
    def test_runtime_tuning_overrides_apply_from_environment(self) -> None:
        env = {
            "XAUUSD_AI_MT5_DEVIATION": "35",
            "XAUUSD_AI_MT5_MAGIC": "2026040101",
            "XAUUSD_AI_RISK_CONTRACT_SIZE": "100",
            "XAUUSD_AI_RISK_MAX_SPREAD_RATIO": "1.33",
            "XAUUSD_AI_STATE_SPREAD_RATIO_MAX": "1.44",
            "XAUUSD_AI_VOLATILITY_SPREAD_RATIO_TRIGGER": "1.17",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_system_config()

        self.assertEqual(config.execution.mt5.deviation, 35)
        self.assertEqual(config.execution.mt5.magic, 2026040101)
        self.assertEqual(config.risk.contract_size, 100.0)
        self.assertEqual(config.risk.max_spread_ratio, 1.33)
        self.assertEqual(config.state_thresholds.spread_ratio_max, 1.44)
        self.assertEqual(config.volatility_monitor.spread_ratio_trigger, 1.17)

    def test_environment_tuning_overrides_yaml_values(self) -> None:
        config_text = textwrap.dedent(
            """
            state_thresholds:
              spread_ratio_max: 1.60
            risk:
              max_spread_ratio: 1.50
            volatility_monitor:
              spread_ratio_trigger: 1.30
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


if __name__ == "__main__":
    unittest.main()
