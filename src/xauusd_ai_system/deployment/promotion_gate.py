from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from ..config.schema import SystemConfig
from ..storage.report_catalog import ArchivedReportDetails, FileReportCatalog


@dataclass
class PromotionGateCheck:
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
class PromotionGateSummary:
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
class PromotionGateReport:
    environment: str
    platform: str
    ready: bool
    checked_at: datetime
    summary: PromotionGateSummary
    thresholds: dict[str, Any]
    checks: list[PromotionGateCheck] = field(default_factory=list)
    candidate_acceptance: dict[str, Any] | None = None
    baseline_acceptance: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    current_daily_check: dict[str, Any] | None = None
    candidate_daily_check: dict[str, Any] | None = None
    current_execution_audit: dict[str, Any] | None = None
    candidate_execution_audit: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "platform": self.platform,
            "ready": self.ready,
            "checked_at": self.checked_at.isoformat(),
            "summary": self.summary.as_dict(),
            "thresholds": self.thresholds,
            "checks": [item.as_dict() for item in self.checks],
            "candidate_acceptance": self.candidate_acceptance,
            "baseline_acceptance": self.baseline_acceptance,
            "comparison": self.comparison,
            "current_daily_check": self.current_daily_check,
            "candidate_daily_check": self.candidate_daily_check,
            "current_execution_audit": self.current_execution_audit,
            "candidate_execution_audit": self.candidate_execution_audit,
        }


class PromotionGateRunner:
    def __init__(
        self,
        config: SystemConfig,
        *,
        candidate_report_dir: str | None = None,
        baseline_report_dir: str | None = None,
        report_type: str = "acceptance",
        max_acceptance_age_hours: float | None = None,
        max_daily_check_age_hours: float | None = None,
        max_execution_audit_age_hours: float | None = None,
        min_total_net_pnl: float | None = None,
        min_total_profit_factor: float | None = None,
        min_closed_trades: int | None = None,
        min_out_of_sample_net_pnl: float | None = None,
        min_out_of_sample_profit_factor: float | None = None,
        min_walk_forward_positive_window_rate: float | None = None,
        max_close_month_profit_concentration: float | None = None,
        max_session_profit_concentration: float | None = None,
        max_execution_attention_sync_count: int | None = None,
        current_daily_check_path: str | None = None,
        candidate_daily_check_path: str | None = None,
        current_execution_audit_path: str | None = None,
        candidate_execution_audit_path: str | None = None,
        require_current_daily_check: bool | None = None,
        require_candidate_daily_check: bool | None = None,
        require_current_execution_audit: bool | None = None,
        require_candidate_execution_audit: bool | None = None,
        now: datetime | None = None,
    ) -> None:
        promotion_config = config.promotion_gate
        self.config = config
        self.candidate_report_dir = candidate_report_dir
        self.baseline_report_dir = baseline_report_dir
        self.report_type = report_type
        self.max_acceptance_age_hours = (
            promotion_config.max_acceptance_report_age_hours
            if max_acceptance_age_hours is None
            else max_acceptance_age_hours
        )
        self.max_daily_check_age_hours = (
            promotion_config.max_daily_check_age_hours
            if max_daily_check_age_hours is None
            else max_daily_check_age_hours
        )
        self.max_execution_audit_age_hours = (
            promotion_config.max_execution_audit_age_hours
            if max_execution_audit_age_hours is None
            else max_execution_audit_age_hours
        )
        self.min_total_net_pnl = (
            promotion_config.min_total_net_pnl
            if min_total_net_pnl is None
            else min_total_net_pnl
        )
        self.min_total_profit_factor = (
            promotion_config.min_total_profit_factor
            if min_total_profit_factor is None
            else min_total_profit_factor
        )
        self.min_closed_trades = (
            promotion_config.min_closed_trades
            if min_closed_trades is None
            else min_closed_trades
        )
        self.min_out_of_sample_net_pnl = (
            promotion_config.min_out_of_sample_net_pnl
            if min_out_of_sample_net_pnl is None
            else min_out_of_sample_net_pnl
        )
        self.min_out_of_sample_profit_factor = (
            promotion_config.min_out_of_sample_profit_factor
            if min_out_of_sample_profit_factor is None
            else min_out_of_sample_profit_factor
        )
        self.min_walk_forward_positive_window_rate = (
            promotion_config.min_walk_forward_positive_window_rate
            if min_walk_forward_positive_window_rate is None
            else min_walk_forward_positive_window_rate
        )
        self.max_close_month_profit_concentration = (
            promotion_config.max_close_month_profit_concentration
            if max_close_month_profit_concentration is None
            else max_close_month_profit_concentration
        )
        self.max_session_profit_concentration = (
            promotion_config.max_session_profit_concentration
            if max_session_profit_concentration is None
            else max_session_profit_concentration
        )
        self.max_execution_attention_sync_count = (
            promotion_config.max_execution_attention_sync_count
            if max_execution_attention_sync_count is None
            else max_execution_attention_sync_count
        )
        self.current_daily_check_path = current_daily_check_path
        self.candidate_daily_check_path = candidate_daily_check_path
        self.current_execution_audit_path = current_execution_audit_path
        self.candidate_execution_audit_path = candidate_execution_audit_path
        self.require_current_daily_check = (
            promotion_config.require_current_daily_check
            if require_current_daily_check is None
            else require_current_daily_check
        )
        self.require_candidate_daily_check = (
            promotion_config.require_candidate_daily_check
            if require_candidate_daily_check is None
            else require_candidate_daily_check
        )
        self.require_current_execution_audit = (
            promotion_config.require_current_execution_audit
            if require_current_execution_audit is None
            else require_current_execution_audit
        )
        self.require_candidate_execution_audit = (
            promotion_config.require_candidate_execution_audit
            if require_candidate_execution_audit is None
            else require_candidate_execution_audit
        )
        self.now = now

    def run(self) -> PromotionGateReport:
        checked_at = self.now or datetime.now(timezone.utc)
        checks: list[PromotionGateCheck] = []

        candidate_details = self._load_latest_report(self.candidate_report_dir)
        candidate_checks, candidate_snapshot, candidate_headline = self._evaluate_candidate_acceptance(
            candidate_details,
            checked_at=checked_at,
        )
        checks.extend(candidate_checks)

        baseline_snapshot = None
        comparison = None
        if self.baseline_report_dir:
            baseline_details = self._load_latest_report(self.baseline_report_dir)
            baseline_snapshot, baseline_headline = self._build_acceptance_snapshot(
                baseline_details
            )
            comparison = self._build_comparison(
                candidate_headline,
                baseline_headline,
                candidate_report_dir=self._catalog_base_dir(self.candidate_report_dir),
                baseline_report_dir=self._catalog_base_dir(self.baseline_report_dir),
            )

        current_checks, current_daily_snapshot = self._evaluate_daily_check(
            name_prefix="current_daily_check",
            json_path=self.current_daily_check_path,
            required=self.require_current_daily_check,
            checked_at=checked_at,
        )
        checks.extend(current_checks)

        candidate_daily_checks, candidate_daily_snapshot = self._evaluate_daily_check(
            name_prefix="candidate_daily_check",
            json_path=self.candidate_daily_check_path,
            required=self.require_candidate_daily_check,
            checked_at=checked_at,
        )
        checks.extend(candidate_daily_checks)

        current_execution_checks, current_execution_snapshot = self._evaluate_execution_audit(
            name_prefix="current_execution_audit",
            json_path=self.current_execution_audit_path,
            required=self.require_current_execution_audit,
            checked_at=checked_at,
            fallback_daily_check=current_daily_snapshot,
            fallback_daily_check_name="current_daily_check",
        )
        checks.extend(current_execution_checks)

        candidate_execution_checks, candidate_execution_snapshot = self._evaluate_execution_audit(
            name_prefix="candidate_execution_audit",
            json_path=self.candidate_execution_audit_path,
            required=self.require_candidate_execution_audit,
            checked_at=checked_at,
            fallback_daily_check=candidate_daily_snapshot,
            fallback_daily_check_name="candidate_daily_check",
        )
        checks.extend(candidate_execution_checks)

        passed_checks = sum(item.passed or item.severity == "info" for item in checks)
        summary = PromotionGateSummary(
            passed_checks=passed_checks,
            failed_checks=len(checks) - passed_checks,
            total_checks=len(checks),
        )
        ready = all(item.passed or item.severity == "info" for item in checks)
        return PromotionGateReport(
            environment=self.config.runtime.environment,
            platform=self._platform(),
            ready=ready,
            checked_at=checked_at,
            summary=summary,
            thresholds=self._thresholds(),
            checks=checks,
            candidate_acceptance=candidate_snapshot,
            baseline_acceptance=baseline_snapshot,
            comparison=comparison,
            current_daily_check=current_daily_snapshot,
            candidate_daily_check=candidate_daily_snapshot,
            current_execution_audit=current_execution_snapshot,
            candidate_execution_audit=candidate_execution_snapshot,
        )

    def _evaluate_candidate_acceptance(
        self,
        details: ArchivedReportDetails | None,
        *,
        checked_at: datetime,
    ) -> tuple[list[PromotionGateCheck], dict[str, Any] | None, dict[str, Any]]:
        checks: list[PromotionGateCheck] = []
        snapshot, headline = self._build_acceptance_snapshot(details)

        if details is None:
            checks.append(
                PromotionGateCheck(
                    name="candidate_acceptance_report_available",
                    passed=False,
                    detail=(
                        f"No archived {self.report_type} report found in "
                        f"{self._catalog_base_dir(self.candidate_report_dir)}."
                    ),
                )
            )
            return checks, snapshot, headline

        checks.append(
            PromotionGateCheck(
                name="candidate_acceptance_report_available",
                passed=True,
                detail=(
                    f"Found candidate {details.record.report_type} report saved at "
                    f"{details.record.saved_at}."
                ),
                metadata={
                    "archive_path": details.record.archive_path,
                    "saved_at": details.record.saved_at,
                },
            )
        )
        checks.append(
            PromotionGateCheck(
                name="candidate_acceptance_report_ready",
                passed=details.record.ready is True,
                detail=(
                    "Candidate acceptance report is marked ready."
                    if details.record.ready is True
                    else (
                        "Candidate acceptance report is not ready. Failed checks: "
                        f"{', '.join(details.failed_check_names) or 'unknown'}."
                        if details.record.ready is False
                        else "Candidate acceptance report does not include a ready verdict."
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
                PromotionGateCheck(
                    name="candidate_acceptance_report_freshness",
                    passed=False,
                    detail=(
                        "Candidate acceptance report timestamp could not be parsed, so "
                        "freshness cannot be verified."
                    ),
                    metadata={
                        "checked_at": details.checked_at,
                        "saved_at": details.record.saved_at,
                    },
                )
            )
        else:
            age_hours = round(
                max(0.0, (checked_at - observed_at).total_seconds() / 3600.0),
                4,
            )
            freshness_ok = age_hours <= self.max_acceptance_age_hours
            checks.append(
                PromotionGateCheck(
                    name="candidate_acceptance_report_freshness",
                    passed=freshness_ok,
                    detail=(
                        f"Candidate acceptance report age is {age_hours:.4f} hours."
                        if freshness_ok
                        else (
                            f"Candidate acceptance report age is {age_hours:.4f} hours, "
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

        checks.append(
            PromotionGateCheck(
                name="candidate_headline_metrics_available",
                passed=bool(headline),
                detail=(
                    "Candidate acceptance headline metrics are available."
                    if headline
                    else "Candidate acceptance headline metrics are missing."
                ),
            )
        )

        checks.extend(
            [
                self._build_min_metric_check(
                    name="candidate_total_net_pnl_threshold",
                    observed=headline.get("net_pnl"),
                    minimum=self.min_total_net_pnl,
                    detail_label="candidate total net PnL",
                ),
                self._build_min_metric_check(
                    name="candidate_total_profit_factor_threshold",
                    observed=headline.get("profit_factor"),
                    minimum=self.min_total_profit_factor,
                    detail_label="candidate total profit factor",
                ),
                self._build_min_metric_check(
                    name="candidate_closed_trades_threshold",
                    observed=headline.get("closed_trades"),
                    minimum=self.min_closed_trades,
                    detail_label="candidate closed trades",
                    integer=True,
                ),
                self._build_min_metric_check(
                    name="candidate_out_of_sample_net_pnl_threshold",
                    observed=headline.get("out_of_sample_net_pnl"),
                    minimum=self.min_out_of_sample_net_pnl,
                    detail_label="candidate out-of-sample net PnL",
                ),
                self._build_min_metric_check(
                    name="candidate_out_of_sample_profit_factor_threshold",
                    observed=headline.get("out_of_sample_profit_factor"),
                    minimum=self.min_out_of_sample_profit_factor,
                    detail_label="candidate out-of-sample profit factor",
                ),
                self._build_min_metric_check(
                    name="candidate_walk_forward_positive_window_rate_threshold",
                    observed=headline.get("walk_forward_positive_window_rate"),
                    minimum=self.min_walk_forward_positive_window_rate,
                    detail_label="candidate walk-forward positive window rate",
                ),
                self._build_max_metric_check(
                    name="candidate_close_month_profit_concentration_threshold",
                    observed=headline.get("close_month_profit_concentration"),
                    maximum=self.max_close_month_profit_concentration,
                    detail_label="candidate close-month profit concentration",
                ),
                self._build_max_metric_check(
                    name="candidate_session_profit_concentration_threshold",
                    observed=headline.get("session_profit_concentration"),
                    maximum=self.max_session_profit_concentration,
                    detail_label="candidate session profit concentration",
                ),
            ]
        )
        return checks, snapshot, headline

    def _evaluate_daily_check(
        self,
        *,
        name_prefix: str,
        json_path: str | None,
        required: bool,
        checked_at: datetime,
    ) -> tuple[list[PromotionGateCheck], dict[str, Any] | None]:
        checks: list[PromotionGateCheck] = []
        payload, path_error = self._load_optional_json_payload(
            name_prefix=name_prefix,
            json_path=json_path,
            required=required,
            checks=checks,
        )
        if payload is None:
            return checks, None

        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_available",
                passed=True,
                detail=f"Loaded {name_prefix} JSON from {path_error}.",
                metadata={"path": str(path_error)},
            )
        )

        health = payload.get("health")
        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_health",
                passed=health == "ok",
                detail=(
                    f"{name_prefix} health is ok."
                    if health == "ok"
                    else f"{name_prefix} health is {health or 'unknown'}."
                ),
                metadata={"health": health, "issue_count": payload.get("issue_count")},
            )
        )

        observed_at = self._parse_timestamp(payload.get("checked_at"))
        if observed_at is None:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_freshness",
                    passed=False,
                    detail=f"{name_prefix} checked_at could not be parsed.",
                    metadata={"checked_at": payload.get("checked_at")},
                )
            )
            return checks, payload

        age_hours = round(
            max(0.0, (checked_at - observed_at).total_seconds() / 3600.0),
            4,
        )
        freshness_ok = age_hours <= self.max_daily_check_age_hours
        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_freshness",
                passed=freshness_ok,
                detail=(
                    f"{name_prefix} age is {age_hours:.4f} hours."
                    if freshness_ok
                    else (
                        f"{name_prefix} age is {age_hours:.4f} hours, "
                        f"which exceeds the limit of {self.max_daily_check_age_hours:.4f} hours."
                    )
                ),
                metadata={
                    "checked_at": observed_at.isoformat(),
                    "age_hours": age_hours,
                    "max_age_hours": self.max_daily_check_age_hours,
                },
            )
        )
        return checks, payload

    def _evaluate_execution_audit(
        self,
        *,
        name_prefix: str,
        json_path: str | None,
        required: bool,
        checked_at: datetime,
        fallback_daily_check: dict[str, Any] | None,
        fallback_daily_check_name: str,
    ) -> tuple[list[PromotionGateCheck], dict[str, Any] | None]:
        checks: list[PromotionGateCheck] = []
        payload, resolved_source, source_kind = self._resolve_execution_audit_payload(
            name_prefix=name_prefix,
            json_path=json_path,
            required=required,
            checks=checks,
            fallback_daily_check=fallback_daily_check,
            fallback_daily_check_name=fallback_daily_check_name,
        )
        if payload is None:
            return checks, None

        payload = dict(payload)
        payload["promotion_gate_source"] = str(resolved_source)
        payload["promotion_gate_source_kind"] = source_kind

        available_detail = (
            f"Loaded {name_prefix} JSON from {resolved_source}."
            if source_kind == "path"
            else f"Loaded {name_prefix} from embedded {resolved_source}."
        )
        available_metadata = (
            {"path": str(resolved_source)}
            if source_kind == "path"
            else {"embedded_source": str(resolved_source)}
        )
        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_available",
                passed=True,
                detail=available_detail,
                metadata=available_metadata,
            )
        )

        observed_at = self._parse_timestamp(
            self._string_or_none(payload.get("generated_at"))
            or self._string_or_none(payload.get("checked_at"))
        )
        if observed_at is None:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_freshness",
                    passed=False,
                    detail=f"{name_prefix} generated_at / checked_at could not be parsed.",
                    metadata={
                        "generated_at": payload.get("generated_at"),
                        "checked_at": payload.get("checked_at"),
                    },
                )
            )
            return checks, payload

        age_hours = round(
            max(0.0, (checked_at - observed_at).total_seconds() / 3600.0),
            4,
        )
        freshness_ok = age_hours <= self.max_execution_audit_age_hours
        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_freshness",
                passed=freshness_ok,
                detail=(
                    f"{name_prefix} age is {age_hours:.4f} hours."
                    if freshness_ok
                    else (
                        f"{name_prefix} age is {age_hours:.4f} hours, "
                        f"which exceeds the limit of {self.max_execution_audit_age_hours:.4f} hours."
                    )
                ),
                metadata={
                    "checked_at": observed_at.isoformat(),
                    "age_hours": age_hours,
                    "max_age_hours": self.max_execution_audit_age_hours,
                },
            )
        )

        summary = payload.get("summary")
        if not isinstance(summary, dict):
            summary = {}
        verdict = payload.get("verdict")
        if not isinstance(verdict, dict):
            verdict = {}
        issues = payload.get("issues")
        issue_count = len(issues) if isinstance(issues, list) else 0

        execution_chain_visible = verdict.get("execution_chain_visible") is True
        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_execution_chain_visible",
                passed=execution_chain_visible,
                detail=(
                    f"{name_prefix} execution chain is visible."
                    if execution_chain_visible
                    else f"{name_prefix} execution chain is not yet visible."
                ),
                metadata={
                    "execution_attempt_count": summary.get("execution_attempt_count"),
                    "execution_sync_count": summary.get("execution_sync_count"),
                    "accepted_attempt_count": summary.get("accepted_attempt_count"),
                    "issue_count": issue_count,
                },
            )
        )

        reconcile_chain_visible = verdict.get("reconcile_chain_visible") is True
        checks.append(
            PromotionGateCheck(
                name=f"{name_prefix}_reconcile_chain_visible",
                passed=reconcile_chain_visible,
                detail=(
                    f"{name_prefix} reconcile chain is visible."
                    if reconcile_chain_visible
                    else f"{name_prefix} reconcile chain is not yet visible."
                ),
                metadata={
                    "reconcile_sync_count": summary.get("reconcile_sync_count"),
                    "submission_sync_count": summary.get("submission_sync_count"),
                    "issue_count": issue_count,
                },
            )
        )

        attention_sync_count = self._coerce_numeric(
            summary.get("attention_sync_count"),
            integer=True,
        )
        if attention_sync_count is None:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_attention_sync_threshold",
                    passed=False,
                    detail=f"{name_prefix} attention_sync_count is missing.",
                    metadata={
                        "attention_sync_count": summary.get("attention_sync_count"),
                        "maximum": self.max_execution_attention_sync_count,
                    },
                )
            )
        else:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_attention_sync_threshold",
                    passed=int(attention_sync_count) <= self.max_execution_attention_sync_count,
                    detail=(
                        f"{name_prefix} attention sync count = {int(attention_sync_count)}, "
                        f"threshold <= {self.max_execution_attention_sync_count}."
                        if int(attention_sync_count) <= self.max_execution_attention_sync_count
                        else (
                            f"{name_prefix} attention sync count = {int(attention_sync_count)}, "
                            f"above threshold <= {self.max_execution_attention_sync_count}."
                        )
                    ),
                    metadata={
                        "attention_sync_count": int(attention_sync_count),
                        "maximum": self.max_execution_attention_sync_count,
                        "issue_count": issue_count,
                    },
                )
            )

        close_event_count = self._coerce_numeric(
            summary.get("close_event_count"),
            integer=True,
        )
        if close_event_count is None:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_close_reason_complete",
                    passed=False,
                    detail=f"{name_prefix} close_event_count is missing.",
                    metadata={"close_event_count": summary.get("close_event_count")},
                )
            )
        elif int(close_event_count) <= 0:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_close_reason_complete",
                    passed=True,
                    detail=f"{name_prefix} has no recent close events; close-reason completeness check skipped.",
                    severity="info",
                    metadata={"close_event_count": int(close_event_count)},
                )
            )
        else:
            close_reason_complete = verdict.get("close_reason_complete") is True
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_close_reason_complete",
                    passed=close_reason_complete,
                    detail=(
                        f"{name_prefix} close reasons are complete for recent close events."
                        if close_reason_complete
                        else f"{name_prefix} close reasons are incomplete for recent close events."
                    ),
                    metadata={
                        "close_event_count": int(close_event_count),
                        "missing_close_reason_count": summary.get("missing_close_reason_count"),
                        "close_reason_coverage_rate": summary.get("close_reason_coverage_rate"),
                        "issue_count": issue_count,
                    },
                )
            )

        return checks, payload

    @staticmethod
    def _resolve_execution_audit_payload(
        *,
        name_prefix: str,
        json_path: str | None,
        required: bool,
        checks: list[PromotionGateCheck],
        fallback_daily_check: dict[str, Any] | None,
        fallback_daily_check_name: str,
    ) -> tuple[dict[str, Any] | None, Path | str | None, str | None]:
        if json_path:
            payload, path = PromotionGateRunner._load_optional_json_payload(
                name_prefix=name_prefix,
                json_path=json_path,
                required=required,
                checks=checks,
            )
            return payload, path, "path" if payload is not None and path is not None else None

        embedded_payload = None
        if isinstance(fallback_daily_check, dict):
            candidate = fallback_daily_check.get("execution_audit")
            if isinstance(candidate, dict):
                embedded_payload = dict(candidate)

        if embedded_payload is not None:
            if embedded_payload.get("available") is False:
                detail = (
                    f"{name_prefix} embedded in {fallback_daily_check_name}.execution_audit is marked unavailable."
                )
                error_message = embedded_payload.get("error")
                if isinstance(error_message, str) and error_message:
                    detail = f"{detail} {error_message}"

                if required:
                    checks.append(
                        PromotionGateCheck(
                            name=f"{name_prefix}_available",
                            passed=False,
                            detail=detail,
                            metadata={
                                "embedded_source": f"{fallback_daily_check_name}.execution_audit",
                                "error": error_message,
                            },
                        )
                    )
                else:
                    checks.append(
                        PromotionGateCheck(
                            name=f"{name_prefix}_skipped",
                            passed=True,
                            detail=f"{detail} Check skipped for this promotion gate run.",
                            severity="info",
                            metadata={
                                "embedded_source": f"{fallback_daily_check_name}.execution_audit",
                                "error": error_message,
                            },
                        )
                    )
                return None, None, None

            return (
                embedded_payload,
                f"{fallback_daily_check_name}.execution_audit",
                "embedded",
            )

        if required:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_available",
                    passed=False,
                    detail=(
                        f"{name_prefix} JSON path is required but was not provided, and "
                        f"{fallback_daily_check_name} does not include execution_audit."
                    ),
                )
            )
        else:
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_skipped",
                    passed=True,
                    detail=(
                        f"{name_prefix} check skipped for this promotion gate run; "
                        f"no explicit JSON path or embedded {fallback_daily_check_name}.execution_audit was available."
                    ),
                    severity="info",
                )
            )
        return None, None, None

    def _build_acceptance_snapshot(
        self,
        details: ArchivedReportDetails | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        if details is None:
            return None, {}

        record_headline: dict[str, Any] = {}
        if isinstance(details.record.summary, dict):
            candidate = details.record.summary.get("headline_metrics")
            if isinstance(candidate, dict):
                record_headline = dict(candidate)

        payload_headline: dict[str, Any] = {}
        payload_candidate = details.payload.get("headline_metrics")
        if isinstance(payload_candidate, dict):
            payload_headline = dict(payload_candidate)

        payload_summary_headline: dict[str, Any] = {}
        payload_summary = details.payload.get("summary")
        if isinstance(payload_summary, dict):
            summary_candidate = payload_summary.get("headline_metrics")
            if isinstance(summary_candidate, dict):
                payload_summary_headline = dict(summary_candidate)

        headline = self._merge_metric_sources(
            record_headline,
            payload_headline,
            payload_summary_headline,
            self._derive_headline_metrics(details.payload),
        )

        snapshot = details.as_dict(include_payload=False)
        snapshot["summary"] = details.record.summary
        snapshot["headline_metrics"] = headline
        return snapshot, headline

    def _build_min_metric_check(
        self,
        *,
        name: str,
        observed: Any,
        minimum: float | int,
        detail_label: str,
        integer: bool = False,
    ) -> PromotionGateCheck:
        normalized = self._coerce_numeric(observed, integer=integer)
        if normalized is None:
            return PromotionGateCheck(
                name=name,
                passed=False,
                detail=f"{detail_label} is missing.",
                metadata={"observed": observed, "minimum": minimum},
            )

        passed = normalized >= minimum
        observed_text = int(normalized) if integer else round(normalized, 4)
        minimum_text = int(minimum) if integer else round(float(minimum), 4)
        return PromotionGateCheck(
            name=name,
            passed=passed,
            detail=(
                f"{detail_label} = {observed_text}, threshold >= {minimum_text}."
                if passed
                else f"{detail_label} = {observed_text}, below threshold >= {minimum_text}."
            ),
            metadata={"observed": normalized, "minimum": minimum},
        )

    def _build_max_metric_check(
        self,
        *,
        name: str,
        observed: Any,
        maximum: float | int,
        detail_label: str,
    ) -> PromotionGateCheck:
        normalized = self._coerce_numeric(observed, integer=False)
        if normalized is None:
            return PromotionGateCheck(
                name=name,
                passed=False,
                detail=f"{detail_label} is missing.",
                metadata={"observed": observed, "maximum": maximum},
            )

        passed = normalized <= maximum
        observed_text = round(normalized, 4)
        maximum_text = round(float(maximum), 4)
        return PromotionGateCheck(
            name=name,
            passed=passed,
            detail=(
                f"{detail_label} = {observed_text}, threshold <= {maximum_text}."
                if passed
                else f"{detail_label} = {observed_text}, above threshold <= {maximum_text}."
            ),
            metadata={"observed": normalized, "maximum": maximum},
        )

    def _build_comparison(
        self,
        candidate_headline: dict[str, Any],
        baseline_headline: dict[str, Any],
        *,
        candidate_report_dir: Path,
        baseline_report_dir: Path,
    ) -> dict[str, Any] | None:
        if not candidate_headline or not baseline_headline:
            return None

        compared_metrics = (
            "net_pnl",
            "profit_factor",
            "closed_trades",
            "out_of_sample_net_pnl",
            "out_of_sample_profit_factor",
            "walk_forward_positive_window_rate",
        )
        deltas: dict[str, float | int | None] = {}
        for metric_name in compared_metrics:
            candidate_value = candidate_headline.get(metric_name)
            baseline_value = baseline_headline.get(metric_name)
            if isinstance(candidate_value, bool) or isinstance(baseline_value, bool):
                deltas[metric_name] = None
                continue
            if isinstance(candidate_value, int) and isinstance(baseline_value, int):
                deltas[metric_name] = candidate_value - baseline_value
                continue
            if isinstance(candidate_value, (int, float)) and isinstance(
                baseline_value, (int, float)
            ):
                deltas[metric_name] = round(float(candidate_value) - float(baseline_value), 8)
                continue
            deltas[metric_name] = None

        return {
            "candidate_report_dir": str(candidate_report_dir),
            "baseline_report_dir": str(baseline_report_dir),
            "candidate_headline_metrics": candidate_headline,
            "baseline_headline_metrics": baseline_headline,
            "headline_metric_deltas": deltas,
        }

    def _catalog(self, report_dir: str | None) -> FileReportCatalog:
        archive_config = replace(self.config.report_archive)
        if report_dir is not None:
            archive_config.base_dir = report_dir
        return FileReportCatalog(archive_config)

    def _catalog_base_dir(self, report_dir: str | None) -> Path:
        return self._catalog(report_dir).base_dir

    def _load_latest_report(self, report_dir: str | None) -> ArchivedReportDetails | None:
        return self._catalog(report_dir).latest_report(report_type=self.report_type)

    def _thresholds(self) -> dict[str, Any]:
        return {
            "max_acceptance_report_age_hours": self.max_acceptance_age_hours,
            "max_daily_check_age_hours": self.max_daily_check_age_hours,
            "max_execution_audit_age_hours": self.max_execution_audit_age_hours,
            "min_total_net_pnl": self.min_total_net_pnl,
            "min_total_profit_factor": self.min_total_profit_factor,
            "min_closed_trades": self.min_closed_trades,
            "min_out_of_sample_net_pnl": self.min_out_of_sample_net_pnl,
            "min_out_of_sample_profit_factor": self.min_out_of_sample_profit_factor,
            "min_walk_forward_positive_window_rate": self.min_walk_forward_positive_window_rate,
            "max_close_month_profit_concentration": self.max_close_month_profit_concentration,
            "max_session_profit_concentration": self.max_session_profit_concentration,
            "max_execution_attention_sync_count": self.max_execution_attention_sync_count,
            "require_current_daily_check": self.require_current_daily_check,
            "require_candidate_daily_check": self.require_candidate_daily_check,
            "require_current_execution_audit": self.require_current_execution_audit,
            "require_candidate_execution_audit": self.require_candidate_execution_audit,
        }

    def _platform(self) -> str:
        execution_platform = self.config.execution.platform.lower()
        market_data_platform = self.config.market_data.platform.lower()
        return execution_platform if execution_platform != "none" else market_data_platform

    @staticmethod
    def _coerce_numeric(value: Any, *, integer: bool) -> float | int | None:
        if isinstance(value, bool):
            return None
        if integer:
            if isinstance(value, int):
                return value
            if isinstance(value, float) and value.is_integer():
                return int(value)
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if isinstance(value, str) and value:
            return value
        return None

    @staticmethod
    def _load_optional_json_payload(
        *,
        name_prefix: str,
        json_path: str | None,
        required: bool,
        checks: list[PromotionGateCheck],
    ) -> tuple[dict[str, Any] | None, Path | None]:
        if not json_path:
            if required:
                checks.append(
                    PromotionGateCheck(
                        name=f"{name_prefix}_available",
                        passed=False,
                        detail=f"{name_prefix} JSON path is required but was not provided.",
                    )
                )
            else:
                checks.append(
                    PromotionGateCheck(
                        name=f"{name_prefix}_skipped",
                        passed=True,
                        detail=f"{name_prefix} check skipped for this promotion gate run.",
                        severity="info",
                    )
                )
            return None, None

        path = Path(json_path)
        if not path.exists():
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_available",
                    passed=False,
                    detail=f"{name_prefix} JSON file not found: {path}",
                )
            )
            return None, None

        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            checks.append(
                PromotionGateCheck(
                    name=f"{name_prefix}_available",
                    passed=False,
                    detail=f"{name_prefix} JSON must be an object: {path}",
                )
            )
            return None, None
        return payload, path

    @staticmethod
    def _derive_headline_metrics(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        backtest = payload.get("backtest")
        if not isinstance(backtest, dict):
            return {}

        decision_summary = backtest.get("decision_summary")
        if not isinstance(decision_summary, dict):
            decision_summary = {}

        out_of_sample = payload.get("sample_split")
        if isinstance(out_of_sample, dict):
            out_of_sample = out_of_sample.get("out_of_sample")
        if isinstance(out_of_sample, dict):
            out_of_sample = out_of_sample.get("backtest")
        if not isinstance(out_of_sample, dict):
            out_of_sample = {}

        walk_forward = payload.get("walk_forward")
        if isinstance(walk_forward, dict):
            walk_forward = walk_forward.get("summary")
        if not isinstance(walk_forward, dict):
            walk_forward = {}

        signals_by_strategy = decision_summary.get("signals_by_strategy")
        if not isinstance(signals_by_strategy, dict):
            signals_by_strategy = {}

        derived = {
            "net_pnl": backtest.get("net_pnl"),
            "profit_factor": backtest.get("profit_factor"),
            "max_drawdown_pct": backtest.get("max_drawdown_pct"),
            "closed_trades": backtest.get("closed_trades"),
            "won_trades": backtest.get("won_trades"),
            "lost_trades": backtest.get("lost_trades"),
            "win_rate": backtest.get("win_rate"),
            "signals_generated": decision_summary.get("signals_generated"),
            "pullback_signal_count": signals_by_strategy.get("pullback"),
            "trades_allowed": decision_summary.get("trades_allowed"),
            "blocked_trades": decision_summary.get("blocked_trades"),
            "event_window_rows": decision_summary.get("event_window_rows"),
            "event_window_signals": decision_summary.get("event_window_signals"),
            "event_window_blocked_trades": decision_summary.get("event_window_blocked_trades"),
            "event_window_block_rate": decision_summary.get("event_window_block_rate"),
            "out_of_sample_net_pnl": out_of_sample.get("net_pnl"),
            "out_of_sample_profit_factor": out_of_sample.get("profit_factor"),
            "out_of_sample_max_drawdown_pct": out_of_sample.get("max_drawdown_pct"),
            "walk_forward_window_count": walk_forward.get("total_windows"),
            "walk_forward_positive_window_rate": walk_forward.get("positive_window_rate"),
        }
        return {key: value for key, value in derived.items() if value is not None}

    @staticmethod
    def _merge_metric_sources(*sources: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key, value in source.items():
                if value is None:
                    continue
                if key not in merged or merged[key] is None:
                    merged[key] = value
        return merged

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
            normalized = re.sub(
                r"([T\s]\d{2}:\d{2}:\d{2})\.(\d+)(?=(?:[+-]\d{2}:\d{2}|$))",
                lambda match: f"{match.group(1)}.{match.group(2)[:6]}",
                normalized,
            )
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None
