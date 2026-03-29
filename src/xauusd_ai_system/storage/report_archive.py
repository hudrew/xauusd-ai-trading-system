from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ..config.schema import ReportArchiveConfig


@dataclass
class ArchivedReportRecord:
    report_type: str
    saved_at: str
    archive_path: str
    latest_path: str | None
    ready: bool | None
    summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "saved_at": self.saved_at,
            "archive_path": self.archive_path,
            "latest_path": self.latest_path,
            "ready": self.ready,
            "summary": self.summary,
        }


class FileReportArchive:
    def __init__(self, config: ReportArchiveConfig) -> None:
        self.config = config
        self.base_dir = self._resolve_base_dir(config.base_dir)

    def save(
        self,
        report_type: str,
        payload: dict[str, Any],
        *,
        summary: dict[str, Any] | None = None,
        ready: bool | None = None,
    ) -> ArchivedReportRecord | None:
        if not self.config.enabled:
            return None

        safe_type = self._safe_slug(report_type)
        saved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
        report_dir = self.base_dir / safe_type
        report_dir.mkdir(parents=True, exist_ok=True)

        archive_path = report_dir / f"{saved_at}.json"
        latest_path = report_dir / "latest.json" if self.config.write_latest else None

        envelope = {
            "report_type": safe_type,
            "saved_at": saved_at,
            "ready": ready,
            "summary": summary or {},
            "payload": payload,
        }
        archive_path.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if latest_path is not None:
            latest_path.write_text(
                json.dumps(envelope, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        record = ArchivedReportRecord(
            report_type=safe_type,
            saved_at=saved_at,
            archive_path=str(archive_path),
            latest_path=str(latest_path) if latest_path is not None else None,
            ready=ready,
            summary=summary or {},
        )
        self._append_index(record)
        return record

    def _append_index(self, record: ArchivedReportRecord) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        index_path = self.base_dir / "index.jsonl"
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _resolve_base_dir(base_dir: str) -> Path:
        path = Path(base_dir)
        if path.is_absolute():
            return path
        project_root = Path(__file__).resolve().parents[3]
        return project_root / path

    @staticmethod
    def _safe_slug(value: str) -> str:
        slug = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip().lower())
        return slug.strip("-") or "report"
