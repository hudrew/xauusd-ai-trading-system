from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from ..config.schema import ReportArchiveConfig
from .report_archive import ArchivedReportRecord, FileReportArchive


@dataclass
class ArchivedReportDetails:
    record: ArchivedReportRecord
    checked_at: str | None
    failed_check_names: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, *, include_payload: bool = False) -> dict[str, Any]:
        data = {
            "record": self.record.as_dict(),
            "checked_at": self.checked_at,
            "failed_check_names": self.failed_check_names,
        }
        if include_payload:
            data["payload"] = self.payload
        return data


@dataclass
class ArchivedReportTrend:
    total_records: int
    ready_records: int
    failed_records: int
    readiness_rate: float
    latest_saved_at: str | None
    latest_ready: bool | None
    last_ready_at: str | None
    last_failed_at: str | None
    latest_failed_check_names: list[str] = field(default_factory=list)
    failed_check_counts: dict[str, int] = field(default_factory=dict)
    recent_records: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "total_records": self.total_records,
                "ready_records": self.ready_records,
                "failed_records": self.failed_records,
                "readiness_rate": self.readiness_rate,
                "latest_saved_at": self.latest_saved_at,
                "latest_ready": self.latest_ready,
                "last_ready_at": self.last_ready_at,
                "last_failed_at": self.last_failed_at,
            },
            "latest_failed_check_names": self.latest_failed_check_names,
            "failed_check_counts": self.failed_check_counts,
            "recent_records": self.recent_records,
        }


class FileReportCatalog:
    def __init__(self, config: ReportArchiveConfig) -> None:
        self.config = config
        self.base_dir = FileReportArchive(config).base_dir

    def list_records(
        self,
        *,
        report_type: str | None = None,
        limit: int | None = 20,
    ) -> list[ArchivedReportRecord]:
        records = self._read_index(report_type=report_type)
        if limit is None or limit < 0:
            return records
        return records[:limit]

    def latest_report(self, *, report_type: str | None = None) -> ArchivedReportDetails | None:
        records = self.list_records(report_type=report_type, limit=1)
        if records:
            return self.read_details(records[0])

        normalized_type = self._normalize_report_type(report_type)
        if normalized_type is None:
            return None

        latest_path = self.base_dir / normalized_type / "latest.json"
        if not latest_path.exists():
            return None

        envelope = json.loads(latest_path.read_text(encoding="utf-8"))
        return self._build_details(
            ArchivedReportRecord(
                report_type=normalized_type,
                saved_at=envelope.get("saved_at", ""),
                archive_path=str(latest_path),
                latest_path=str(latest_path),
                ready=envelope.get("ready"),
                summary=envelope.get("summary") or {},
            ),
            envelope,
        )

    def build_trend(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
    ) -> ArchivedReportTrend:
        records = self.list_records(report_type=report_type, limit=limit)
        ready_records = sum(record.ready is True for record in records)
        failed_records = sum(record.ready is False for record in records)

        latest_failed_check_names: list[str] = []
        failed_check_counter: Counter[str] = Counter()
        recent_records: list[dict[str, Any]] = []

        for index, record in enumerate(records):
            entry = record.as_dict()
            if record.ready is False:
                details = self.read_details(record)
                entry["failed_check_names"] = details.failed_check_names
                failed_check_counter.update(details.failed_check_names)
                if index == 0:
                    latest_failed_check_names = details.failed_check_names
            recent_records.append(entry)

        total_records = len(records)
        readiness_rate = (
            round(ready_records / total_records, 4)
            if total_records
            else 0.0
        )

        return ArchivedReportTrend(
            total_records=total_records,
            ready_records=ready_records,
            failed_records=failed_records,
            readiness_rate=readiness_rate,
            latest_saved_at=records[0].saved_at if records else None,
            latest_ready=records[0].ready if records else None,
            last_ready_at=next((record.saved_at for record in records if record.ready is True), None),
            last_failed_at=next((record.saved_at for record in records if record.ready is False), None),
            latest_failed_check_names=latest_failed_check_names,
            failed_check_counts=dict(failed_check_counter),
            recent_records=recent_records,
        )

    def read_details(self, record: ArchivedReportRecord) -> ArchivedReportDetails:
        candidate_paths = [Path(record.archive_path)]
        if record.latest_path:
            candidate_paths.append(Path(record.latest_path))

        envelope: dict[str, Any] | None = None
        for path in candidate_paths:
            if path.exists():
                envelope = json.loads(path.read_text(encoding="utf-8"))
                break

        if envelope is None:
            raise FileNotFoundError(f"Archived report not found: {record.archive_path}")

        return self._build_details(record, envelope)

    def _read_index(self, *, report_type: str | None = None) -> list[ArchivedReportRecord]:
        index_path = self.base_dir / "index.jsonl"
        if not index_path.exists():
            return []

        normalized_type = self._normalize_report_type(report_type)
        records: list[ArchivedReportRecord] = []

        with index_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                record = ArchivedReportRecord(
                    report_type=payload["report_type"],
                    saved_at=payload["saved_at"],
                    archive_path=payload["archive_path"],
                    latest_path=payload.get("latest_path"),
                    ready=payload.get("ready"),
                    summary=payload.get("summary") or {},
                )
                if normalized_type is not None and record.report_type != normalized_type:
                    continue
                records.append(record)

        records.reverse()
        return records

    @staticmethod
    def _build_details(
        record: ArchivedReportRecord,
        envelope: dict[str, Any],
    ) -> ArchivedReportDetails:
        payload = envelope.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        checks = payload.get("checks") or []
        failed_check_names = [
            check.get("name")
            for check in checks
            if isinstance(check, dict) and check.get("passed") is False and check.get("name")
        ]

        return ArchivedReportDetails(
            record=record,
            checked_at=payload.get("checked_at"),
            failed_check_names=failed_check_names,
            payload=payload,
        )

    @staticmethod
    def _normalize_report_type(report_type: str | None) -> str | None:
        if report_type is None:
            return None
        return FileReportArchive._safe_slug(report_type)
