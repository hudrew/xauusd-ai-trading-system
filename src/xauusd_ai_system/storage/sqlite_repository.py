from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..execution.base import ExecutionOrder, ExecutionResult
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

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _resolve_path(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite URLs are supported by SQLiteAuditRepository.")
        return Path(database_url[len(prefix) :])
