from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import ReportArchiveConfig
from xauusd_ai_system.storage.report_archive import FileReportArchive
from xauusd_ai_system.storage.report_catalog import FileReportCatalog


class FileReportCatalogTests(unittest.TestCase):
    def test_list_records_returns_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportArchiveConfig(
                enabled=True,
                base_dir=str(Path(tmpdir) / "research"),
                write_latest=True,
            )
            archive = FileReportArchive(config)
            archive.save(
                "acceptance",
                {"checked_at": "2026-03-29T10:00:00+00:00", "checks": []},
                summary={"failed_checks": 1, "total_checks": 10},
                ready=False,
            )
            latest = archive.save(
                "acceptance",
                {"checked_at": "2026-03-29T11:00:00+00:00", "checks": []},
                summary={"failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            self.assertIsNotNone(latest)
            catalog = FileReportCatalog(config)
            records = catalog.list_records(report_type="acceptance", limit=10)

            self.assertEqual(len(records), 2)
            self.assertTrue(records[0].ready)
            self.assertFalse(records[1].ready)
            self.assertNotEqual(records[0].archive_path, records[1].archive_path)

    def test_latest_report_returns_failed_check_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportArchiveConfig(
                enabled=True,
                base_dir=str(Path(tmpdir) / "research"),
                write_latest=True,
            )
            archive = FileReportArchive(config)
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T12:00:00+00:00",
                    "checks": [
                        {"name": "total_profit_factor", "passed": False},
                        {"name": "session_profit_concentration", "passed": True},
                    ],
                },
                summary={"failed_checks": 1, "total_checks": 10},
                ready=False,
            )

            catalog = FileReportCatalog(config)
            details = catalog.latest_report(report_type="acceptance")

            self.assertIsNotNone(details)
            assert details is not None
            self.assertEqual(details.checked_at, "2026-03-29T12:00:00+00:00")
            self.assertEqual(details.failed_check_names, ["total_profit_factor"])

    def test_build_trend_counts_recent_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportArchiveConfig(
                enabled=True,
                base_dir=str(Path(tmpdir) / "research"),
                write_latest=True,
            )
            archive = FileReportArchive(config)
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T10:00:00+00:00",
                    "checks": [{"name": "close_month_profit_concentration", "passed": False}],
                },
                summary={"failed_checks": 1, "total_checks": 10},
                ready=False,
            )
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T11:00:00+00:00",
                    "checks": [{"name": "total_profit_factor", "passed": False}],
                },
                summary={"failed_checks": 1, "total_checks": 10},
                ready=False,
            )
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T12:00:00+00:00",
                    "checks": [],
                },
                summary={"failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            catalog = FileReportCatalog(config)
            trend = catalog.build_trend(report_type="acceptance", limit=3)

            self.assertEqual(trend.total_records, 3)
            self.assertEqual(trend.ready_records, 1)
            self.assertEqual(trend.failed_records, 2)
            self.assertAlmostEqual(trend.readiness_rate, 0.3333, places=4)
            self.assertEqual(trend.failed_check_counts["close_month_profit_concentration"], 1)
            self.assertEqual(trend.failed_check_counts["total_profit_factor"], 1)
            self.assertTrue(trend.recent_records[0]["ready"])


if __name__ == "__main__":
    unittest.main()
