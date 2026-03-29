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
from xauusd_ai_system.config.schema import ReportArchiveConfig
from xauusd_ai_system.storage.report_archive import FileReportArchive


class ReportCliTests(unittest.TestCase):
    def test_reports_latest_emits_archived_failure_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir) / "research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T12:00:00+00:00",
                    "checks": [{"name": "total_profit_factor", "passed": False}],
                },
                summary={"failed_checks": 1, "total_checks": 10},
                ready=False,
            )

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "reports",
                    "latest",
                    "--report-dir",
                    str(report_dir),
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["view"], "latest")
            self.assertEqual(payload["result"]["failed_check_names"], ["total_profit_factor"])
            self.assertFalse(payload["result"]["record"]["ready"])

    def test_report_import_archives_latest_envelope_into_target_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            target_dir = Path(tmpdir) / "target"
            source_archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(source_dir),
                    write_latest=True,
                )
            )
            source_record = source_archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T12:00:00+00:00",
                    "checks": [],
                },
                summary={"failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            self.assertIsNotNone(source_record)
            source_latest = source_dir / "acceptance" / "latest.json"

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "report-import",
                    str(source_latest),
                    "--report-dir",
                    str(target_dir),
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["imported"])
            self.assertEqual(payload["report_type"], "acceptance")
            self.assertEqual(payload["checked_at"], "2026-03-29T12:00:00+00:00")

            imported_latest = target_dir / "acceptance" / "latest.json"
            self.assertTrue(imported_latest.exists())
            imported_envelope = json.loads(imported_latest.read_text(encoding="utf-8"))
            self.assertEqual(
                imported_envelope["payload"]["checked_at"],
                "2026-03-29T12:00:00+00:00",
            )
            self.assertTrue(imported_envelope["ready"])


if __name__ == "__main__":
    unittest.main()
