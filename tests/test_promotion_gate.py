from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import ReportArchiveConfig, SystemConfig
from xauusd_ai_system.deployment.promotion_gate import PromotionGateRunner
from xauusd_ai_system.storage.report_archive import FileReportArchive


class PromotionGateRunnerTests(unittest.TestCase):
    def test_promotion_gate_ready_with_candidate_acceptance_and_current_daily_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                        "out_of_sample_net_pnl": 2.47,
                        "out_of_sample_profit_factor": 1.7490,
                        "walk_forward_positive_window_rate": 0.9960,
                        "close_month_profit_concentration": 0.6129,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            config = SystemConfig()
            config.runtime.environment = "paper"
            config.runtime.dry_run = True
            config.execution.platform = "mt5"
            config.market_data.platform = "mt5"

            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                require_candidate_daily_check=False,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertEqual(report.summary.failed_checks, 0)
            self.assertEqual(report.candidate_acceptance["headline_metrics"]["profit_factor"], 2.0618)
            self.assertEqual(report.current_daily_check["health"], "ok")

    def test_promotion_gate_can_require_current_execution_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                        "out_of_sample_net_pnl": 2.47,
                        "out_of_sample_profit_factor": 1.7490,
                        "walk_forward_positive_window_rate": 0.9960,
                        "close_month_profit_concentration": 0.6129,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            current_execution_audit_path = base_dir / "current_execution_audit_latest.json"
            self._write_execution_audit(
                current_execution_audit_path,
                generated_at="2026-04-01T11:35:00+00:00",
                execution_chain_visible=True,
                reconcile_chain_visible=True,
                close_reason_complete=True,
                execution_attempt_count=4,
                execution_sync_count=4,
                accepted_attempt_count=2,
                reconcile_sync_count=2,
                close_event_count=1,
                attention_sync_count=0,
                missing_close_reason_count=0,
            )

            config = SystemConfig()
            config.runtime.environment = "paper"
            config.runtime.dry_run = True
            config.execution.platform = "mt5"
            config.market_data.platform = "mt5"

            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                current_execution_audit_path=str(current_execution_audit_path),
                require_candidate_daily_check=False,
                require_current_execution_audit=True,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertEqual(report.summary.failed_checks, 0)
            self.assertIsNotNone(report.current_execution_audit)
            self.assertEqual(report.current_execution_audit["promotion_gate_source_kind"], "path")
            self.assertTrue(
                any(
                    item.name == "current_execution_audit_execution_chain_visible" and item.passed
                    for item in report.checks
                )
            )

    def test_promotion_gate_can_reuse_execution_audit_embedded_in_daily_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                        "out_of_sample_net_pnl": 2.47,
                        "out_of_sample_profit_factor": 1.7490,
                        "walk_forward_positive_window_rate": 0.9960,
                        "close_month_profit_concentration": 0.6129,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            embedded_execution_audit = self._execution_audit_payload(
                generated_at="2026-04-01T11:35:00+00:00",
                execution_chain_visible=True,
                reconcile_chain_visible=True,
                close_reason_complete=True,
                execution_attempt_count=4,
                execution_sync_count=4,
                accepted_attempt_count=2,
                reconcile_sync_count=2,
                close_event_count=1,
                attention_sync_count=0,
                missing_close_reason_count=0,
            )
            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                        "execution_audit": {
                            "available": True,
                            "health": "ok",
                            "generated_at": embedded_execution_audit["generated_at"],
                            "issue_count": 0,
                            "issues": [],
                            "summary": embedded_execution_audit["summary"],
                            "verdict": embedded_execution_audit["verdict"],
                            "latest_close_event": None,
                            "recent_attention_sync_count": 0,
                            "error": None,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = SystemConfig()
            config.runtime.environment = "paper"
            config.runtime.dry_run = True
            config.execution.platform = "mt5"
            config.market_data.platform = "mt5"

            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                require_candidate_daily_check=False,
                require_current_execution_audit=True,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertIsNotNone(report.current_execution_audit)
            self.assertEqual(report.current_execution_audit["verdict"]["reconcile_chain_visible"], True)
            self.assertEqual(report.current_execution_audit["promotion_gate_source_kind"], "embedded")
            self.assertEqual(
                report.current_execution_audit["promotion_gate_source"],
                "current_daily_check.execution_audit",
            )
            self.assertTrue(
                any(
                    item.name == "current_execution_audit_available"
                    and item.metadata.get("embedded_source") == "current_daily_check.execution_audit"
                    for item in report.checks
                )
            )

    def test_promotion_gate_accepts_bom_prefixed_daily_check_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                        "out_of_sample_net_pnl": 2.47,
                        "out_of_sample_profit_factor": 1.7490,
                        "walk_forward_positive_window_rate": 0.9960,
                        "close_month_profit_concentration": 0.6129,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8-sig",
            )

            config = SystemConfig()
            config.runtime.environment = "paper"
            config.runtime.dry_run = True

            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                require_candidate_daily_check=False,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertEqual(report.current_daily_check["health"], "ok")

    def test_promotion_gate_accepts_windows_powershell_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                        "out_of_sample_net_pnl": 2.47,
                        "out_of_sample_profit_factor": 1.7490,
                        "walk_forward_positive_window_rate": 0.9960,
                        "close_month_profit_concentration": 0.6129,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T19:30:00.0400831+08:00",
                        "health": "ok",
                        "issue_count": 0,
                        "execution_audit": {
                            "available": True,
                            "health": "ok",
                            "generated_at": "2026-04-01T19:35:00.0400831+08:00",
                            "issue_count": 0,
                            "issues": [],
                            "summary": {
                                "execution_attempt_count": 4,
                                "execution_sync_count": 4,
                                "accepted_attempt_count": 2,
                                "reconcile_sync_count": 2,
                                "close_event_count": 1,
                                "attention_sync_count": 0,
                                "missing_close_reason_count": 0,
                                "close_reason_coverage_rate": 1.0,
                            },
                            "verdict": {
                                "execution_chain_visible": True,
                                "reconcile_chain_visible": True,
                                "close_reason_complete": True,
                                "close_reason_stable": True,
                            },
                            "latest_close_event": None,
                            "recent_attention_sync_count": 0,
                            "error": None,
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = SystemConfig()
            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                require_candidate_daily_check=False,
                require_current_execution_audit=True,
                now=datetime(2026, 4, 1, 11, 40, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertTrue(
                any(item.name == "current_daily_check_freshness" and item.passed for item in report.checks)
            )
            self.assertTrue(
                any(
                    item.name == "current_execution_audit_freshness" and item.passed
                    for item in report.checks
                )
            )

    def test_promotion_gate_merges_partial_record_headline_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-04-01T10:00:00+00:00",
                    "checks": [],
                    "summary": {
                        "headline_metrics": {
                            "net_pnl": 2.97,
                            "profit_factor": 2.0618,
                            "closed_trades": 18,
                            "out_of_sample_net_pnl": 2.47,
                            "out_of_sample_profit_factor": 1.7490,
                            "walk_forward_positive_window_rate": 0.9960,
                            "close_month_profit_concentration": 0.6129,
                            "session_profit_concentration": 1.0,
                        }
                    },
                },
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            config = SystemConfig()
            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                require_candidate_daily_check=False,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertEqual(
                report.candidate_acceptance["headline_metrics"]["close_month_profit_concentration"],
                0.6129,
            )
            self.assertEqual(
                report.candidate_acceptance["headline_metrics"]["session_profit_concentration"],
                1.0,
            )

    def test_promotion_gate_derives_profit_concentration_from_acceptance_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {
                    "checked_at": "2026-04-01T10:00:00+00:00",
                    "backtest": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "max_drawdown_pct": 0.0002,
                        "closed_trades": 18,
                        "won_trades": 13,
                        "lost_trades": 5,
                        "win_rate": 0.7222,
                        "decision_summary": {
                            "signals_generated": 10414,
                            "signals_by_strategy": {"pullback": 26},
                            "trades_allowed": 26,
                            "blocked_trades": 10388,
                        },
                    },
                    "sample_split": {
                        "out_of_sample": {
                            "backtest": {
                                "net_pnl": 2.47,
                                "profit_factor": 1.7490,
                                "max_drawdown_pct": 0.0002,
                            }
                        }
                    },
                    "walk_forward": {
                        "summary": {
                            "total_windows": 741,
                            "positive_window_rate": 0.9960,
                        }
                    },
                    "checks": [
                        {
                            "name": "close_month_profit_concentration",
                            "observed": 0.6129,
                            "passed": True,
                        },
                        {
                            "name": "session_profit_concentration",
                            "observed": 1.0,
                            "passed": True,
                        },
                    ],
                },
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            config = SystemConfig()
            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                require_candidate_daily_check=False,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertTrue(report.ready)
            self.assertEqual(
                report.candidate_acceptance["headline_metrics"]["close_month_profit_concentration"],
                0.6129,
            )
            self.assertEqual(
                report.candidate_acceptance["headline_metrics"]["session_profit_concentration"],
                1.0,
            )

    def test_promotion_gate_fails_when_candidate_metrics_do_not_meet_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 1.20,
                        "profit_factor": 1.30,
                        "closed_trades": 12,
                        "out_of_sample_net_pnl": 0.40,
                        "out_of_sample_profit_factor": 1.10,
                        "walk_forward_positive_window_rate": 0.70,
                        "close_month_profit_concentration": 0.72,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            config = SystemConfig()
            config.runtime.environment = "paper"
            config.runtime.dry_run = True

            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertFalse(report.ready)
            failed_names = {item.name for item in report.checks if not item.passed}
            self.assertIn("candidate_total_profit_factor_threshold", failed_names)
            self.assertIn("candidate_closed_trades_threshold", failed_names)
            self.assertIn("candidate_close_month_profit_concentration_threshold", failed_names)

    def test_promotion_gate_fails_when_required_execution_audit_is_not_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            archive = FileReportArchive(
                ReportArchiveConfig(
                    enabled=True,
                    base_dir=str(candidate_report_dir),
                    write_latest=True,
                )
            )
            archive.save(
                "acceptance",
                {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                summary={
                    "passed_checks": 10,
                    "failed_checks": 0,
                    "total_checks": 10,
                    "headline_metrics": {
                        "net_pnl": 2.97,
                        "profit_factor": 2.0618,
                        "closed_trades": 18,
                        "out_of_sample_net_pnl": 2.47,
                        "out_of_sample_profit_factor": 1.7490,
                        "walk_forward_positive_window_rate": 0.9960,
                        "close_month_profit_concentration": 0.6129,
                        "session_profit_concentration": 1.0,
                    },
                },
                ready=True,
            )

            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            current_execution_audit_path = base_dir / "current_execution_audit_latest.json"
            self._write_execution_audit(
                current_execution_audit_path,
                generated_at="2026-04-01T11:35:00+00:00",
                execution_chain_visible=True,
                reconcile_chain_visible=False,
                close_reason_complete=False,
                execution_attempt_count=4,
                execution_sync_count=2,
                accepted_attempt_count=2,
                reconcile_sync_count=0,
                close_event_count=0,
                attention_sync_count=1,
                missing_close_reason_count=0,
            )

            config = SystemConfig()
            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                current_execution_audit_path=str(current_execution_audit_path),
                require_current_execution_audit=True,
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertFalse(report.ready)
            failed_names = {item.name for item in report.checks if not item.passed}
            self.assertIn("current_execution_audit_reconcile_chain_visible", failed_names)
            self.assertIn("current_execution_audit_attention_sync_threshold", failed_names)

    def test_promotion_gate_includes_baseline_comparison_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            candidate_report_dir = base_dir / "candidate_research"
            baseline_report_dir = base_dir / "baseline_research"
            current_daily_check_path = base_dir / "current_daily_check_latest.json"
            current_daily_check_path.write_text(
                json.dumps(
                    {
                        "checked_at": "2026-04-01T11:30:00+00:00",
                        "health": "ok",
                        "issue_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            for report_dir, net_pnl in (
                (candidate_report_dir, 2.97),
                (baseline_report_dir, 2.69),
            ):
                archive = FileReportArchive(
                    ReportArchiveConfig(
                        enabled=True,
                        base_dir=str(report_dir),
                        write_latest=True,
                    )
                )
                archive.save(
                    "acceptance",
                    {"checked_at": "2026-04-01T10:00:00+00:00", "checks": []},
                    summary={
                        "passed_checks": 10,
                        "failed_checks": 0,
                        "total_checks": 10,
                        "headline_metrics": {
                            "net_pnl": net_pnl,
                            "profit_factor": 2.0,
                            "closed_trades": 18,
                            "out_of_sample_net_pnl": 2.0,
                            "out_of_sample_profit_factor": 1.7,
                            "walk_forward_positive_window_rate": 0.99,
                            "close_month_profit_concentration": 0.61,
                            "session_profit_concentration": 1.0,
                        },
                    },
                    ready=True,
                )

            config = SystemConfig()
            runner = PromotionGateRunner(
                config,
                candidate_report_dir=str(candidate_report_dir),
                baseline_report_dir=str(baseline_report_dir),
                current_daily_check_path=str(current_daily_check_path),
                now=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            )
            report = runner.run()

            self.assertIsNotNone(report.comparison)
            self.assertAlmostEqual(report.comparison["headline_metric_deltas"]["net_pnl"], 0.28)

    @staticmethod
    def _write_execution_audit(
        path: Path,
        *,
        generated_at: str,
        execution_chain_visible: bool,
        reconcile_chain_visible: bool,
        close_reason_complete: bool,
        execution_attempt_count: int,
        execution_sync_count: int,
        accepted_attempt_count: int,
        reconcile_sync_count: int,
        close_event_count: int,
        attention_sync_count: int,
        missing_close_reason_count: int,
    ) -> None:
        path.write_text(
            json.dumps(
                PromotionGateRunnerTests._execution_audit_payload(
                    generated_at=generated_at,
                    execution_chain_visible=execution_chain_visible,
                    reconcile_chain_visible=reconcile_chain_visible,
                    close_reason_complete=close_reason_complete,
                    execution_attempt_count=execution_attempt_count,
                    execution_sync_count=execution_sync_count,
                    accepted_attempt_count=accepted_attempt_count,
                    reconcile_sync_count=reconcile_sync_count,
                    close_event_count=close_event_count,
                    attention_sync_count=attention_sync_count,
                    missing_close_reason_count=missing_close_reason_count,
                )
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _execution_audit_payload(
        *,
        generated_at: str,
        execution_chain_visible: bool,
        reconcile_chain_visible: bool,
        close_reason_complete: bool,
        execution_attempt_count: int,
        execution_sync_count: int,
        accepted_attempt_count: int,
        reconcile_sync_count: int,
        close_event_count: int,
        attention_sync_count: int,
        missing_close_reason_count: int,
    ) -> dict[str, object]:
        return {
            "generated_at": generated_at,
            "summary": {
                "execution_attempt_count": execution_attempt_count,
                "execution_sync_count": execution_sync_count,
                "accepted_attempt_count": accepted_attempt_count,
                "reconcile_sync_count": reconcile_sync_count,
                "close_event_count": close_event_count,
                "attention_sync_count": attention_sync_count,
                "missing_close_reason_count": missing_close_reason_count,
                "close_reason_coverage_rate": (
                    1.0 if close_event_count > 0 and missing_close_reason_count == 0 else None
                ),
            },
            "verdict": {
                "execution_chain_visible": execution_chain_visible,
                "reconcile_chain_visible": reconcile_chain_visible,
                "close_reason_complete": close_reason_complete,
                "close_reason_stable": close_reason_complete and attention_sync_count == 0,
                "recent_close_outcomes_distinguishable": close_event_count > 0,
            },
            "issues": [],
        }


if __name__ == "__main__":
    unittest.main()
