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

    def test_mean_reversion_research_config_is_scoped_to_range_strategy(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_mean_reversion_research.yaml")

        self.assertEqual(config.routing.enabled_strategies, ["mean_reversion"])
        self.assertEqual(
            config.routing.disabled_strategies,
            ["breakout", "pullback"],
        )

    def test_pullback_research_config_is_scoped_to_pullback_strategy(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_pullback_research.yaml")

        self.assertEqual(config.routing.enabled_strategies, ["pullback"])
        self.assertEqual(
            config.routing.disabled_strategies,
            ["breakout", "mean_reversion"],
        )

    def test_pullback_sell_research_config_is_scoped_to_sell_pullback(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_pullback_sell_research.yaml")

        self.assertEqual(config.routing.enabled_strategies, ["pullback"])
        self.assertEqual(
            config.routing.disabled_strategies,
            ["breakout", "mean_reversion"],
        )
        self.assertEqual(config.pullback.allowed_sides, ["sell"])

    def test_pullback_sell_research_v2_config_loads(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_pullback_sell_research_v2.yaml")

        self.assertEqual(config.routing.enabled_strategies, ["pullback"])
        self.assertEqual(config.pullback.allowed_sides, ["sell"])

    def test_hybrid_research_config_keeps_pullback_sell_only(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_hybrid_research.yaml")

        self.assertEqual(
            config.routing.enabled_strategies,
            ["pullback", "mean_reversion"],
        )
        self.assertEqual(config.routing.disabled_strategies, ["breakout"])
        self.assertEqual(config.pullback.allowed_sides, ["sell"])

    def test_pullback_sell_research_v3_config_loads(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_pullback_sell_research_v3.yaml")

        self.assertEqual(config.routing.enabled_strategies, ["pullback"])
        self.assertEqual(config.pullback.allowed_sides, ["sell"])
        self.assertEqual(config.pullback.min_entry_hour, 20)

    def test_mt5_paper_pullback_sell_v3_config_isolated_from_mainline(self) -> None:
        config = load_system_config(ROOT / "configs/mt5_paper_pullback_sell_v3.yaml")

        self.assertEqual(config.runtime.environment, "paper")
        self.assertTrue(config.runtime.dry_run)
        self.assertEqual(config.routing.enabled_strategies, ["pullback"])
        self.assertEqual(config.routing.disabled_strategies, ["breakout", "mean_reversion"])
        self.assertEqual(config.routing.allowed_sessions, ["us"])
        self.assertEqual(config.pullback.allowed_sides, ["sell"])
        self.assertEqual(config.report_archive.base_dir, "reports/research_pullback_sell_v3")
        self.assertEqual(config.database.url, "sqlite:///var/xauusd_ai/paper_pullback_sell_v3.db")


if __name__ == "__main__":
    unittest.main()
