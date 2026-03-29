from __future__ import annotations

import argparse
import json

from xauusd_ai_system.backtest.backtrader_runner import run_backtrader_csv
from xauusd_ai_system.bootstrap import load_default_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Backtrader CSV execution backtest.")
    parser.add_argument("csv_path", help="Path to a CSV file with timestamp/open/high/low/close columns.")
    parser.add_argument("--symbol", default=None, help="Optional trading symbol label.")
    parser.add_argument("--initial-cash", type=float, default=None, help="Override backtest.initial_cash from config.")
    parser.add_argument("--commission", type=float, default=None, help="Override backtest.commission from config.")
    parser.add_argument("--slippage-perc", type=float, default=None, help="Override backtest.slippage_perc from config.")
    parser.add_argument("--slippage-fixed", type=float, default=None, help="Override backtest.slippage_fixed from config.")
    args = parser.parse_args()

    report = run_backtrader_csv(
        args.csv_path,
        load_default_config(),
        symbol=args.symbol,
        initial_cash=args.initial_cash,
        commission=args.commission,
        slippage_perc=args.slippage_perc,
        slippage_fixed=args.slippage_fixed,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
