from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


@dataclass
class AccountStateBaseline:
    day_key: str
    start_equity: float
    peak_equity: float
    updated_at: datetime


class SQLiteAccountStateStore:
    def __init__(self, database_url: str, auto_create: bool = True) -> None:
        self.path = self._resolve_path(database_url)
        if auto_create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def get_or_create(
        self,
        day_key: str,
        *,
        fallback_equity: float,
    ) -> AccountStateBaseline:
        row = self.connection.execute(
            """
            SELECT day_key, start_equity, peak_equity, updated_at
            FROM account_state_daily_baselines
            WHERE day_key = ?
            """,
            (day_key,),
        ).fetchone()
        if row is not None:
            return AccountStateBaseline(
                day_key=str(row["day_key"]),
                start_equity=float(row["start_equity"]),
                peak_equity=float(row["peak_equity"]),
                updated_at=datetime.fromisoformat(str(row["updated_at"])),
            )

        baseline = AccountStateBaseline(
            day_key=day_key,
            start_equity=float(fallback_equity),
            peak_equity=float(fallback_equity),
            updated_at=datetime.now(timezone.utc),
        )
        self.save(baseline)
        return baseline

    def save(self, baseline: AccountStateBaseline) -> None:
        self.connection.execute(
            """
            INSERT INTO account_state_daily_baselines (
                day_key,
                start_equity,
                peak_equity,
                updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(day_key) DO UPDATE SET
                start_equity = excluded.start_equity,
                peak_equity = excluded.peak_equity,
                updated_at = excluded.updated_at
            """,
            (
                baseline.day_key,
                baseline.start_equity,
                baseline.peak_equity,
                baseline.updated_at.isoformat(),
            ),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS account_state_daily_baselines (
                day_key TEXT PRIMARY KEY,
                start_equity REAL NOT NULL,
                peak_equity REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    @staticmethod
    def _resolve_path(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite URLs are supported by SQLiteAccountStateStore.")
        return Path(database_url[len(prefix) :])
