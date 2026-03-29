from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from ..bootstrap import build_host_check_runner, build_preflight_runner
from ..config.schema import SystemConfig
from ..storage.report_catalog import ArchivedReportDetails, FileReportCatalog


@dataclass
class DeploymentGateCheck:
    name: str
    passed: bool
    detail: str
    severity: str = "error"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class DeploymentGateSummary:
    passed_checks: int
    failed_checks: int
    total_checks: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "total_checks": self.total_checks,
        }


@dataclass
class DeploymentGateReport:
    environment: str
    platform: str
    ready: bool
    checked_at: datetime
    summary: DeploymentGateSummary
    checks: list[DeploymentGateCheck] = field(default_factory=list)
    acceptance: dict[str, Any] | None = None
    host_check: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "platform": self.platform,
            "ready": self.ready,
            "checked_at": self.checked_at.isoformat(),
            "summary": self.summary.as_dict(),
            "checks": [item.as_dict() for item in self.checks],
            "acceptance": self.acceptance,
            "host_check": self.host_check,
            "preflight": self.preflight,
        }


class DeploymentGateRunner:
    def __init__(
        self,
        config: SystemConfig,
        *,
        report_dir: str | None = None,
        report_type: str = "acceptance",
        max_acceptance_age_hours: float | None = None,
        require_acceptance_report: bool | None = None,
        require_host_check: bool | None = None,
        require_preflight: bool | None = None,
        host_check_runner: Any | None = None,
        preflight_runner: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config
        self.report_dir = report_dir
        self.report_type = report_type
        self.max_acceptance_age_hours = (
            config.deployment_gate.max_acceptance_report_age_hours
            if max_acceptance_age_hours is None
            else max_acceptance_age_hours
        )
        self.require_acceptance_report = (
            config.deployment_gate.require_acceptance_report
            if require_acceptance_report is None
            else require_acceptance_report
        )
        self.require_host_check = (
            self._default_require_host_check()
            if require_host_check is None
            else require_host_check
        )
        self.require_preflight = (
            self._default_require_preflight()
            if require_preflight is None
            else require_preflight
        )
        self.host_check_runner = host_check_runner
        self.preflight_runner = preflight_runner
        self.now = now

    def run(self) -> DeploymentGateReport:
        checked_at = self.now or datetime.now(timezone.utc)
        checks: list[DeploymentGateCheck] = []
        acceptance_snapshot: dict[str, Any] | None = None
        host_snapshot: dict[str, Any] | None = None
        preflight_snapshot: dict[str, Any] | None = None

        if self.require_acceptance_report:
            acceptance_details = self._load_latest_acceptance()
            acceptance_checks, acceptance_snapshot = self._evaluate_acceptance(
                acceptance_details,
                checked_at=checked_at,
            )
            checks.extend(acceptance_checks)
        else:
            checks.append(
                DeploymentGateCheck(
                    name="acceptance_gate_skipped",
                    passed=True,
                    detail="Acceptance gate skipped by configuration or CLI override.",
                    severity="info",
                )
            )

        if self.require_host_check:
            host_checks, host_snapshot = self._run_preflight_stage(
                name="host_check_ready",
                runner=self.host_check_runner or build_host_check_runner(self.config),
                success_detail="Execution host check passed.",
                failure_prefix="Execution host check failed",
            )
            checks.extend(host_checks)
        else:
            checks.append(
                DeploymentGateCheck(
                    name="host_check_skipped",
                    passed=True,
                    detail="Host check skipped because live host validation is not required for this run.",
                    severity="info",
                )
            )

        if self.require_preflight:
            try:
                runner = self.preflight_runner or build_preflight_runner(self.config)
            except Exception as exc:
                runner = None
                checks.append(
                    DeploymentGateCheck(
                        name="preflight_ready",
                        passed=False,
                        detail=f"Unable to build preflight runner: {exc}",
                    )
                )
            if runner is not None:
                preflight_checks, preflight_snapshot = self._run_preflight_stage(
                    name="preflight_ready",
                    runner=runner,
                    success_detail="Platform preflight passed.",
                    failure_prefix="Platform preflight failed",
                )
                checks.extend(preflight_checks)
        else:
            checks.append(
                DeploymentGateCheck(
                    name="preflight_skipped",
                    passed=True,
                    detail="Preflight skipped because live platform validation is not required for this run.",
                    severity="info",
                )
            )

        passed_checks = sum(item.passed or item.severity == "info" for item in checks)
        summary = DeploymentGateSummary(
            passed_checks=passed_checks,
            failed_checks=len(checks) - passed_checks,
            total_checks=len(checks),
        )
        ready = all(item.passed or item.severity == "info" for item in checks)
        return DeploymentGateReport(
            environment=self.config.runtime.environment,
            platform=self._platform(),
            ready=ready,
            checked_at=checked_at,
            summary=summary,
            checks=checks,
            acceptance=acceptance_snapshot,
            host_check=host_snapshot,
            preflight=preflight_snapshot,
        )

    def _evaluate_acceptance(
        self,
        details: ArchivedReportDetails | None,
        *,
        checked_at: datetime,
    ) -> tuple[list[DeploymentGateCheck], dict[str, Any] | None]:
        checks: list[DeploymentGateCheck] = []
        if details is None:
            checks.append(
                DeploymentGateCheck(
                    name="acceptance_report_available",
                    passed=False,
                    detail=(
                        f"No archived {self.report_type} report found in "
                        f"{self._catalog().base_dir}."
                    ),
                )
            )
            return checks, None

        snapshot = details.as_dict(include_payload=False)
        snapshot["summary"] = details.record.summary

        checks.append(
            DeploymentGateCheck(
                name="acceptance_report_available",
                passed=True,
                detail=(
                    f"Found archived {details.record.report_type} report saved at "
                    f"{details.record.saved_at}."
                ),
                metadata={
                    "archive_path": details.record.archive_path,
                    "saved_at": details.record.saved_at,
                },
            )
        )

        checks.append(
            DeploymentGateCheck(
                name="acceptance_report_ready",
                passed=details.record.ready is True,
                detail=(
                    "Latest acceptance report is marked ready."
                    if details.record.ready is True
                    else (
                        "Latest acceptance report is not ready. Failed checks: "
                        f"{', '.join(details.failed_check_names) or 'unknown'}."
                        if details.record.ready is False
                        else "Latest acceptance report does not include a ready verdict."
                    )
                ),
                metadata={
                    "failed_check_names": details.failed_check_names,
                    "summary": details.record.summary,
                },
            )
        )

        observed_at = self._parse_timestamp(details.checked_at) or self._parse_timestamp(
            details.record.saved_at
        )
        if observed_at is None:
            checks.append(
                DeploymentGateCheck(
                    name="acceptance_report_freshness",
                    passed=False,
                    detail=(
                        "Latest acceptance report timestamp could not be parsed, so "
                        "freshness cannot be verified."
                    ),
                    metadata={
                        "checked_at": details.checked_at,
                        "saved_at": details.record.saved_at,
                    },
                )
            )
            return checks, snapshot

        age_hours = round(
            max(0.0, (checked_at - observed_at).total_seconds() / 3600.0),
            4,
        )
        freshness_ok = age_hours <= self.max_acceptance_age_hours
        checks.append(
            DeploymentGateCheck(
                name="acceptance_report_freshness",
                passed=freshness_ok,
                detail=(
                    f"Latest acceptance report age is {age_hours:.4f} hours."
                    if freshness_ok
                    else (
                        f"Latest acceptance report age is {age_hours:.4f} hours, "
                        f"which exceeds the limit of {self.max_acceptance_age_hours:.4f} hours."
                    )
                ),
                metadata={
                    "checked_at": observed_at.isoformat(),
                    "age_hours": age_hours,
                    "max_age_hours": self.max_acceptance_age_hours,
                },
            )
        )
        return checks, snapshot

    def _run_preflight_stage(
        self,
        *,
        name: str,
        runner: Any,
        success_detail: str,
        failure_prefix: str,
    ) -> tuple[list[DeploymentGateCheck], dict[str, Any] | None]:
        try:
            report = runner.run()
        except Exception as exc:
            return [
                DeploymentGateCheck(
                    name=name,
                    passed=False,
                    detail=f"{failure_prefix}: {exc}",
                )
            ], None

        failed_names = [
            item.name
            for item in report.checks
            if not item.passed and item.severity != "info"
        ]
        detail = (
            success_detail
            if report.ready
            else f"{failure_prefix}: {', '.join(failed_names) or 'unknown checks'}."
        )
        return [
            DeploymentGateCheck(
                name=name,
                passed=report.ready,
                detail=detail,
                metadata={"failed_checks": failed_names, "platform": report.platform},
            )
        ], report.as_dict()

    def _catalog(self) -> FileReportCatalog:
        archive_config = replace(self.config.report_archive)
        if self.report_dir is not None:
            archive_config.base_dir = self.report_dir
        return FileReportCatalog(archive_config)

    def _load_latest_acceptance(self) -> ArchivedReportDetails | None:
        return self._catalog().latest_report(report_type=self.report_type)

    def _default_require_host_check(self) -> bool:
        return (
            self.config.deployment_gate.require_host_check_on_live
            and self._platform() == "mt5"
            and not self.config.runtime.dry_run
        )

    def _default_require_preflight(self) -> bool:
        return (
            self.config.deployment_gate.require_preflight_on_live
            and self._platform() in {"mt5", "ctrader"}
            and not self.config.runtime.dry_run
        )

    def _platform(self) -> str:
        execution_platform = self.config.execution.platform.lower()
        market_data_platform = self.config.market_data.platform.lower()
        return execution_platform if execution_platform != "none" else market_data_platform

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None

        for fmt in (
            "%Y-%m-%dT%H-%M-%S-%fZ",
            "%Y-%m-%dT%H-%M-%SZ",
        ):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
