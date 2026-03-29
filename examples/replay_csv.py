from __future__ import annotations

import argparse
import json

from xauusd_ai_system.bootstrap import load_default_config
from xauusd_ai_system.backtest.runner import HistoricalReplayRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a historical CSV dataset.")
    parser.add_argument("csv_path", help="Path to a CSV file with timestamp/open/high/low/close columns.")
    parser.add_argument("--symbol", default="XAUUSD", help="Trading symbol label.")
    parser.add_argument("--equity", type=float, default=10_000.0, help="Starting equity.")
    args = parser.parse_args()

    runner = HistoricalReplayRunner(load_default_config())
    summary = runner.run_csv(args.csv_path, symbol=args.symbol, equity=args.equity)
    print(json.dumps(summary.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
