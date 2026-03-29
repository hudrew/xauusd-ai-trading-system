from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ..config.schema import SystemConfig
from ..data.csv_loader import CSVMarketDataLoader
from .backtrader_runner import BacktraderRunResult, run_backtrader_market_data


@dataclass
class BacktestSliceReport:
    label: str
    total_rows: int
    warmup_rows: int
    evaluation_rows: int
    evaluation_start: str
    evaluation_end: str
    backtest: BacktraderRunResult

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "total_rows": self.total_rows,
            "warmup_rows": self.warmup_rows,
            "evaluation_rows": self.evaluation_rows,
            "evaluation_start": self.evaluation_start,
            "evaluation_end": self.evaluation_end,
            "backtest": self.backtest.as_dict(),
        }


@dataclass
class InOutSampleComparison:
    return_pct_delta: float
    net_pnl_delta: float
    win_rate_delta: float
    max_drawdown_pct_delta: float
    profit_factor_delta: float | None
    out_of_sample_positive: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "return_pct_delta": self.return_pct_delta,
            "net_pnl_delta": self.net_pnl_delta,
            "win_rate_delta": self.win_rate_delta,
            "max_drawdown_pct_delta": self.max_drawdown_pct_delta,
            "profit_factor_delta": self.profit_factor_delta,
            "out_of_sample_positive": self.out_of_sample_positive,
        }


@dataclass
class InOutSampleReport:
    total_rows: int
    split_index: int
    train_ratio: float
    warmup_bars: int
    in_sample: BacktestSliceReport
    out_of_sample: BacktestSliceReport
    comparison: InOutSampleComparison

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "split_index": self.split_index,
            "train_ratio": self.train_ratio,
            "warmup_bars": self.warmup_bars,
            "in_sample": self.in_sample.as_dict(),
            "out_of_sample": self.out_of_sample.as_dict(),
            "comparison": self.comparison.as_dict(),
        }


@dataclass
class WalkForwardWindowReport:
    window_index: int
    train_rows: int
    warmup_rows: int
    evaluation_rows: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    backtest: BacktraderRunResult

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "train_rows": self.train_rows,
            "warmup_rows": self.warmup_rows,
            "evaluation_rows": self.evaluation_rows,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "backtest": self.backtest.as_dict(),
        }


@dataclass
class WalkForwardSummary:
    total_windows: int
    positive_windows: int
    positive_window_rate: float
    total_net_pnl: float
    average_return_pct: float
    best_window_return_pct: float
    worst_window_return_pct: float
    average_profit_factor: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_windows": self.total_windows,
            "positive_windows": self.positive_windows,
            "positive_window_rate": self.positive_window_rate,
            "total_net_pnl": self.total_net_pnl,
            "average_return_pct": self.average_return_pct,
            "best_window_return_pct": self.best_window_return_pct,
            "worst_window_return_pct": self.worst_window_return_pct,
            "average_profit_factor": self.average_profit_factor,
        }


@dataclass
class WalkForwardReport:
    total_rows: int
    train_bars: int
    test_bars: int
    step_bars: int
    warmup_bars: int
    windows: list[WalkForwardWindowReport]
    summary: WalkForwardSummary

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "train_bars": self.train_bars,
            "test_bars": self.test_bars,
            "step_bars": self.step_bars,
            "warmup_bars": self.warmup_bars,
            "windows": [window.as_dict() for window in self.windows],
            "summary": self.summary.as_dict(),
        }


def run_in_out_sample_csv(
    path: str | Path,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    train_ratio: float = 0.7,
    warmup_bars: int = 720,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> InOutSampleReport:
    market_data = _load_market_data(path, config, symbol=symbol)
    return run_in_out_sample_market_data(
        market_data,
        config,
        symbol=symbol,
        train_ratio=train_ratio,
        warmup_bars=warmup_bars,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )


def run_in_out_sample_market_data(
    market_data: pd.DataFrame,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    train_ratio: float = 0.7,
    warmup_bars: int = 720,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> InOutSampleReport:
    if not 0.0 < train_ratio < 1.0:
        raise ValueError("train_ratio must be between 0 and 1.")

    market_data = market_data.copy().sort_values("timestamp").reset_index(drop=True)
    total_rows = len(market_data)
    if total_rows < 2:
        raise ValueError("At least 2 rows are required for in/out sample evaluation.")

    split_index = int(total_rows * train_ratio)
    split_index = min(max(split_index, 1), total_rows - 1)

    in_sample_frame = market_data.iloc[:split_index].copy()
    out_eval_frame = market_data.iloc[split_index:].copy()
    warmup_start = max(0, split_index - max(warmup_bars, 0))
    out_run_frame = market_data.iloc[warmup_start:].copy()

    in_sample = _run_slice(
        "in_sample",
        in_sample_frame,
        evaluation_start=in_sample_frame.iloc[0]["timestamp"],
        evaluation_end=in_sample_frame.iloc[-1]["timestamp"],
        warmup_rows=0,
        config=config,
        symbol=symbol,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )
    out_of_sample = _run_slice(
        "out_of_sample",
        out_run_frame,
        evaluation_start=out_eval_frame.iloc[0]["timestamp"],
        evaluation_end=out_eval_frame.iloc[-1]["timestamp"],
        warmup_rows=len(out_run_frame) - len(out_eval_frame),
        config=config,
        symbol=symbol,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )

    return InOutSampleReport(
        total_rows=total_rows,
        split_index=split_index,
        train_ratio=round(train_ratio, 4),
        warmup_bars=max(warmup_bars, 0),
        in_sample=in_sample,
        out_of_sample=out_of_sample,
        comparison=_compare_slices(in_sample.backtest, out_of_sample.backtest),
    )


def run_walk_forward_csv(
    path: str | Path,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    warmup_bars: int = 720,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> WalkForwardReport:
    market_data = _load_market_data(path, config, symbol=symbol)
    return run_walk_forward_market_data(
        market_data,
        config,
        symbol=symbol,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
        warmup_bars=warmup_bars,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )


def run_walk_forward_market_data(
    market_data: pd.DataFrame,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    warmup_bars: int = 720,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> WalkForwardReport:
    market_data = market_data.copy().sort_values("timestamp").reset_index(drop=True)
    total_rows = len(market_data)
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive.")
    step_bars = test_bars if step_bars is None else step_bars
    if step_bars <= 0:
        raise ValueError("step_bars must be positive.")
    if total_rows < train_bars + test_bars:
        raise ValueError("Not enough rows for the requested walk-forward windows.")

    windows: list[WalkForwardWindowReport] = []
    window_index = 1
    cursor = train_bars
    warmup_bars = max(warmup_bars, 0)
    while cursor + test_bars <= total_rows:
        train_start_idx = cursor - train_bars
        train_end_idx = cursor - 1
        test_start_idx = cursor
        test_end_idx = cursor + test_bars - 1
        run_start_idx = max(0, test_start_idx - warmup_bars)
        run_frame = market_data.iloc[run_start_idx : test_end_idx + 1].copy()
        test_frame = market_data.iloc[test_start_idx : test_end_idx + 1].copy()

        backtest = run_backtrader_market_data(
            run_frame,
            config,
            symbol=symbol,
            initial_cash=initial_cash,
            commission=commission,
            slippage_perc=slippage_perc,
            slippage_fixed=slippage_fixed,
            evaluation_start=test_frame.iloc[0]["timestamp"],
            evaluation_end=test_frame.iloc[-1]["timestamp"],
        )
        windows.append(
            WalkForwardWindowReport(
                window_index=window_index,
                train_rows=train_bars,
                warmup_rows=len(run_frame) - len(test_frame),
                evaluation_rows=len(test_frame),
                train_start=_timestamp_string(market_data.iloc[train_start_idx]["timestamp"]),
                train_end=_timestamp_string(market_data.iloc[train_end_idx]["timestamp"]),
                test_start=_timestamp_string(test_frame.iloc[0]["timestamp"]),
                test_end=_timestamp_string(test_frame.iloc[-1]["timestamp"]),
                backtest=backtest,
            )
        )
        window_index += 1
        cursor += step_bars

    return WalkForwardReport(
        total_rows=total_rows,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
        warmup_bars=warmup_bars,
        windows=windows,
        summary=_build_walk_forward_summary(windows),
    )


def _run_slice(
    label: str,
    frame: pd.DataFrame,
    *,
    evaluation_start,
    evaluation_end,
    warmup_rows: int,
    config: SystemConfig,
    symbol: str | None,
    initial_cash: float | None,
    commission: float | None,
    slippage_perc: float | None,
    slippage_fixed: float | None,
) -> BacktestSliceReport:
    report = run_backtrader_market_data(
        frame,
        config,
        symbol=symbol,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
        evaluation_start=evaluation_start.to_pydatetime().replace(tzinfo=None)
        if hasattr(evaluation_start, "to_pydatetime")
        else evaluation_start,
        evaluation_end=evaluation_end.to_pydatetime().replace(tzinfo=None)
        if hasattr(evaluation_end, "to_pydatetime")
        else evaluation_end,
    )
    return BacktestSliceReport(
        label=label,
        total_rows=len(frame),
        warmup_rows=warmup_rows,
        evaluation_rows=len(frame) - warmup_rows,
        evaluation_start=_timestamp_string(evaluation_start),
        evaluation_end=_timestamp_string(evaluation_end),
        backtest=report,
    )


def _load_market_data(
    path: str | Path,
    config: SystemConfig,
    *,
    symbol: str | None,
) -> pd.DataFrame:
    resolved_symbol = (
        symbol
        or config.market_data.symbol
        or config.execution.symbol
        or config.market_data.mt5.symbol
        or "XAUUSD"
    )
    return CSVMarketDataLoader().load(path, symbol=resolved_symbol)


def _compare_slices(
    in_sample: BacktraderRunResult,
    out_of_sample: BacktraderRunResult,
) -> InOutSampleComparison:
    in_profit_factor = in_sample.profit_factor or 0.0
    out_profit_factor = out_of_sample.profit_factor or 0.0
    return InOutSampleComparison(
        return_pct_delta=round(out_of_sample.return_pct - in_sample.return_pct, 4),
        net_pnl_delta=round(out_of_sample.net_pnl - in_sample.net_pnl, 4),
        win_rate_delta=round(out_of_sample.win_rate - in_sample.win_rate, 4),
        max_drawdown_pct_delta=round(
            out_of_sample.max_drawdown_pct - in_sample.max_drawdown_pct,
            4,
        ),
        profit_factor_delta=round(out_profit_factor - in_profit_factor, 4),
        out_of_sample_positive=out_of_sample.net_pnl >= 0,
    )


def _build_walk_forward_summary(
    windows: list[WalkForwardWindowReport],
) -> WalkForwardSummary:
    total_windows = len(windows)
    positive_windows = sum(window.backtest.net_pnl >= 0 for window in windows)
    total_net_pnl = sum(window.backtest.net_pnl for window in windows)
    returns = [window.backtest.return_pct for window in windows]
    profit_factors = [
        window.backtest.profit_factor
        for window in windows
        if window.backtest.profit_factor is not None
    ]
    return WalkForwardSummary(
        total_windows=total_windows,
        positive_windows=positive_windows,
        positive_window_rate=round(_ratio(positive_windows, total_windows), 4),
        total_net_pnl=round(total_net_pnl, 4),
        average_return_pct=round(_ratio(sum(returns), total_windows), 4),
        best_window_return_pct=round(max(returns), 4) if returns else 0.0,
        worst_window_return_pct=round(min(returns), 4) if returns else 0.0,
        average_profit_factor=(
            round(_ratio(sum(profit_factors), len(profit_factors)), 4)
            if profit_factors
            else None
        ),
    )


def _timestamp_string(value) -> str:
    timestamp = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
    return timestamp.replace(tzinfo=None).isoformat(sep=" ")


def _ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return numerator / denominator
