from __future__ import annotations

import csv
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import SystemConfig
from xauusd_ai_system.data.mt5_history_exporter import MT5HistoryCsvExporter


class FakeSymbolInfo:
    point = 0.01


class FakeMT5:
    TIMEFRAME_M1 = 1

    def __init__(self) -> None:
        self.initialized = False
        self.shutdown_calls = 0

    def initialize(self, **kwargs):
        self.initialized = True
        return True

    def shutdown(self):
        self.shutdown_calls += 1
        return None

    def last_error(self):
        return (0, "OK")

    def symbol_select(self, symbol, enable):
        return True

    def symbol_info(self, symbol):
        return FakeSymbolInfo()

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        return [
            {
                "time": 1711731600,
                "open": 3000.0,
                "high": 3001.0,
                "low": 2999.5,
                "close": 3000.5,
                "tick_volume": 12,
                "spread": 25,
                "real_volume": 0,
            },
            {
                "time": 1711731660,
                "open": 3000.5,
                "high": 3001.2,
                "low": 3000.1,
                "close": 3001.0,
                "tick_volume": 10,
                "spread": 30,
                "real_volume": 0,
            },
        ]


class MT5HistoryCsvExporterTests(unittest.TestCase):
    def test_export_csv_writes_normalized_spread_and_quotes(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.market_data.mt5.timeframe = "M1"
        config.market_data.mt5.history_bars = 100

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "history.csv"
            result = MT5HistoryCsvExporter(config, mt5_module=FakeMT5()).export_csv(
                output_path,
                bars=2,
            )

            self.assertEqual(result.bars_exported, 2)
            self.assertEqual(result.point, 0.01)
            self.assertTrue(output_path.exists())

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["symbol"], "XAUUSD")
            self.assertAlmostEqual(float(rows[0]["spread"]), 0.25)
            self.assertAlmostEqual(float(rows[0]["bid"]), 3000.375)
            self.assertAlmostEqual(float(rows[0]["ask"]), 3000.625)
            self.assertIn("+00:00", rows[0]["timestamp"])


if __name__ == "__main__":
    unittest.main()
