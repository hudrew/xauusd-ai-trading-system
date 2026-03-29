from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.cli import main
from xauusd_ai_system.data.mt5_history_exporter import MT5HistoryExportResult


class ExportMt5HistoryCliTests(unittest.TestCase):
    def test_export_mt5_history_emits_export_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "history.csv"
            buffer = StringIO()

            with patch(
                "xauusd_ai_system.data.mt5_history_exporter.MT5HistoryCsvExporter.export_csv",
                return_value=MT5HistoryExportResult(
                    output_path=str(output_path),
                    symbol="XAUUSD",
                    timeframe="M1",
                    bars_requested=20000,
                    bars_exported=19980,
                    point=0.01,
                ),
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "xauusd_ai_system.cli",
                        "export-mt5-history",
                        str(output_path),
                    ],
                ):
                    with redirect_stdout(buffer):
                        main()

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["output_path"], str(output_path))
            self.assertEqual(payload["symbol"], "XAUUSD")
            self.assertEqual(payload["bars_exported"], 19980)


if __name__ == "__main__":
    unittest.main()
