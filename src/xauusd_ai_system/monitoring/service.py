from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any


class MonitoringSnapshotService:
    def __init__(
        self,
        database_url: str,
        *,
        project_root: Path | None = None,
    ) -> None:
        self.database_url = database_url
        self.project_root = project_root or Path(__file__).resolve().parents[3]
        self.database_path = self._resolve_database_path(database_url)

    def build_snapshot(
        self,
        *,
        decision_limit: int = 120,
        execution_limit: int = 40,
        stale_after_seconds: int = 120,
        alert_limit: int = 12,
    ) -> dict[str, Any]:
        generated_at = datetime.now(timezone.utc)
        snapshot: dict[str, Any] = {
            "generated_at": generated_at.isoformat(),
            "database": {
                "url": self.database_url,
                "path": str(self.database_path),
                "exists": self.database_path.exists(),
            },
            "runtime": {
                "status": "missing",
                "stale_after_seconds": stale_after_seconds,
                "latest_timestamp": None,
                "staleness_seconds": None,
            },
            "overview": {
                "decision_window_size": 0,
                "execution_window_size": 0,
                "warning_alerts": 0,
                "critical_alerts": 0,
                "risk_blocked": 0,
                "risk_allowed": 0,
                "risk_block_rate": 0.0,
                "accepted_executions": 0,
                "rejected_executions": 0,
            },
            "mix": {
                "state_labels": [],
                "volatility_levels": [],
                "sessions": [],
                "signal_strategies": [],
            },
            "latest_decision": None,
            "recent_alerts": [],
            "recent_decisions": [],
            "recent_executions": [],
        }
        if not self.database_path.exists():
            return snapshot

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            if not self._table_exists(connection, "evaluations"):
                snapshot["runtime"]["status"] = "inactive"
                return snapshot

            recent_decisions = self._load_recent_decisions(
                connection,
                limit=max(decision_limit, 1),
            )
            recent_executions = self._load_recent_executions(
                connection,
                limit=max(execution_limit, 1),
            )
        finally:
            connection.close()

        latest_timestamp = None
        if recent_decisions:
            latest_timestamp = self._parse_timestamp(recent_decisions[0]["timestamp"])

        snapshot["runtime"] = self._build_runtime_status(
            generated_at,
            latest_timestamp,
            stale_after_seconds=stale_after_seconds,
        )
        snapshot["overview"] = self._build_overview(recent_decisions, recent_executions)
        snapshot["mix"] = self._build_mix(recent_decisions)
        snapshot["latest_decision"] = recent_decisions[0] if recent_decisions else None
        snapshot["recent_alerts"] = [
            decision
            for decision in recent_decisions
            if decision["volatility_level"] in {"warning", "critical"}
        ][:alert_limit]
        snapshot["recent_decisions"] = recent_decisions
        snapshot["recent_executions"] = recent_executions
        return snapshot

    def _load_recent_decisions(
        self,
        connection: sqlite3.Connection,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT
                timestamp,
                symbol,
                session_tag,
                bid,
                ask,
                close,
                account_equity,
                daily_pnl_pct,
                drawdown_pct,
                open_positions,
                state_label,
                volatility_level,
                risk_allowed,
                position_size,
                payload_json
            FROM evaluations
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        decisions: list[dict[str, Any]] = []
        for row in rows:
            payload = self._load_json(row["payload_json"])
            decision_payload = self._as_mapping(payload.get("decision"))
            signal_payload = self._as_mapping(decision_payload.get("signal"))
            volatility_payload = self._as_mapping(decision_payload.get("volatility"))
            primary_alert = self._as_mapping(volatility_payload.get("primary_alert"))
            risk_payload = self._as_mapping(decision_payload.get("risk"))

            decisions.append(
                {
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "session_tag": row["session_tag"],
                    "bid": float(row["bid"]),
                    "ask": float(row["ask"]),
                    "close": float(row["close"]),
                    "spread": round(float(row["ask"]) - float(row["bid"]), 4),
                    "account_equity": float(row["account_equity"]),
                    "daily_pnl_pct": float(row["daily_pnl_pct"]),
                    "drawdown_pct": float(row["drawdown_pct"]),
                    "open_positions": int(row["open_positions"]),
                    "state_label": row["state_label"],
                    "volatility_level": row["volatility_level"] or "info",
                    "volatility_score": self._float_or_none(primary_alert.get("risk_score")),
                    "volatility_reasons": self._list_of_strings(
                        primary_alert.get("reason_codes")
                    ),
                    "suggested_action": primary_alert.get("suggested_action") or "observe",
                    "risk_allowed": bool(row["risk_allowed"]),
                    "position_size": float(row["position_size"]),
                    "risk_reason": self._list_of_strings(risk_payload.get("risk_reason")),
                    "risk_advisory": self._list_of_strings(risk_payload.get("advisory")),
                    "signal_strategy": signal_payload.get("strategy_name"),
                    "signal_side": signal_payload.get("side"),
                    "signal_entry_type": signal_payload.get("entry_type"),
                    "signal_entry_price": self._float_or_none(signal_payload.get("entry_price")),
                    "signal_stop_loss": self._float_or_none(signal_payload.get("stop_loss")),
                    "signal_take_profit": self._float_or_none(signal_payload.get("take_profit")),
                    "signal_reason": self._list_of_strings(signal_payload.get("signal_reason")),
                }
            )
        return decisions

    def _load_recent_executions(
        self,
        connection: sqlite3.Connection,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not self._table_exists(connection, "execution_attempts"):
            return []

        rows = connection.execute(
            """
            SELECT
                timestamp,
                symbol,
                platform,
                strategy_name,
                accepted,
                order_id,
                error_message,
                order_payload_json,
                response_payload_json
            FROM execution_attempts
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        executions: list[dict[str, Any]] = []
        for row in rows:
            order_payload = self._load_json(row["order_payload_json"])
            response_payload = self._load_json(row["response_payload_json"])
            executions.append(
                {
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "platform": row["platform"],
                    "strategy_name": row["strategy_name"],
                    "accepted": bool(row["accepted"]),
                    "order_id": row["order_id"],
                    "error_message": row["error_message"],
                    "order_side": order_payload.get("side"),
                    "order_type": order_payload.get("type") or order_payload.get("order_type"),
                    "order_price": self._float_or_none(
                        order_payload.get("price") or order_payload.get("entry_price")
                    ),
                    "order_volume": self._float_or_none(
                        order_payload.get("volume") or order_payload.get("lot")
                    ),
                    "response": response_payload,
                }
            )
        return executions

    def _build_runtime_status(
        self,
        generated_at: datetime,
        latest_timestamp: datetime | None,
        *,
        stale_after_seconds: int,
    ) -> dict[str, Any]:
        if latest_timestamp is None:
            return {
                "status": "inactive",
                "stale_after_seconds": stale_after_seconds,
                "latest_timestamp": None,
                "staleness_seconds": None,
            }

        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)

        staleness_seconds = max(int((generated_at - latest_timestamp).total_seconds()), 0)
        status = "healthy" if staleness_seconds <= stale_after_seconds else "stale"
        return {
            "status": status,
            "stale_after_seconds": stale_after_seconds,
            "latest_timestamp": latest_timestamp.isoformat(),
            "staleness_seconds": staleness_seconds,
        }

    @staticmethod
    def _build_overview(
        recent_decisions: list[dict[str, Any]],
        recent_executions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        warning_alerts = sum(
            1 for item in recent_decisions if item["volatility_level"] == "warning"
        )
        critical_alerts = sum(
            1 for item in recent_decisions if item["volatility_level"] == "critical"
        )
        risk_blocked = sum(1 for item in recent_decisions if not item["risk_allowed"])
        risk_allowed = len(recent_decisions) - risk_blocked
        accepted_executions = sum(1 for item in recent_executions if item["accepted"])
        rejected_executions = len(recent_executions) - accepted_executions

        return {
            "decision_window_size": len(recent_decisions),
            "execution_window_size": len(recent_executions),
            "warning_alerts": warning_alerts,
            "critical_alerts": critical_alerts,
            "risk_blocked": risk_blocked,
            "risk_allowed": risk_allowed,
            "risk_block_rate": round(
                risk_blocked / len(recent_decisions),
                4,
            )
            if recent_decisions
            else 0.0,
            "accepted_executions": accepted_executions,
            "rejected_executions": rejected_executions,
        }

    def _build_mix(
        self,
        recent_decisions: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        state_counter = Counter(item["state_label"] or "unknown" for item in recent_decisions)
        volatility_counter = Counter(item["volatility_level"] or "unknown" for item in recent_decisions)
        session_counter = Counter(item["session_tag"] or "unknown" for item in recent_decisions)
        strategy_counter = Counter(
            item["signal_strategy"] or "none" for item in recent_decisions
        )
        return {
            "state_labels": self._counter_to_rows(state_counter),
            "volatility_levels": self._counter_to_rows(volatility_counter),
            "sessions": self._counter_to_rows(session_counter),
            "signal_strategies": self._counter_to_rows(strategy_counter),
        }

    @staticmethod
    def _counter_to_rows(counter: Counter[str]) -> list[dict[str, Any]]:
        total = sum(counter.values())
        rows: list[dict[str, Any]] = []
        for name, count in counter.most_common():
            rows.append(
                {
                    "name": name,
                    "count": count,
                    "share": round(count / total, 4) if total else 0.0,
                }
            )
        return rows

    def _resolve_database_path(self, database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Monitoring currently supports sqlite URLs only.")

        raw_path = Path(database_url[len(prefix) :])
        if raw_path.is_absolute():
            return raw_path
        return (self.project_root / raw_path).resolve()

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @staticmethod
    def _load_json(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _as_mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _list_of_strings(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
