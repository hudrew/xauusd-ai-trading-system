from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config.schema import AcceptanceConfig, SystemConfig
from ..data.csv_loader import CSVMarketDataLoader
from .backtrader_runner import BacktraderRunResult, run_backtrader_market_data
from .evaluation import (
    InOutSampleReport,
    WalkForwardReport,
    run_in_out_sample_market_data,
    run_walk_forward_market_data,
)


@dataclass
class AcceptanceCheck:
    name: str
    passed: bool
    threshold: str
    observed: Any
    detail: str
    severity: str = "error"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "threshold": self.threshold,
            "observed": self.observed,
            "detail": self.detail,
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class AcceptanceSummary:
    passed_checks: int
    failed_checks: int
    total_checks: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "total_checks": self.total_checks,
        }


@dataclass
class AcceptanceReport:
    ready: bool
    checked_at: datetime
    summary: AcceptanceSummary
    checks: list[AcceptanceCheck] = field(default_factory=list)
    backtest: BacktraderRunResult | None = None
    sample_split: InOutSampleReport | None = None
    walk_forward: WalkForwardReport | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "checked_at": self.checked_at.isoformat(),
            "summary": self.summary.as_dict(),
            "checks": [check.as_dict() for check in self.checks],
            "backtest": self.backtest.as_dict() if self.backtest else None,
            "sample_split": self.sample_split.as_dict() if self.sample_split else None,
            "walk_forward": self.walk_forward.as_dict() if self.walk_forward else None,
        }


def run_acceptance_csv(
    path: str | Path,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    train_ratio: float = 0.7,
    warmup_bars: int = 720,
    train_bars: int = 5000,
    test_bars: int = 1000,
    step_bars: int | None = None,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> AcceptanceReport:
    resolved_symbol = (
        symbol
        or config.market_data.symbol
        or config.execution.symbol
        or config.market_data.mt5.symbol
        or "XAUUSD"
    )
    market_data = CSVMarketDataLoader().load(path, symbol=resolved_symbol)
    backtest = run_backtrader_market_data(
        market_data,
        config,
        symbol=resolved_symbol,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    sample_split = run_in_out_sample_market_data(
        market_data,
        config,
        symbol=resolved_symbol,
        train_ratio=train_ratio,
        warmup_bars=warmup_bars,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    walk_forward = run_walk_forward_market_data(
        market_data,
        config,
        symbol=resolved_symbol,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
        warmup_bars=warmup_bars,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    return build_acceptance_report(
        config.acceptance,
        backtest=backtest,
        sample_split=sample_split,
        walk_forward=walk_forward,
    )


def build_acceptance_report(
    acceptance_config: AcceptanceConfig,
    *,
    backtest: BacktraderRunResult,
    sample_split: InOutSampleReport,
    walk_forward: WalkForwardReport,
) -> AcceptanceReport:
    checks = [
        _min_value_check(
            "total_net_pnl",
            backtest.net_pnl,
            acceptance_config.min_total_net_pnl,
            unit="USD",
        ),
        _min_profit_factor_check(
            "total_profit_factor",
            backtest,
            acceptance_config.min_total_profit_factor,
        ),
        _max_value_check(
            "total_max_drawdown_pct",
            backtest.max_drawdown_pct,
            acceptance_config.max_total_drawdown_pct,
            unit="ratio",
        ),
        _min_value_check(
            "out_of_sample_net_pnl",
            sample_split.out_of_sample.backtest.net_pnl,
            acceptance_config.min_out_of_sample_net_pnl,
            unit="USD",
        ),
        _min_profit_factor_check(
            "out_of_sample_profit_factor",
            sample_split.out_of_sample.backtest,
            acceptance_config.min_out_of_sample_profit_factor,
        ),
        _max_value_check(
            "out_of_sample_max_drawdown_pct",
            sample_split.out_of_sample.backtest.max_drawdown_pct,
            acceptance_config.max_out_of_sample_drawdown_pct,
            unit="ratio",
        ),
        _min_value_check(
            "walk_forward_window_count",
            walk_forward.summary.total_windows,
            acceptance_config.min_walk_forward_windows,
            unit="windows",
        ),
        _min_value_check(
            "walk_forward_positive_window_rate",
            walk_forward.summary.positive_window_rate,
            acceptance_config.min_walk_forward_positive_window_rate,
            unit="ratio",
        ),
        _positive_concentration_check(
            "close_month_profit_concentration",
            backtest.trade_segmentation.performance_by_close_month,
            acceptance_config.max_close_month_profit_concentration,
        ),
        _positive_concentration_check(
            "session_profit_concentration",
            backtest.trade_segmentation.performance_by_session,
            acceptance_config.max_session_profit_concentration,
        ),
    ]

    passed_checks = sum(check.passed for check in checks)
    summary = AcceptanceSummary(
        passed_checks=passed_checks,
        failed_checks=len(checks) - passed_checks,
        total_checks=len(checks),
    )
    return AcceptanceReport(
        ready=passed_checks == len(checks),
        checked_at=datetime.now(timezone.utc),
        summary=summary,
        checks=checks,
        backtest=backtest,
        sample_split=sample_split,
        walk_forward=walk_forward,
    )


def _min_value_check(name: str, observed: float, threshold: float, *, unit: str) -> AcceptanceCheck:
    passed = observed >= threshold
    return AcceptanceCheck(
        name=name,
        passed=passed,
        threshold=f">= {threshold}",
        observed=round(observed, 4) if isinstance(observed, float) else observed,
        detail=(
            f"Observed {observed:.4f} {unit}, required at least {threshold:.4f}."
            if isinstance(observed, float)
            else f"Observed {observed} {unit}, required at least {threshold}."
        ),
    )


def _max_value_check(name: str, observed: float, threshold: float, *, unit: str) -> AcceptanceCheck:
    passed = observed <= threshold
    return AcceptanceCheck(
        name=name,
        passed=passed,
        threshold=f"<= {threshold}",
        observed=round(observed, 4),
        detail=f"Observed {observed:.4f} {unit}, required no more than {threshold:.4f}.",
    )


def _min_profit_factor_check(
    name: str,
    report: BacktraderRunResult,
    threshold: float,
) -> AcceptanceCheck:
    observed = _effective_profit_factor(report)
    if observed is None:
        return AcceptanceCheck(
            name=name,
            passed=False,
            threshold=f">= {threshold}",
            observed=None,
            detail="Profit Factor is unavailable because no closed trades were produced.",
            metadata={"closed_trades": report.closed_trades},
        )
    passed = observed >= threshold
    observed_value = "inf" if observed == float("inf") else round(observed, 4)
    return AcceptanceCheck(
        name=name,
        passed=passed,
        threshold=f">= {threshold}",
        observed=observed_value,
        detail=(
            f"Observed Profit Factor {observed_value}, required at least {threshold:.4f}."
        ),
        metadata={"closed_trades": report.closed_trades},
    )


def _positive_concentration_check(
    name: str,
    segments: dict[str, Any],
    threshold: float,
) -> AcceptanceCheck:
    top_label, share, positive_pool = _positive_profit_concentration(segments)
    if positive_pool <= 0 or top_label is None:
        return AcceptanceCheck(
            name=name,
            passed=True,
            threshold=f"<= {threshold}",
            observed=None,
            detail="No positive profit pool was available, so concentration is not applicable.",
            severity="warning",
            metadata={"positive_profit_pool": round(positive_pool, 4)},
        )

    passed = share <= threshold
    return AcceptanceCheck(
        name=name,
        passed=passed,
        threshold=f"<= {threshold}",
        observed=round(share, 4),
        detail=(
            f"Top positive profit contribution came from '{top_label}' with share {share:.4f}; "
            f"required no more than {threshold:.4f}."
        ),
        metadata={
            "top_label": top_label,
            "positive_profit_pool": round(positive_pool, 4),
        },
    )


def _effective_profit_factor(report: BacktraderRunResult) -> float | None:
    if report.closed_trades <= 0:
        return None
    if report.gross_loss <= 0 and report.gross_profit > 0:
        return float("inf")
    if report.profit_factor is None:
        return None
    return float(report.profit_factor)


def _positive_profit_concentration(segments: dict[str, Any]) -> tuple[str | None, float, float]:
    positive_pnls = {
        key: max(float(summary.net_pnl), 0.0)
        for key, summary in segments.items()
    }
    positive_pool = sum(positive_pnls.values())
    if positive_pool <= 0:
        return None, 0.0, positive_pool

    top_label, top_value = max(
        positive_pnls.items(),
        key=lambda item: (item[1], item[0]),
    )
    return top_label, top_value / positive_pool, positive_pool
