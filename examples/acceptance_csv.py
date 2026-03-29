from __future__ import annotations

import argparse
import json

from xauusd_ai_system.backtest.acceptance import run_acceptance_csv
from xauusd_ai_system.bootstrap import load_default_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run automatic research acceptance on a CSV file."
    )
    parser.add_argument("csv_path", help="Path to a CSV file with timestamp/open/high/low/close columns.")
    parser.add_argument("--symbol", default=None, help="Optional trading symbol label.")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Chronological fraction used for the in-sample split.")
    parser.add_argument("--warmup-bars", type=int, default=720, help="Bars to prepend before test windows for feature warmup.")
    parser.add_argument("--train-bars", type=int, default=5000, help="Bars in each rolling walk-forward training window.")
    parser.add_argument("--test-bars", type=int, default=1000, help="Bars in each rolling walk-forward test window.")
    parser.add_argument("--step-bars", type=int, default=None, help="Bars to move the walk-forward window each iteration. Defaults to test-bars.")
    parser.add_argument("--initial-cash", type=float, default=None, help="Override backtest.initial_cash from config.")
    parser.add_argument("--commission", type=float, default=None, help="Override backtest.commission from config.")
    parser.add_argument("--slippage-perc", type=float, default=None, help="Override backtest.slippage_perc from config.")
    parser.add_argument("--slippage-fixed", type=float, default=None, help="Override backtest.slippage_fixed from config.")
    args = parser.parse_args()

    report = run_acceptance_csv(
        args.csv_path,
        load_default_config(),
        symbol=args.symbol,
        train_ratio=args.train_ratio,
        warmup_bars=args.warmup_bars,
        train_bars=args.train_bars,
        test_bars=args.test_bars,
        step_bars=args.step_bars,
        initial_cash=args.initial_cash,
        commission=args.commission,
        slippage_perc=args.slippage_perc,
        slippage_fixed=args.slippage_fixed,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
