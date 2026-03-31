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
    def _write_audit_source(
        self,
        path: Path,
        *,
        sample_bars: int,
        rows_processed: int,
        pullback_state_rows: int,
        pullback_signals: int,
        trades_allowed: int,
        closed_trades: int,
        signals_generated: int,
    ) -> None:
        envelope = {
            "report_type": "acceptance",
            "ready": True,
            "payload": {
                "ready": True,
                "checked_at": "2026-03-31T12:00:00+00:00",
                "summary": {"passed_checks": 10, "failed_checks": 0, "total_checks": 10},
                "checks": [
                    {
                        "name": "session_profit_concentration",
                        "passed": True,
                        "observed": 1.0,
                        "threshold": "<= 1.0",
                        "metadata": {"top_label": "us"},
                    }
                ],
                "backtest": {
                    "closed_trades": closed_trades,
                    "won_trades": max(closed_trades - 1, 0),
                    "lost_trades": 1 if closed_trades > 0 else 0,
                    "net_pnl": 1.23,
                    "profit_factor": 1.8,
                    "win_rate": 0.7,
                    "max_drawdown_pct": 0.01,
                    "decision_summary": {
                        "rows_processed": rows_processed,
                        "signals_generated": signals_generated,
                        "trades_allowed": trades_allowed,
                        "blocked_trades": max(signals_generated - trades_allowed, 0),
                        "states_by_label": {
                            "pullback_continuation": pullback_state_rows,
                            "trend_breakout": sample_bars // 1000,
                        },
                        "states_by_session": {
                            "us": {
                                "pullback_continuation": pullback_state_rows // 3,
                            }
                        },
                        "signals_by_strategy": {
                            "breakout": max(signals_generated - pullback_signals, 0),
                            "pullback": pullback_signals,
                        },
                        "blocked_reasons": {
                            "STRATEGY_DISABLED": max(signals_generated - trades_allowed, 0),
                        },
                    },
                    "trade_segmentation": {
                        "performance_by_session": {
                            "us": {
                                "closed_trades": closed_trades,
                                "net_pnl": 1.23,
                            }
                        },
                        "performance_by_exit_reason": {
                            "max_hold_timeout": {
                                "closed_trades": closed_trades,
                                "net_pnl": 1.23,
                            }
                        },
                    },
                },
                "walk_forward": {
                    "summary": {
                        "total_windows": 12,
                        "positive_window_rate": 0.9,
                    }
                },
            },
        }
        path.write_text(json.dumps(envelope), encoding="utf-8")

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

    def test_report_export_writes_latest_envelope_to_requested_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir) / "research"
            output_path = Path(tmpdir) / "exports" / "acceptance_latest.json"
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
                    "checks": [],
                },
                summary={"failed_checks": 0, "total_checks": 10},
                ready=True,
            )

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "report-export",
                    str(output_path),
                    "--report-dir",
                    str(report_dir),
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["exported"])
            self.assertEqual(payload["report_type"], "acceptance")
            self.assertTrue(output_path.exists())
            exported_envelope = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(exported_envelope["report_type"], "acceptance")
            self.assertTrue(exported_envelope["ready"])

    def test_report_audit_detects_pullback_trigger_plateau(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first_path = Path(tmpdir) / "probe_acceptance_150000_local.json"
            second_path = Path(tmpdir) / "probe_acceptance_300000_local.json"
            self._write_audit_source(
                first_path,
                sample_bars=150000,
                rows_processed=150000,
                pullback_state_rows=60000,
                pullback_signals=5,
                trades_allowed=5,
                closed_trades=3,
                signals_generated=1000,
            )
            self._write_audit_source(
                second_path,
                sample_bars=300000,
                rows_processed=300000,
                pullback_state_rows=120000,
                pullback_signals=5,
                trades_allowed=5,
                closed_trades=3,
                signals_generated=2000,
            )

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "report-audit",
                    str(first_path),
                    str(second_path),
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            payload = json.loads(buffer.getvalue())
            comparison = payload["comparison"]
            self.assertTrue(payload["audited"])
            self.assertTrue(comparison["trade_count_plateau_detected"])
            self.assertTrue(comparison["pullback_signal_plateau_detected"])
            self.assertTrue(comparison["pullback_state_rows_increasing"])
            self.assertEqual(comparison["coverage_bottleneck"], "pullback_signal_generation")
            self.assertIn("pullback.min_entry_hour", comparison["recommended_focus"])
            self.assertEqual(comparison["dominant_signal_strategy"], "breakout")

    def test_report_audit_writes_output_file_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "probe_acceptance_150000_local.json"
            output_path = Path(tmpdir) / "exports" / "coverage_audit.json"
            self._write_audit_source(
                source_path,
                sample_bars=150000,
                rows_processed=150000,
                pullback_state_rows=60000,
                pullback_signals=5,
                trades_allowed=5,
                closed_trades=3,
                signals_generated=1000,
            )

            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "report-audit",
                    str(source_path),
                    "--output",
                    str(output_path),
                ],
            ):
                with redirect_stdout(buffer):
                    main()

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["output_path"], str(output_path))
            self.assertTrue(output_path.exists())
            written_payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written_payload["report_type"], "acceptance_audit")
            self.assertEqual(written_payload["source_count"], 1)

    def test_pullback_density_probe_cli_emits_builder_payload(self) -> None:
        fake_payload = {
            "probed": True,
            "report_type": "pullback_density_probe",
            "variant_count": 2,
            "probe_summary": {"best_variant_by_rank": "entry_hour_19"},
            "results": [],
        }

        with patch(
            "xauusd_ai_system.backtest.pullback_density_probe.build_pullback_density_probe",
            return_value=fake_payload,
        ):
            buffer = StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "xauusd_ai_system.cli",
                    "pullback-density-probe",
                    "tmp/xauusd_m1_history_150000_chunked_vps_full.csv",
                ],
            ):
                with redirect_stdout(buffer):
                    main()

        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["probed"])
        self.assertEqual(payload["variant_count"], 2)
        self.assertEqual(payload["probe_summary"]["best_variant_by_rank"], "entry_hour_19")


if __name__ == "__main__":
    unittest.main()
