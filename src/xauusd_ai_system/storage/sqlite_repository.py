from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..execution.base import ExecutionOrder, ExecutionResult, ExecutionSyncResult
from .repository import AuditRepository


class SQLiteAuditRepository(AuditRepository):
    def __init__(self, database_url: str, auto_create: bool = True) -> None:
        self.path = self._resolve_path(database_url)
        if auto_create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                session_tag TEXT NOT NULL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                close REAL NOT NULL,
                account_equity REAL NOT NULL,
                daily_pnl_pct REAL NOT NULL,
                drawdown_pct REAL NOT NULL,
                open_positions INTEGER NOT NULL,
                state_label TEXT,
                volatility_level TEXT,
                risk_allowed INTEGER NOT NULL,
                position_size REAL NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                platform TEXT NOT NULL,
                strategy_name TEXT,
                accepted INTEGER NOT NULL,
                order_id TEXT,
                error_message TEXT,
                order_payload_json TEXT NOT NULL,
                response_payload_json TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_syncs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                platform TEXT NOT NULL,
                requested_order_id TEXT,
                accepted INTEGER NOT NULL,
                sync_status TEXT NOT NULL,
                open_order_count INTEGER NOT NULL,
                open_position_count INTEGER NOT NULL,
                error_message TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_evaluation(
        self,
        snapshot: MarketSnapshot,
        account_state: AccountState,
        decision: TradingDecision,
    ) -> None:
        volatility_level = (
            decision.volatility.primary_alert.warning_level.value
            if decision.volatility is not None
            else None
        )
        self.connection.execute(
            """
            INSERT INTO evaluations (
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.timestamp.isoformat(),
                snapshot.symbol,
                snapshot.session_tag,
                snapshot.bid,
                snapshot.ask,
                snapshot.close,
                account_state.equity,
                account_state.daily_pnl_pct,
                account_state.drawdown_pct,
                account_state.open_positions,
                decision.state.state_label.value,
                volatility_level,
                int(decision.risk.allowed),
                decision.risk.position_size,
                json.dumps(
                    {
                        "snapshot": {
                            "features": snapshot.features,
                            "minutes_to_event": snapshot.minutes_to_event,
                            "minutes_from_event": snapshot.minutes_from_event,
                            "news_flag": snapshot.news_flag,
                        },
                        "decision": decision.as_dict(),
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        self.connection.commit()

    def save_execution_attempt(
        self,
        snapshot: MarketSnapshot,
        decision: TradingDecision,
        order: ExecutionOrder,
        execution_result: ExecutionResult,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO execution_attempts (
                timestamp,
                symbol,
                platform,
                strategy_name,
                accepted,
                order_id,
                error_message,
                order_payload_json,
                response_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.timestamp.isoformat(),
                snapshot.symbol,
                execution_result.platform,
                decision.signal.strategy_name if decision.signal is not None else None,
                int(execution_result.accepted),
                execution_result.order_id,
                execution_result.error_message,
                json.dumps(order.payload, ensure_ascii=False),
                json.dumps(execution_result.raw_response, ensure_ascii=False),
            ),
        )
        self.connection.commit()

    def save_execution_sync(
        self,
        snapshot: MarketSnapshot,
        order: ExecutionOrder | None,
        execution_result: ExecutionResult | None,
        sync_result: ExecutionSyncResult,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO execution_syncs (
                timestamp,
                symbol,
                platform,
                requested_order_id,
                accepted,
                sync_status,
                open_order_count,
                open_position_count,
                error_message,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.timestamp.isoformat(),
                snapshot.symbol,
                sync_result.platform,
                sync_result.requested_order_id
                or (execution_result.order_id if execution_result is not None else None),
                int(sync_result.accepted),
                sync_result.sync_status,
                len(sync_result.open_orders),
                len(sync_result.open_positions),
                sync_result.error_message,
                json.dumps(
                    {
                        "order": order.payload if order is not None else None,
                        "execution_result": (
                            {
                                "accepted": execution_result.accepted,
                                "platform": execution_result.platform,
                                "order_id": execution_result.order_id,
                                "raw_response": execution_result.raw_response,
                                "error_message": execution_result.error_message,
                            }
                            if execution_result is not None
                            else None
                        ),
                        "sync_result": {
                            "platform": sync_result.platform,
                            "symbol": sync_result.symbol,
                            "requested_order_id": sync_result.requested_order_id,
                            "accepted": sync_result.accepted,
                            "sync_status": sync_result.sync_status,
                            "sync_origin": sync_result.sync_origin,
                            "requested_price": sync_result.requested_price,
                            "observed_price": sync_result.observed_price,
                            "observed_price_source": sync_result.observed_price_source,
                            "position_ticket": sync_result.position_ticket,
                            "position_identifier": sync_result.position_identifier,
                            "history_order_state": sync_result.history_order_state,
                            "history_deal_ticket": sync_result.history_deal_ticket,
                            "history_deal_entry": sync_result.history_deal_entry,
                            "history_deal_reason": sync_result.history_deal_reason,
                            "price_offset": sync_result.price_offset,
                            "adverse_slippage": sync_result.adverse_slippage,
                            "adverse_slippage_points": sync_result.adverse_slippage_points,
                            "open_orders": sync_result.open_orders,
                            "open_positions": sync_result.open_positions,
                            "history_orders": sync_result.history_orders,
                            "history_deals": sync_result.history_deals,
                            "raw_response": sync_result.raw_response,
                            "error_message": sync_result.error_message,
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        self.connection.commit()

    def load_latest_execution_sync_summary(
        self,
        *,
        symbol: str,
        platform: str,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT
                requested_order_id,
                sync_status,
                open_order_count,
                open_position_count,
                error_message,
                payload_json
            FROM execution_syncs
            WHERE symbol = ? AND platform = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (symbol, platform),
        ).fetchone()
        if row is None:
            return None

        payload = self._load_json(row["payload_json"])
        sync_result = self._as_mapping(payload.get("sync_result"))
        raw_response = self._as_mapping(sync_result.get("raw_response"))
        history_orders = self._list_of_mappings(sync_result.get("history_orders"))
        history_deals = self._list_of_mappings(sync_result.get("history_deals"))
        return {
            "requested_order_id": row["requested_order_id"],
            "sync_status": row["sync_status"],
            "sync_origin": self._coalesce(
                sync_result.get("sync_origin"),
                raw_response.get("sync_origin"),
                "submission",
            ),
            "requested_price": self._coalesce_float(
                sync_result.get("requested_price"),
                raw_response.get("requested_price"),
            ),
            "observed_price": self._coalesce_float(
                sync_result.get("observed_price"),
                raw_response.get("observed_price"),
            ),
            "observed_price_source": self._coalesce(
                sync_result.get("observed_price_source"),
                raw_response.get("observed_price_source"),
            ),
            "position_ticket": self._coalesce(
                sync_result.get("position_ticket"),
                raw_response.get("position_ticket"),
            ),
            "position_identifier": self._coalesce(
                sync_result.get("position_identifier"),
                raw_response.get("position_identifier"),
            ),
            "history_order_state": self._coalesce(
                sync_result.get("history_order_state"),
                raw_response.get("history_order_state"),
            ),
            "history_deal_ticket": self._coalesce(
                sync_result.get("history_deal_ticket"),
                raw_response.get("history_deal_ticket"),
            ),
            "history_deal_entry": self._coalesce(
                sync_result.get("history_deal_entry"),
                raw_response.get("history_deal_entry"),
            ),
            "history_deal_reason": self._coalesce(
                sync_result.get("history_deal_reason"),
                raw_response.get("history_deal_reason"),
            ),
            "price_offset": self._coalesce_float(
                sync_result.get("price_offset"),
                raw_response.get("price_offset"),
            ),
            "adverse_slippage_points": self._coalesce_float(
                sync_result.get("adverse_slippage_points"),
                raw_response.get("adverse_slippage_points"),
            ),
            "open_order_count": int(row["open_order_count"]),
            "open_position_count": int(row["open_position_count"]),
            "history_order_count": len(history_orders),
            "history_deal_count": len(history_deals),
            "error_message": row["error_message"],
        }

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _resolve_path(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite URLs are supported by SQLiteAuditRepository.")
        return Path(database_url[len(prefix) :])

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
    def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _coalesce_float(cls, *values: Any) -> float | None:
        for value in values:
            parsed = cls._float_or_none(value)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _coalesce(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None
