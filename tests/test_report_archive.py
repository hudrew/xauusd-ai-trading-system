from __future__ import annotations

import json
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import ReportArchiveConfig
from xauusd_ai_system.storage.report_archive import FileReportArchive


class FileReportArchiveTests(unittest.TestCase):
    def test_save_writes_archive_latest_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(Path(tmpdir) / "research"),
                    write_latest=True,
                )
            )
            record = archive.save(
                "acceptance",
                {"ready": False, "summary": {"failed_checks": 1}},
                summary={"failed_checks": 1, "total_checks": 10},
                ready=False,
            )

            self.assertIsNotNone(record)
            archive_path = Path(record.archive_path)
            latest_path = Path(record.latest_path) if record.latest_path is not None else None
            index_path = Path(tmpdir) / "research" / "index.jsonl"

            self.assertTrue(archive_path.exists())
            self.assertIsNotNone(latest_path)
            self.assertTrue(latest_path.exists())
            self.assertTrue(index_path.exists())

            archive_payload = json.loads(archive_path.read_text(encoding="utf-8"))
            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            index_rows = [
                json.loads(line)
                for line in index_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual(archive_payload["report_type"], "acceptance")
            self.assertFalse(archive_payload["ready"])
            self.assertEqual(latest_payload["summary"]["failed_checks"], 1)
            self.assertEqual(index_rows[-1]["report_type"], "acceptance")
            self.assertEqual(index_rows[-1]["summary"]["total_checks"], 10)

    def test_save_returns_none_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=False,
                    base_dir=str(Path(tmpdir) / "research"),
                    write_latest=True,
                )
            )
            record = archive.save("acceptance", {"ready": True})

            self.assertIsNone(record)
            self.assertFalse((Path(tmpdir) / "research").exists())


if __name__ == "__main__":
    unittest.main()
