from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.backtest.acceptance import build_acceptance_report
from xauusd_ai_system.backtest.backtrader_runner import BacktraderRunResult
from xauusd_ai_system.backtest.evaluation import (
    BacktestSliceReport,
    InOutSampleComparison,
    InOutSampleReport,
    WalkForwardReport,
    WalkForwardSummary,
    WalkForwardWindowReport,
)
from xauusd_ai_system.backtest.reporting import (
    DecisionAuditSummary,
    TradeSegmentSummary,
    TradeSegmentationSummary,
)
from xauusd_ai_system.config.schema import AcceptanceConfig


class AcceptanceReportTests(unittest.TestCase):
    def test_build_acceptance_report_passes_with_permissive_thresholds(self) -> None:
        report = build_acceptance_report(
            AcceptanceConfig(
                min_total_net_pnl=0.0,
                min_total_profit_factor=1.0,
                max_total_drawdown_pct=0.10,
                min_out_of_sample_net_pnl=0.0,
                min_out_of_sample_profit_factor=1.0,
                max_out_of_sample_drawdown_pct=0.10,
                min_walk_forward_windows=2,
                min_walk_forward_positive_window_rate=0.5,
                max_close_month_profit_concentration=0.70,
                max_session_profit_concentration=0.80,
            ),
            backtest=self._make_backtest(
                net_pnl=120.0,
                profit_factor=1.6,
                max_drawdown_pct=0.03,
                month_segments={"2026-03": 70.0, "2026-04": 50.0},
                session_segments={"eu": 70.0, "us": 50.0},
            ),
            sample_split=self._make_sample_split(
                in_sample_net_pnl=80.0,
                out_of_sample_net_pnl=40.0,
                out_of_sample_profit_factor=1.2,
                out_of_sample_drawdown_pct=0.04,
            ),
            walk_forward=self._make_walk_forward(
                total_windows=4,
                positive_windows=3,
                positive_window_rate=0.75,
            ),
        )

        self.assertTrue(report.ready)
        self.assertEqual(report.summary.failed_checks, 0)
        self.assertEqual(report.summary.total_checks, len(report.checks))

    def test_build_acceptance_report_fails_when_thresholds_are_violated(self) -> None:
        report = build_acceptance_report(
            AcceptanceConfig(
                min_total_net_pnl=0.0,
                min_total_profit_factor=1.15,
                max_total_drawdown_pct=0.08,
                min_out_of_sample_net_pnl=0.0,
                min_out_of_sample_profit_factor=1.0,
                max_out_of_sample_drawdown_pct=0.08,
                min_walk_forward_windows=3,
                min_walk_forward_positive_window_rate=0.60,
                max_close_month_profit_concentration=0.65,
                max_session_profit_concentration=0.75,
            ),
            backtest=self._make_backtest(
                net_pnl=-10.0,
                profit_factor=0.9,
                max_drawdown_pct=0.12,
                month_segments={"2026-03": 100.0, "2026-04": -110.0},
                session_segments={"eu": 100.0, "us": -110.0},
            ),
            sample_split=self._make_sample_split(
                in_sample_net_pnl=60.0,
                out_of_sample_net_pnl=-20.0,
                out_of_sample_profit_factor=0.7,
                out_of_sample_drawdown_pct=0.10,
            ),
            walk_forward=self._make_walk_forward(
                total_windows=2,
                positive_windows=0,
                positive_window_rate=0.0,
            ),
        )

        failed_names = {check.name for check in report.checks if not check.passed}

        self.assertFalse(report.ready)
        self.assertGreater(report.summary.failed_checks, 0)
        self.assertIn("total_net_pnl", failed_names)
        self.assertIn("total_profit_factor", failed_names)
        self.assertIn("total_max_drawdown_pct", failed_names)
        self.assertIn("out_of_sample_net_pnl", failed_names)
        self.assertIn("out_of_sample_profit_factor", failed_names)
        self.assertIn("walk_forward_window_count", failed_names)
        self.assertIn("walk_forward_positive_window_rate", failed_names)
        self.assertIn("close_month_profit_concentration", failed_names)
        self.assertIn("session_profit_concentration", failed_names)

    @staticmethod
    def _make_backtest(
        *,
        net_pnl: float,
        profit_factor: float | None,
        max_drawdown_pct: float,
        month_segments: dict[str, float],
        session_segments: dict[str, float],
    ) -> BacktraderRunResult:
        total_positive = sum(max(value, 0.0) for value in month_segments.values())
        total_negative = abs(sum(min(value, 0.0) for value in month_segments.values()))
        return BacktraderRunResult(
            initial_cash=10_000.0,
            final_value=10_000.0 + net_pnl,
            cash=10_000.0 + net_pnl,
            net_pnl=net_pnl,
            return_pct=round(net_pnl / 10_000.0, 4),
            total_decisions=100,
            orders_submitted=10,
            orders_completed=8,
            orders_cancelled=2,
            orders_rejected=0,
            orders_margin=0,
            closed_trades=4,
            won_trades=2 if net_pnl >= 0 else 1,
            lost_trades=2 if net_pnl >= 0 else 3,
            win_rate=0.5 if net_pnl >= 0 else 0.25,
            average_trade_pnl=round(net_pnl / 4.0, 4),
            average_win_pnl=40.0 if net_pnl >= 0 else 20.0,
            average_loss_pnl=-10.0 if net_pnl >= 0 else -15.0,
            payoff_ratio=1.5 if profit_factor else 0.8,
            gross_profit=round(total_positive, 4),
            gross_loss=round(total_negative, 4),
            profit_factor=profit_factor,
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_amount=round(max_drawdown_pct * 10_000.0, 4),
            average_hold_bars=20.0,
            average_hold_minutes=20.0,
            max_consecutive_losses=2,
            commission_paid=5.0,
            decision_summary=_make_decision_summary(),
            trade_segmentation=_make_trade_segmentation(month_segments, session_segments),
        )

    @staticmethod
    def _make_sample_split(
        *,
        in_sample_net_pnl: float,
        out_of_sample_net_pnl: float,
        out_of_sample_profit_factor: float | None,
        out_of_sample_drawdown_pct: float,
    ) -> InOutSampleReport:
        in_sample_backtest = AcceptanceReportTests._make_backtest(
            net_pnl=in_sample_net_pnl,
            profit_factor=1.3,
            max_drawdown_pct=0.03,
            month_segments={"2026-03": in_sample_net_pnl},
            session_segments={"eu": in_sample_net_pnl},
        )
        out_sample_backtest = AcceptanceReportTests._make_backtest(
            net_pnl=out_of_sample_net_pnl,
            profit_factor=out_of_sample_profit_factor,
            max_drawdown_pct=out_of_sample_drawdown_pct,
            month_segments={"2026-04": out_of_sample_net_pnl},
            session_segments={"us": out_of_sample_net_pnl},
        )
        return InOutSampleReport(
            total_rows=1000,
            split_index=700,
            train_ratio=0.7,
            warmup_bars=120,
            in_sample=BacktestSliceReport(
                label="in_sample",
                total_rows=700,
                warmup_rows=0,
                evaluation_rows=700,
                evaluation_start="2026-03-01 09:00:00",
                evaluation_end="2026-03-02 09:00:00",
                backtest=in_sample_backtest,
            ),
            out_of_sample=BacktestSliceReport(
                label="out_of_sample",
                total_rows=420,
                warmup_rows=120,
                evaluation_rows=300,
                evaluation_start="2026-03-02 09:01:00",
                evaluation_end="2026-03-03 09:00:00",
                backtest=out_sample_backtest,
            ),
            comparison=InOutSampleComparison(
                return_pct_delta=round(
                    out_sample_backtest.return_pct - in_sample_backtest.return_pct,
                    4,
                ),
                net_pnl_delta=round(out_of_sample_net_pnl - in_sample_net_pnl, 4),
                win_rate_delta=round(
                    out_sample_backtest.win_rate - in_sample_backtest.win_rate,
                    4,
                ),
                max_drawdown_pct_delta=round(
                    out_of_sample_drawdown_pct - in_sample_backtest.max_drawdown_pct,
                    4,
                ),
                profit_factor_delta=(
                    round((out_of_sample_profit_factor or 0.0) - 1.3, 4)
                ),
                out_of_sample_positive=out_of_sample_net_pnl >= 0,
            ),
        )

    @staticmethod
    def _make_walk_forward(
        *,
        total_windows: int,
        positive_windows: int,
        positive_window_rate: float,
    ) -> WalkForwardReport:
        windows = [
            WalkForwardWindowReport(
                window_index=index,
                train_rows=300,
                warmup_rows=90,
                evaluation_rows=150,
                train_start="2026-03-01 09:00:00",
                train_end="2026-03-01 13:59:00",
                test_start="2026-03-01 14:00:00",
                test_end="2026-03-01 16:29:00",
                backtest=AcceptanceReportTests._make_backtest(
                    net_pnl=10.0 if index <= positive_windows else -5.0,
                    profit_factor=1.2 if index <= positive_windows else 0.8,
                    max_drawdown_pct=0.03,
                    month_segments={"2026-03": 10.0 if index <= positive_windows else -5.0},
                    session_segments={"eu": 10.0 if index <= positive_windows else -5.0},
                ),
            )
            for index in range(1, total_windows + 1)
        ]
        return WalkForwardReport(
            total_rows=1200,
            train_bars=300,
            test_bars=150,
            step_bars=150,
            warmup_bars=90,
            windows=windows,
            summary=WalkForwardSummary(
                total_windows=total_windows,
                positive_windows=positive_windows,
                positive_window_rate=positive_window_rate,
                total_net_pnl=round(sum(item.backtest.net_pnl for item in windows), 4),
                average_return_pct=round(
                    sum(item.backtest.return_pct for item in windows) / total_windows,
                    4,
                )
                if total_windows
                else 0.0,
                best_window_return_pct=max(
                    (item.backtest.return_pct for item in windows),
                    default=0.0,
                ),
                worst_window_return_pct=min(
                    (item.backtest.return_pct for item in windows),
                    default=0.0,
                ),
                average_profit_factor=1.1 if total_windows else None,
            ),
        )


def _make_decision_summary() -> DecisionAuditSummary:
    return DecisionAuditSummary(
        rows_processed=100,
        signals_generated=10,
        trades_allowed=8,
        blocked_trades=2,
        no_signal_rows=90,
        high_volatility_alerts=4,
        signal_rate=0.1,
        trade_allow_rate=0.8,
        blocked_signal_rate=0.2,
        high_volatility_alert_rate=0.04,
        states_by_label={"pullback_continuation": 60, "trend_breakout": 40},
        signals_by_strategy={"pullback": 6, "breakout": 4},
        signals_by_side={"buy": 7, "sell": 3},
        blocked_reasons={"NEWS_BLOCK": 1, "SPREAD_LIMIT_REACHED": 1},
        risk_advisories={"VOLATILITY_INFO_OBSERVE": 4},
        volatility_levels={"info": 90, "warning": 10},
        sessions_by_count={"eu": 60, "us": 40},
        states_by_session={"eu": {"pullback_continuation": 60}, "us": {"trend_breakout": 40}},
    )


def _make_trade_segmentation(
    month_segments: dict[str, float],
    session_segments: dict[str, float],
) -> TradeSegmentationSummary:
    return TradeSegmentationSummary(
        performance_by_close_month={
            key: _make_trade_segment(value)
            for key, value in month_segments.items()
        },
        performance_by_strategy={"pullback": _make_trade_segment(sum(month_segments.values()))},
        performance_by_state={
            "pullback_continuation": _make_trade_segment(sum(month_segments.values()))
        },
        performance_by_session={
            key: _make_trade_segment(value)
            for key, value in session_segments.items()
        },
        performance_by_side={"buy": _make_trade_segment(sum(month_segments.values()))},
    )


def _make_trade_segment(net_pnl: float) -> TradeSegmentSummary:
    gross_profit = max(net_pnl, 0.0)
    gross_loss = abs(min(net_pnl, 0.0))
    profit_factor = None if gross_loss == 0 and gross_profit > 0 else (gross_profit / gross_loss if gross_loss > 0 else None)
    return TradeSegmentSummary(
        closed_trades=2,
        won_trades=1 if net_pnl >= 0 else 0,
        lost_trades=1 if net_pnl < 0 else 0,
        win_rate=0.5 if net_pnl >= 0 else 0.0,
        net_pnl=round(net_pnl, 4),
        gross_profit=round(gross_profit, 4),
        gross_loss=round(gross_loss, 4),
        profit_factor=round(profit_factor, 4) if profit_factor is not None else None,
        average_trade_pnl=round(net_pnl / 2.0, 4),
        average_win_pnl=round(gross_profit, 4),
        average_loss_pnl=round(-gross_loss, 4) if gross_loss > 0 else 0.0,
        average_hold_bars=10.0,
        average_hold_minutes=10.0,
        commission_paid=2.0,
    )


if __name__ == "__main__":
    unittest.main()
