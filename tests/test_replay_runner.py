from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import pandas as pd
except ImportError:
    pd = None
    HistoricalReplayRunner = None
    SystemConfig = None
else:
    from xauusd_ai_system.backtest.runner import HistoricalReplayRunner
    from xauusd_ai_system.config.schema import SystemConfig
    from xauusd_ai_system.core.enums import EntryType, MarketState, TradeSide, WarningLevel
    from xauusd_ai_system.core.models import (
        RiskDecision,
        StateDecision,
        TradeSignal,
        TradingDecision,
        VolatilityAlert,
        VolatilityAssessment,
    )


@unittest.skipIf(pd is None, "pandas is not installed")
class HistoricalReplayRunnerTests(unittest.TestCase):
    def test_run_csv_produces_summary(self) -> None:
        timestamps = pd.date_range("2026-03-29 09:00:00", periods=240, freq="min")
        close = pd.Series(range(240), dtype="float64") * 0.05 + 3000.0
        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close + 0.1,
                "bid": close,
                "ask": close + 0.2,
                "volume": 1.0,
                "session_tag": "eu",
                "news_flag": False,
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "history.csv"
            frame.to_csv(path, index=False)
            summary = HistoricalReplayRunner(SystemConfig()).run_csv(path)

        self.assertGreater(summary.rows_processed, 0)
        self.assertEqual(
            summary.no_signal_rows,
            summary.rows_processed - summary.signals_generated,
        )
        self.assertEqual(sum(summary.states_by_label.values()), summary.rows_processed)
        self.assertEqual(sum(summary.sessions_by_count.values()), summary.rows_processed)
        self.assertGreaterEqual(summary.signal_rate, 0.0)
        self.assertLessEqual(summary.signal_rate, 1.0)
        self.assertIn("eu", summary.states_by_session)
        self.assertIsNotNone(summary.last_decision)

    def test_run_csv_aggregates_rich_report_metrics(self) -> None:
        timestamps = pd.date_range("2026-03-29 09:00:00", periods=4, freq="min")
        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": [3000.0, 3001.0, 3002.0, 3003.0],
                "high": [3000.5, 3001.5, 3002.5, 3003.5],
                "low": [2999.5, 3000.5, 3001.5, 3002.5],
                "close": [3000.2, 3001.2, 3002.2, 3003.2],
                "bid": [3000.1, 3001.1, 3002.1, 3003.1],
                "ask": [3000.3, 3001.3, 3002.3, 3003.3],
                "volume": [1.0, 1.0, 1.0, 1.0],
                "session_tag": ["eu", "eu", "eu", "eu"],
                "news_flag": [False, False, True, False],
            }
        )

        decisions = [
            TradingDecision(
                state=StateDecision(
                    state_label=MarketState.TREND_BREAKOUT,
                    confidence_score=0.82,
                    reason_codes=["MTF_ALIGNMENT_OK"],
                    bias=TradeSide.BUY,
                ),
                volatility=VolatilityAssessment(
                    primary_alert=VolatilityAlert(
                        warning_level=WarningLevel.WARNING,
                        forecast_horizon_minutes=5,
                        risk_score=0.68,
                        reason_codes=["ATR_EXPAND"],
                        suggested_action="reduce_risk",
                    )
                ),
                signal=TradeSignal(
                    strategy_name="breakout",
                    side=TradeSide.BUY,
                    entry_type=EntryType.RETEST,
                    entry_price=3000.3,
                    stop_loss=2999.2,
                    take_profit=3002.5,
                ),
                risk=RiskDecision(
                    allowed=True,
                    position_size=0.45,
                    risk_per_unit=110.0,
                    max_risk_amount=50.0,
                    position_scale=0.7,
                    advisory=["MTF_PARTIAL_ALIGNMENT"],
                ),
            ),
            TradingDecision(
                state=StateDecision(
                    state_label=MarketState.NO_TRADE,
                    confidence_score=0.95,
                    reason_codes=["RANGE_NOT_READY"],
                ),
                volatility=VolatilityAssessment(
                    primary_alert=VolatilityAlert(
                        warning_level=WarningLevel.INFO,
                        forecast_horizon_minutes=5,
                        risk_score=0.22,
                        reason_codes=["VOLATILITY_NORMAL"],
                        suggested_action="observe",
                    )
                ),
                signal=None,
                risk=RiskDecision(
                    allowed=False,
                    risk_reason=["NO_SIGNAL"],
                ),
            ),
            TradingDecision(
                state=StateDecision(
                    state_label=MarketState.PULLBACK_CONTINUATION,
                    confidence_score=0.74,
                    reason_codes=["TREND_PULLBACK_OK"],
                    bias=TradeSide.BUY,
                    blocked_by_risk=True,
                ),
                volatility=VolatilityAssessment(
                    primary_alert=VolatilityAlert(
                        warning_level=WarningLevel.CRITICAL,
                        forecast_horizon_minutes=5,
                        risk_score=0.91,
                        reason_codes=["NEWS_NEAR", "SPREAD_EXPAND"],
                        suggested_action="block_new_trade",
                    )
                ),
                signal=TradeSignal(
                    strategy_name="pullback",
                    side=TradeSide.BUY,
                    entry_type=EntryType.MARKET,
                    entry_price=3002.3,
                    stop_loss=3000.9,
                    take_profit=3004.8,
                ),
                risk=RiskDecision(
                    allowed=False,
                    risk_reason=["NEWS_BLOCK", "VOLATILITY_CRITICAL_BLOCK"],
                    risk_per_unit=140.0,
                    max_risk_amount=50.0,
                ),
            ),
            TradingDecision(
                state=StateDecision(
                    state_label=MarketState.RANGE_MEAN_REVERSION,
                    confidence_score=0.71,
                    reason_codes=["RANGE_REVERSION_READY"],
                    bias=TradeSide.SELL,
                ),
                volatility=VolatilityAssessment(
                    primary_alert=VolatilityAlert(
                        warning_level=WarningLevel.INFO,
                        forecast_horizon_minutes=5,
                        risk_score=0.18,
                        reason_codes=["VOLATILITY_NORMAL"],
                        suggested_action="observe",
                    )
                ),
                signal=TradeSignal(
                    strategy_name="mean_reversion",
                    side=TradeSide.SELL,
                    entry_type=EntryType.LIMIT,
                    entry_price=3003.1,
                    stop_loss=3004.0,
                    take_profit=3001.7,
                ),
                risk=RiskDecision(
                    allowed=True,
                    position_size=0.56,
                    risk_per_unit=90.0,
                    max_risk_amount=50.0,
                ),
            ),
        ]

        runner = HistoricalReplayRunner(SystemConfig())

        def fake_load(*args, **kwargs):
            return frame

        def fake_calculate(market_data):
            return market_data

        def fake_evaluate_bar(system, row, *, features, account_state):
            return decisions.pop(0)

        runner.loader.load = fake_load
        runner.calculator.calculate = fake_calculate
        runner.adapter.evaluate_bar = fake_evaluate_bar

        summary = runner.run_csv("ignored.csv")

        self.assertEqual(summary.rows_processed, 4)
        self.assertEqual(summary.signals_generated, 3)
        self.assertEqual(summary.trades_allowed, 2)
        self.assertEqual(summary.blocked_trades, 1)
        self.assertEqual(summary.no_signal_rows, 1)
        self.assertEqual(summary.high_volatility_alerts, 2)
        self.assertEqual(summary.signal_rate, 0.75)
        self.assertEqual(summary.trade_allow_rate, 0.6667)
        self.assertEqual(summary.blocked_signal_rate, 0.3333)
        self.assertEqual(summary.high_volatility_alert_rate, 0.5)
        self.assertEqual(
            summary.states_by_label,
            {
                "no_trade": 1,
                "pullback_continuation": 1,
                "range_mean_reversion": 1,
                "trend_breakout": 1,
            },
        )
        self.assertEqual(
            summary.signals_by_strategy,
            {"breakout": 1, "mean_reversion": 1, "pullback": 1},
        )
        self.assertEqual(summary.signals_by_side, {"buy": 2, "sell": 1})
        self.assertEqual(
            summary.blocked_reasons,
            {"NEWS_BLOCK": 1, "VOLATILITY_CRITICAL_BLOCK": 1},
        )
        self.assertEqual(summary.risk_advisories, {"MTF_PARTIAL_ALIGNMENT": 1})
        self.assertEqual(
            summary.volatility_levels,
            {"info": 2, "critical": 1, "warning": 1},
        )
        self.assertEqual(summary.sessions_by_count, {"eu": 4})
        self.assertEqual(
            summary.states_by_session,
            {
                "eu": {
                    "no_trade": 1,
                    "pullback_continuation": 1,
                    "range_mean_reversion": 1,
                    "trend_breakout": 1,
                }
            },
        )
        self.assertEqual(
            summary.as_dict()["states_by_session"]["eu"]["trend_breakout"],
            1,
        )
        self.assertEqual(summary.last_decision["signal"]["strategy_name"], "mean_reversion")


if __name__ == "__main__":
    unittest.main()
