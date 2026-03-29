from __future__ import annotations

import csv
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import pandas as pd  # noqa: F401
except ImportError:
    pd = None
    CSVMarketDataLoader = None
else:
    from xauusd_ai_system.data.csv_loader import CSVMarketDataLoader


@unittest.skipIf(pd is None, "pandas is not installed")
class CSVMarketDataLoaderTests(unittest.TestCase):
    def test_load_fills_basic_market_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "sample.csv"
            rows = [
                ["timestamp", "open", "high", "low", "close"],
                ["2026-03-29 09:00:00", "3000.0", "3001.0", "2999.5", "3000.5"],
                ["2026-03-29 09:01:00", "3000.5", "3001.2", "3000.2", "3001.0"],
            ]
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)

            frame = CSVMarketDataLoader().load(csv_path)
            self.assertIn("bid", frame.columns)
            self.assertIn("ask", frame.columns)
            self.assertIn("session_tag", frame.columns)
            self.assertIn("news_level", frame.columns)
            self.assertIn("event_category", frame.columns)
            self.assertIn("event_source", frame.columns)
            self.assertEqual(frame.iloc[0]["symbol"], "XAUUSD")
            self.assertEqual(frame.iloc[0]["news_level"], "none")


if __name__ == "__main__":
    unittest.main()
