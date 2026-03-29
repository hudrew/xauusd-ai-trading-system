from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import load_system_config


ROOT = Path(__file__).resolve().parents[1]


class DefaultConfigTests(unittest.TestCase):
    def test_mt5_runtime_configs_keep_research_routing_defaults(self) -> None:
        for relative_path in ("configs/mt5_paper.yaml", "configs/mt5_prod.yaml"):
            config = load_system_config(ROOT / relative_path)
            self.assertEqual(config.routing.disabled_strategies, ["breakout"])
            self.assertEqual(
                config.routing.allowed_sessions,
                ["eu", "overlap", "us"],
            )
            self.assertEqual(config.routing.enabled_strategies, [])
            self.assertEqual(config.routing.blocked_sessions, [])


if __name__ == "__main__":
    unittest.main()
