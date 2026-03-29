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


class DeployGateCliTests(unittest.TestCase):
    def test_deploy_gate_uses_latest_acceptance_archive(self) -> None:
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
                {"checked_at": "2026-03-29T12:00:00+00:00", "checks": []},
                summary={"passed_checks": 10, "failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "deploy-gate",
                    "--report-dir",
                    str(report_dir),
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["environment"], "dev")
            self.assertTrue(payload["ready"])
            self.assertEqual(payload["acceptance"]["record"]["report_type"], "acceptance")

    def test_deploy_gate_strict_exits_when_not_ready(self) -> None:
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
                summary={"passed_checks": 9, "failed_checks": 1, "total_checks": 10},
                ready=False,
            )

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "deploy-gate",
                    "--strict",
                    "--report-dir",
                    str(report_dir),
                ],
            ):
                with redirect_stdout(buffer):
                    with self.assertRaises(SystemExit) as ctx:
                        main()

            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
