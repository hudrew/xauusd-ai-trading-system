from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.backtest.pullback_density_probe import (
    PullbackDensityVariant,
    apply_dataclass_overrides,
    build_pullback_density_probe,
)
from xauusd_ai_system.config.schema import load_system_config


ROOT = Path(__file__).resolve().parents[1]


class _FakeAcceptanceReport:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def as_dict(self) -> dict:
        return self._payload


def _fake_acceptance_payload(
    *,
    closed_trades: int,
    net_pnl: float,
    profit_factor: float,
    pullback_signals: int,
    trades_allowed: int,
    ready: bool,
) -> dict:
    return {
        "ready": ready,
        "summary": {"passed_checks": 10 if ready else 9, "failed_checks": 0 if ready else 1, "total_checks": 10},
        "checks": [
            {
                "name": "session_profit_concentration",
                "passed": True,
                "observed": 1.0,
                "threshold": "<= 1.0",
                "metadata": {"top_label": "us"},
            },
            {
                "name": "walk_forward_positive_window_rate",
                "passed": ready,
                "observed": 0.9,
                "threshold": ">= 0.55",
                "metadata": {},
            },
        ],
        "backtest": {
            "closed_trades": closed_trades,
            "won_trades": max(closed_trades - 1, 0),
            "lost_trades": 1 if closed_trades > 0 else 0,
            "net_pnl": net_pnl,
            "profit_factor": profit_factor,
            "win_rate": 0.7,
            "max_drawdown_pct": 0.01,
            "decision_summary": {
                "signals_generated": 1000 + pullback_signals,
                "trades_allowed": trades_allowed,
                "blocked_trades": 1000 + pullback_signals - trades_allowed,
                "states_by_label": {"pullback_continuation": 60000},
                "signals_by_strategy": {
                    "breakout": 1000,
                    "pullback": pullback_signals,
                },
                "blocked_reasons": {"STRATEGY_DISABLED": 1000},
                "signal_rate": 0.01,
                "trade_allow_rate": 0.01,
            },
            "trade_segmentation": {
                "performance_by_session": {
                    "us": {
                        "closed_trades": closed_trades,
                        "net_pnl": net_pnl,
                    }
                }
            },
        },
        "sample_split": {
            "out_of_sample": {
                "backtest": {
                    "closed_trades": max(closed_trades - 1, 0),
                    "net_pnl": net_pnl,
                    "profit_factor": profit_factor,
                    "max_drawdown_pct": 0.01,
                }
            }
        },
        "walk_forward": {
            "summary": {
                "total_windows": 12,
                "positive_window_rate": 0.9,
                "total_net_pnl": net_pnl,
            }
        },
    }


class PullbackDensityProbeTests(unittest.TestCase):
    def test_apply_dataclass_overrides_updates_nested_pullback_fields(self) -> None:
        config = load_system_config(ROOT / "configs/mvp_pullback_sell_research_v3_branch_gate.yaml")

        updated = apply_dataclass_overrides(
            config,
            {
                "pullback": {
                    "min_entry_hour": 19,
                    "allowed_sides": ["sell"],
                    "min_atr_m5": 12.0,
                }
            },
        )

        self.assertEqual(config.pullback.min_entry_hour, 20)
        self.assertEqual(updated.pullback.min_entry_hour, 19)
        self.assertEqual(updated.pullback.allowed_sides, ["sell"])
        self.assertEqual(updated.pullback.min_atr_m5, 12.0)

    def test_build_pullback_density_probe_ranks_variants_and_writes_output(self) -> None:
        variants = (
            PullbackDensityVariant(name="base", overrides={}),
            PullbackDensityVariant(name="entry_hour_19", overrides={"pullback": {"min_entry_hour": 19}}),
            PullbackDensityVariant(name="atr_m5_12", overrides={"pullback": {"min_atr_m5": 12.0}}),
        )

        def fake_run_acceptance(market_data, config, **kwargs):  # noqa: ANN001
            if config.pullback.min_atr_m5 == 12.0:
                return _FakeAcceptanceReport(
                    _fake_acceptance_payload(
                        closed_trades=9,
                        net_pnl=1.8,
                        profit_factor=2.1,
                        pullback_signals=14,
                        trades_allowed=14,
                        ready=True,
                    )
                )
            if config.pullback.min_entry_hour == 19:
                return _FakeAcceptanceReport(
                    _fake_acceptance_payload(
                        closed_trades=8,
                        net_pnl=1.6,
                        profit_factor=2.0,
                        pullback_signals=12,
                        trades_allowed=12,
                        ready=True,
                    )
                )
            return _FakeAcceptanceReport(
                _fake_acceptance_payload(
                    closed_trades=7,
                    net_pnl=1.4,
                    profit_factor=1.9,
                    pullback_signals=10,
                    trades_allowed=10,
                    ready=True,
                )
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "density_probe.json"
            with patch(
                "xauusd_ai_system.backtest.pullback_density_probe.CSVMarketDataLoader.load",
                return_value=[{"timestamp": "dummy"}],
            ):
                with patch(
                    "xauusd_ai_system.backtest.pullback_density_probe.run_acceptance_market_data",
                    side_effect=fake_run_acceptance,
                ):
                    payload = build_pullback_density_probe(
                        ROOT / "tmp/xauusd_m1_history_150000_chunked_vps_full.csv",
                        config_path=ROOT / "configs/mvp_pullback_sell_research_v3_branch_gate.yaml",
                        output_path=output_path,
                        variants=variants,
                    )

            self.assertTrue(payload["probed"])
            self.assertEqual(payload["variant_count"], 3)
            self.assertEqual(payload["probe_summary"]["best_variant_by_rank"], "atr_m5_12")
            self.assertEqual(
                payload["probe_summary"]["improved_ready_variants"],
                ["atr_m5_12", "entry_hour_19"],
            )
            self.assertEqual(payload["results"][0]["name"], "base")
            self.assertEqual(payload["results"][1]["delta_vs_base"]["closed_trades"], 1)
            self.assertEqual(payload["results"][2]["delta_vs_base"]["pullback_signal_count"], 4)
            self.assertTrue(output_path.exists())
            written_payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written_payload["probe_summary"]["ranking"][0], "atr_m5_12")


if __name__ == "__main__":
    unittest.main()
