from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PreflightCheck:
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
class PreflightReport:
    platform: str
    ready: bool
    checks: list[PreflightCheck] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "ready": self.ready,
            "checked_at": self.checked_at.isoformat(),
            "checks": [item.as_dict() for item in self.checks],
        }
