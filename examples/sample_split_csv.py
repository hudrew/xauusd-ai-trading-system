from __future__ import annotations

import argparse
import json

from xauusd_ai_system.backtest.evaluation import run_in_out_sample_csv
from xauusd_ai_system.bootstrap import load_default_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run chronological in-sample / out-of-sample evaluation on a CSV file."
    )
    parser.add_argument("csv_path", help="Path to a CSV file with timestamp/open/high/low/close columns.")
    parser.add_argument("--symbol", default=None, help="Optional trading symbol label.")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Chronological fraction used for the in-sample split.")
    parser.add_argument("--warmup-bars", type=int, default=720, help="Bars to prepend before the out-of-sample slice for feature warmup.")
    parser.add_argument("--initial-cash", type=float, default=None, help="Override backtest.initial_cash from config.")
    parser.add_argument("--commission", type=float, default=None, help="Override backtest.commission from config.")
    parser.add_argument("--slippage-perc", type=float, default=None, help="Override backtest.slippage_perc from config.")
    parser.add_argument("--slippage-fixed", type=float, default=None, help="Override backtest.slippage_fixed from config.")
    args = parser.parse_args()

    report = run_in_out_sample_csv(
        args.csv_path,
        load_default_config(),
        symbol=args.symbol,
        train_ratio=args.train_ratio,
        warmup_bars=args.warmup_bars,
        initial_cash=args.initial_cash,
        commission=args.commission,
        slippage_perc=args.slippage_perc,
        slippage_fixed=args.slippage_fixed,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
