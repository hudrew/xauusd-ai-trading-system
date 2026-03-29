from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import ReportArchiveConfig, SystemConfig
from xauusd_ai_system.deployment.gate import DeploymentGateRunner
from xauusd_ai_system.preflight.base import PreflightCheck, PreflightReport
from xauusd_ai_system.storage.report_archive import FileReportArchive


class StaticRunner:
    def __init__(self, report: PreflightReport) -> None:
        self.report = report

    def run(self) -> PreflightReport:
        return self.report


class DeploymentGateRunnerTests(unittest.TestCase):
    def test_live_gate_ready_with_fresh_acceptance_and_live_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig()
            config.runtime.environment = "prod"
            config.runtime.dry_run = False
            config.execution.platform = "mt5"
            config.market_data.platform = "mt5"

            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(Path(tmpdir) / "research"),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-03-29T10:00:00+00:00", "checks": []},
                summary={"passed_checks": 10, "failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            ready_report = PreflightReport(
                platform="mt5",
                ready=True,
                checks=[PreflightCheck(name="ok", passed=True, detail="ok")],
            )
            runner = DeploymentGateRunner(
                config,
                report_dir=str(Path(tmpdir) / "research"),
                host_check_runner=StaticRunner(ready_report),
                preflight_runner=StaticRunner(ready_report),
                now=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            )

            report = runner.run()

            self.assertTrue(report.ready)
            self.assertEqual(report.summary.failed_checks, 0)
            self.assertTrue(any(item.name == "host_check_ready" and item.passed for item in report.checks))
            self.assertTrue(any(item.name == "preflight_ready" and item.passed for item in report.checks))

    def test_gate_fails_when_acceptance_report_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig()
            config.runtime.dry_run = True

            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(Path(tmpdir) / "research"),
                    write_latest=True,
                )
            )
            stale_checked_at = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
            archive.save(
                "acceptance",
                {"checked_at": stale_checked_at.isoformat(), "checks": []},
                summary={"passed_checks": 10, "failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            runner = DeploymentGateRunner(
                config,
                report_dir=str(Path(tmpdir) / "research"),
                max_acceptance_age_hours=72.0,
                now=stale_checked_at + timedelta(hours=96),
            )
            report = runner.run()

            self.assertFalse(report.ready)
            freshness_check = next(
                item for item in report.checks if item.name == "acceptance_report_freshness"
            )
            self.assertFalse(freshness_check.passed)

    def test_dry_run_gate_skips_live_checks_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig()
            config.runtime.environment = "paper"
            config.runtime.dry_run = True
            config.execution.platform = "mt5"
            config.market_data.platform = "mt5"

            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(Path(tmpdir) / "research"),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-03-29T10:00:00+00:00", "checks": []},
                summary={"passed_checks": 10, "failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            runner = DeploymentGateRunner(
                config,
                report_dir=str(Path(tmpdir) / "research"),
                now=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            skipped_names = {item.name for item in report.checks if item.severity == "info"}
            self.assertIn("host_check_skipped", skipped_names)
            self.assertIn("preflight_skipped", skipped_names)

    def test_gate_fails_when_latest_acceptance_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig()
            config.runtime.dry_run = True

            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(Path(tmpdir) / "research"),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-03-29T10:00:00+00:00",
                    "checks": [{"name": "total_profit_factor", "passed": False}],
                },
                summary={"passed_checks": 9, "failed_checks": 1, "total_checks": 10},
                ready=False,
            )

            runner = DeploymentGateRunner(
                config,
                report_dir=str(Path(tmpdir) / "research"),
                now=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertFalse(report.ready)
            ready_check = next(
                item for item in report.checks if item.name == "acceptance_report_ready"
            )
            self.assertFalse(ready_check.passed)


if __name__ == "__main__":
    unittest.main()
