from __future__ import annotations

import csv
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
        self._last_error = (0, "OK")

    def initialize(self, **kwargs):
        self.initialized = True
        self._last_error = (0, "OK")
        return True

    def shutdown(self):
        self.shutdown_calls += 1
        return None

    def last_error(self):
        return self._last_error

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


class FakeChunkedMT5(FakeMT5):
    def __init__(self, total_bars: int) -> None:
        super().__init__()
        self.calls: list[tuple[str, int, int, int]] = []
        self._bars = []
        base_timestamp = 1711731600
        for index in range(total_bars):
            open_price = 3000.0 + index
            self._bars.append(
                {
                    "time": base_timestamp + (index * 60),
                    "open": open_price,
                    "high": open_price + 1.0,
                    "low": open_price - 0.5,
                    "close": open_price + 0.25,
                    "tick_volume": 10 + index,
                    "spread": 20 + index,
                    "real_volume": 0,
                }
            )

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self.calls.append((symbol, timeframe, start, count))
        total = len(self._bars)
        if start < 0 or count <= 0:
            self._last_error = (-2, "Terminal: Invalid params")
            return None
        if start >= total:
            self._last_error = (-1, "Terminal: Call failed")
            return None

        newest_end = total - start
        oldest_start = max(0, newest_end - count)
        rows = self._bars[oldest_start:newest_end]
        self._last_error = (0, "OK")
        return rows


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

    def test_export_csv_fetches_recent_history_in_batches(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.market_data.mt5.timeframe = "M1"
        fake_mt5 = FakeChunkedMT5(total_bars=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "history.csv"
            with patch.object(MT5HistoryCsvExporter, "MAX_BARS_PER_REQUEST", 2):
                result = MT5HistoryCsvExporter(config, mt5_module=fake_mt5).export_csv(
                    output_path,
                    bars=5,
                )

            self.assertEqual(result.bars_exported, 5)
            self.assertEqual(
                fake_mt5.calls,
                [
                    ("XAUUSD", fake_mt5.TIMEFRAME_M1, 0, 2),
                    ("XAUUSD", fake_mt5.TIMEFRAME_M1, 2, 2),
                    ("XAUUSD", fake_mt5.TIMEFRAME_M1, 4, 1),
                ],
            )

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 5)
            self.assertEqual(
                [row["timestamp"] for row in rows],
                [
                    "2024-03-29T17:00:00+00:00",
                    "2024-03-29T17:01:00+00:00",
                    "2024-03-29T17:02:00+00:00",
                    "2024-03-29T17:03:00+00:00",
                    "2024-03-29T17:04:00+00:00",
                ],
            )

    def test_export_csv_raises_clear_error_when_terminal_history_is_short(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.market_data.mt5.timeframe = "M1"
        fake_mt5 = FakeChunkedMT5(total_bars=4)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "history.csv"
            with patch.object(MT5HistoryCsvExporter, "MAX_BARS_PER_REQUEST", 2):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "after collecting 4 of 5 bars",
                ):
                    MT5HistoryCsvExporter(config, mt5_module=fake_mt5).export_csv(
                        output_path,
                        bars=5,
                    )

            self.assertFalse(output_path.exists())

    def test_probe_capacity_reports_exact_available_history(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.market_data.mt5.timeframe = "M1"
        fake_mt5 = FakeChunkedMT5(total_bars=5)

        with patch.object(MT5HistoryCsvExporter, "MAX_BARS_PER_REQUEST", 2):
            result = MT5HistoryCsvExporter(config, mt5_module=fake_mt5).probe_capacity(
                batch_size=2,
                max_bars=10,
            )

        self.assertEqual(result.bars_available, 5)
        self.assertEqual(result.batches_loaded, 3)
        self.assertTrue(result.probe_complete)
        self.assertEqual(result.oldest_timestamp, "2024-03-29T17:00:00+00:00")
        self.assertEqual(result.newest_timestamp, "2024-03-29T17:04:00+00:00")
        self.assertEqual(result.stopped_reason, "requested batch_size=2, returned=1")

    def test_probe_capacity_marks_limit_reached_when_probe_cap_hits(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.market_data.mt5.timeframe = "M1"
        fake_mt5 = FakeChunkedMT5(total_bars=20)

        result = MT5HistoryCsvExporter(config, mt5_module=fake_mt5).probe_capacity(
            batch_size=5,
            max_bars=10,
        )

        self.assertEqual(result.bars_available, 10)
        self.assertEqual(result.batches_loaded, 2)
        self.assertFalse(result.probe_complete)
        self.assertEqual(result.stopped_reason, "probe_limit_reached max_bars=10")


if __name__ == "__main__":
    unittest.main()
