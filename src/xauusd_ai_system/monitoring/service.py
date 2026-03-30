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
            "paper": {
                "window_start": None,
                "window_end": None,
                "window_span_minutes": 0.0,
                "latest_equity": None,
                "equity_change": 0.0,
                "equity_change_pct": 0.0,
                "latest_daily_pnl_pct": None,
                "max_drawdown_pct": 0.0,
                "latest_open_positions": 0,
                "max_open_positions": 0,
                "average_spread": None,
                "max_spread": None,
                "candidate_signals": 0,
                "allowed_candidates": 0,
                "blocked_candidates": 0,
                "execution_accept_rate": 0.0,
            },
            "pressure": {
                "risk_reasons": [],
                "risk_advisories": [],
                "execution_errors": [],
                "execution_statuses": [],
                "execution_sync_statuses": [],
                "execution_sync_origins": [],
                "execution_sync_close_statuses": [],
                "execution_sync_deal_reasons": [],
            },
            "execution_sync": {
                "latest_status": None,
                "latest_origin": None,
                "latest_requested_order_id": None,
                "latest_requested_price": None,
                "latest_open_order_count": 0,
                "latest_open_position_count": 0,
                "latest_history_order_count": 0,
                "latest_history_deal_count": 0,
                "latest_history_deal_ticket": None,
                "latest_position_ticket": None,
                "latest_position_identifier": None,
                "latest_history_order_state": None,
                "latest_history_deal_entry": None,
                "latest_history_deal_reason": None,
                "latest_observed_price": None,
                "latest_observed_price_source": None,
                "latest_price_offset": None,
                "latest_adverse_slippage_points": None,
                "average_adverse_slippage_points": None,
                "max_adverse_slippage_points": None,
                "tracked_sync_count": 0,
                "recent_submission_count": 0,
                "recent_reconcile_count": 0,
                "recent_close_event_count": 0,
                "recent_tp_close_count": 0,
                "recent_sl_close_count": 0,
                "recent_manual_close_count": 0,
                "recent_expert_close_count": 0,
                "recent_attention_count": 0,
                "latest_is_attention": False,
                "latest_error_message": None,
            },
            "latest_decision": None,
            "recent_alerts": [],
            "recent_decisions": [],
            "recent_executions": [],
            "recent_execution_syncs": [],
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
            recent_execution_syncs = self._load_recent_execution_syncs(
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
        snapshot["paper"] = self._build_paper_summary(recent_decisions, recent_executions)
        snapshot["pressure"] = self._build_pressure(
            recent_decisions,
            recent_executions,
            recent_execution_syncs,
        )
        snapshot["execution_sync"] = self._build_execution_sync_summary(
            recent_execution_syncs
        )
        snapshot["latest_decision"] = recent_decisions[0] if recent_decisions else None
        snapshot["recent_alerts"] = [
            decision
            for decision in recent_decisions
            if decision["volatility_level"] in {"warning", "critical"}
        ][:alert_limit]
        snapshot["recent_decisions"] = recent_decisions
        snapshot["recent_executions"] = recent_executions
        snapshot["recent_execution_syncs"] = recent_execution_syncs
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

    def _load_recent_execution_syncs(
        self,
        connection: sqlite3.Connection,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not self._table_exists(connection, "execution_syncs"):
            return []

        rows = connection.execute(
            """
            SELECT
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
            FROM execution_syncs
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        sync_rows: list[dict[str, Any]] = []
        for row in rows:
            payload = self._load_json(row["payload_json"])
            sync_result = self._as_mapping(payload.get("sync_result"))
            sync_response = self._as_mapping(sync_result.get("raw_response"))
            order_payload = self._as_mapping(payload.get("order"))
            sync_rows.append(
                {
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "platform": row["platform"],
                    "requested_order_id": row["requested_order_id"],
                    "accepted": bool(row["accepted"]),
                    "sync_status": row["sync_status"],
                    "sync_origin": self._coalesce(
                        sync_result.get("sync_origin"),
                        sync_response.get("sync_origin"),
                        "submission",
                    ),
                    "open_order_count": int(row["open_order_count"]),
                    "open_position_count": int(row["open_position_count"]),
                    "error_message": row["error_message"],
                    "requested_price": self._coalesce_float(
                        sync_result.get("requested_price"),
                        sync_response.get("requested_price"),
                        order_payload.get("price"),
                    ),
                    "observed_price": self._coalesce_float(
                        sync_result.get("observed_price"),
                        sync_response.get("observed_price"),
                    ),
                    "observed_price_source": self._coalesce(
                        sync_result.get("observed_price_source"),
                        sync_response.get("observed_price_source"),
                    ),
                    "position_ticket": self._coalesce(
                        sync_result.get("position_ticket"),
                        sync_response.get("position_ticket"),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("open_positions")),
                            "ticket",
                        ),
                    ),
                    "position_identifier": self._coalesce(
                        sync_result.get("position_identifier"),
                        sync_response.get("position_identifier"),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("open_positions")),
                            "identifier",
                        ),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("history_deals")),
                            "position_id",
                        ),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("history_orders")),
                            "position_id",
                        ),
                    ),
                    "history_order_state": self._coalesce(
                        sync_result.get("history_order_state"),
                        sync_response.get("history_order_state"),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("history_orders")),
                            "state",
                        ),
                    ),
                    "history_deal_ticket": self._coalesce(
                        sync_result.get("history_deal_ticket"),
                        sync_response.get("history_deal_ticket"),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("history_deals")),
                            "ticket",
                        ),
                    ),
                    "history_deal_entry": self._coalesce(
                        sync_result.get("history_deal_entry"),
                        sync_response.get("history_deal_entry"),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("history_deals")),
                            "entry",
                        ),
                    ),
                    "history_deal_reason": self._coalesce(
                        sync_result.get("history_deal_reason"),
                        sync_response.get("history_deal_reason"),
                        self._first_non_empty_value(
                            self._list_of_mappings(sync_result.get("history_deals")),
                            "reason",
                        ),
                    ),
                    "price_offset": self._coalesce_float(
                        sync_result.get("price_offset"),
                        sync_response.get("price_offset"),
                    ),
                    "adverse_slippage": self._coalesce_float(
                        sync_result.get("adverse_slippage"),
                        sync_response.get("adverse_slippage"),
                    ),
                    "adverse_slippage_points": self._coalesce_float(
                        sync_result.get("adverse_slippage_points"),
                        sync_response.get("adverse_slippage_points"),
                    ),
                    "history_orders": self._list_of_mappings(
                        sync_result.get("history_orders")
                    ),
                    "history_deals": self._list_of_mappings(
                        sync_result.get("history_deals")
                    ),
                    "open_orders": self._list_of_mappings(sync_result.get("open_orders")),
                    "open_positions": self._list_of_mappings(
                        sync_result.get("open_positions")
                    ),
                }
            )
            sync_rows[-1]["history_order_count"] = len(sync_rows[-1]["history_orders"])
            sync_rows[-1]["history_deal_count"] = len(sync_rows[-1]["history_deals"])
            sync_rows[-1]["latest_history_deal_ticket"] = self._first_non_empty_string(
                sync_rows[-1]["history_deals"],
                "ticket",
            )
        return sync_rows

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

    def _build_paper_summary(
        self,
        recent_decisions: list[dict[str, Any]],
        recent_executions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not recent_decisions:
            return {
                "window_start": None,
                "window_end": None,
                "window_span_minutes": 0.0,
                "latest_equity": None,
                "equity_change": 0.0,
                "equity_change_pct": 0.0,
                "latest_daily_pnl_pct": None,
                "max_drawdown_pct": 0.0,
                "latest_open_positions": 0,
                "max_open_positions": 0,
                "average_spread": None,
                "max_spread": None,
                "candidate_signals": 0,
                "allowed_candidates": 0,
                "blocked_candidates": 0,
                "execution_accept_rate": 0.0,
            }

        latest = recent_decisions[0]
        earliest = recent_decisions[-1]
        latest_timestamp = self._parse_timestamp(latest["timestamp"])
        earliest_timestamp = self._parse_timestamp(earliest["timestamp"])
        span_minutes = 0.0
        if latest_timestamp is not None and earliest_timestamp is not None:
            span_minutes = max(
                (latest_timestamp - earliest_timestamp).total_seconds() / 60.0,
                0.0,
            )

        latest_equity = float(latest["account_equity"])
        earliest_equity = float(earliest["account_equity"])
        equity_change = latest_equity - earliest_equity
        candidate_signals = sum(1 for item in recent_decisions if item["signal_strategy"])
        allowed_candidates = sum(
            1
            for item in recent_decisions
            if item["signal_strategy"] and item["risk_allowed"]
        )
        execution_accept_rate = (
            sum(1 for item in recent_executions if item["accepted"]) / len(recent_executions)
            if recent_executions
            else 0.0
        )
        spreads = [float(item["spread"]) for item in recent_decisions]

        return {
            "window_start": earliest["timestamp"],
            "window_end": latest["timestamp"],
            "window_span_minutes": round(span_minutes, 2),
            "latest_equity": latest_equity,
            "equity_change": round(equity_change, 4),
            "equity_change_pct": round(equity_change / earliest_equity, 6)
            if earliest_equity
            else 0.0,
            "latest_daily_pnl_pct": float(latest["daily_pnl_pct"]),
            "max_drawdown_pct": round(
                max(float(item["drawdown_pct"]) for item in recent_decisions),
                6,
            ),
            "latest_open_positions": int(latest["open_positions"]),
            "max_open_positions": max(int(item["open_positions"]) for item in recent_decisions),
            "average_spread": round(sum(spreads) / len(spreads), 4) if spreads else None,
            "max_spread": round(max(spreads), 4) if spreads else None,
            "candidate_signals": candidate_signals,
            "allowed_candidates": allowed_candidates,
            "blocked_candidates": max(candidate_signals - allowed_candidates, 0),
            "execution_accept_rate": round(execution_accept_rate, 4),
        }

    def _build_pressure(
        self,
        recent_decisions: list[dict[str, Any]],
        recent_executions: list[dict[str, Any]],
        recent_execution_syncs: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        risk_reason_counter = Counter(
            reason
            for item in recent_decisions
            if not item["risk_allowed"]
            for reason in item["risk_reason"]
        )
        advisory_counter = Counter(
            reason
            for item in recent_decisions
            for reason in item["risk_advisory"]
        )
        execution_error_counter = Counter(
            self._execution_error_label(item)
            for item in recent_executions
            if not item["accepted"]
        )
        execution_status_counter = Counter(
            "accepted" if item["accepted"] else "rejected"
            for item in recent_executions
        )
        execution_sync_status_counter = Counter(
            item["sync_status"] or "unknown" for item in recent_execution_syncs
        )
        execution_sync_origin_counter = Counter(
            item["sync_origin"] or "unknown" for item in recent_execution_syncs
        )
        execution_sync_close_status_counter = Counter(
            item["sync_status"]
            for item in recent_execution_syncs
            if self._is_close_status(item["sync_status"])
        )
        execution_sync_deal_reason_counter = Counter(
            item["history_deal_reason"]
            for item in recent_execution_syncs
            if item["history_deal_reason"] not in (None, "")
        )
        return {
            "risk_reasons": self._counter_to_rows(risk_reason_counter),
            "risk_advisories": self._counter_to_rows(advisory_counter),
            "execution_errors": self._counter_to_rows(execution_error_counter),
            "execution_statuses": self._counter_to_rows(execution_status_counter),
            "execution_sync_statuses": self._counter_to_rows(
                execution_sync_status_counter
            ),
            "execution_sync_origins": self._counter_to_rows(
                execution_sync_origin_counter
            ),
            "execution_sync_close_statuses": self._counter_to_rows(
                execution_sync_close_status_counter
            ),
            "execution_sync_deal_reasons": self._counter_to_rows(
                execution_sync_deal_reason_counter
            ),
        }

    @classmethod
    def _build_execution_sync_summary(
        cls,
        recent_execution_syncs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not recent_execution_syncs:
            return {
                "latest_status": None,
                "latest_origin": None,
                "latest_requested_order_id": None,
                "latest_requested_price": None,
                "latest_open_order_count": 0,
                "latest_open_position_count": 0,
                "latest_history_order_count": 0,
                "latest_history_deal_count": 0,
                "latest_history_deal_ticket": None,
                "latest_position_ticket": None,
                "latest_position_identifier": None,
                "latest_history_order_state": None,
                "latest_history_deal_entry": None,
                "latest_history_deal_reason": None,
                "latest_observed_price": None,
                "latest_observed_price_source": None,
                "latest_price_offset": None,
                "latest_adverse_slippage_points": None,
                "average_adverse_slippage_points": None,
                "max_adverse_slippage_points": None,
                "tracked_sync_count": 0,
                "recent_submission_count": 0,
                "recent_reconcile_count": 0,
                "recent_close_event_count": 0,
                "recent_tp_close_count": 0,
                "recent_sl_close_count": 0,
                "recent_manual_close_count": 0,
                "recent_expert_close_count": 0,
                "recent_attention_count": 0,
                "latest_is_attention": False,
                "latest_error_message": None,
            }

        latest = recent_execution_syncs[0]
        tracked_slippage_points = [
            float(item["adverse_slippage_points"])
            for item in recent_execution_syncs
            if item["adverse_slippage_points"] is not None
        ]
        recent_submission_count = sum(
            1 for item in recent_execution_syncs if item["sync_origin"] == "submission"
        )
        recent_reconcile_count = sum(
            1 for item in recent_execution_syncs if item["sync_origin"] == "reconcile"
        )
        recent_close_event_count = sum(
            1
            for item in recent_execution_syncs
            if cls._is_close_status(item["sync_status"])
        )
        recent_tp_close_count = sum(
            1
            for item in recent_execution_syncs
            if item["sync_status"] == "position_closed_tp"
        )
        recent_sl_close_count = sum(
            1
            for item in recent_execution_syncs
            if item["sync_status"] == "position_closed_sl"
        )
        recent_manual_close_count = sum(
            1
            for item in recent_execution_syncs
            if item["sync_status"] == "position_closed_manual"
        )
        recent_expert_close_count = sum(
            1
            for item in recent_execution_syncs
            if item["sync_status"] == "position_closed_expert"
        )
        recent_attention_count = sum(
            1
            for item in recent_execution_syncs
            if cls._is_attention_sync_status(item["sync_status"])
        )
        return {
            "latest_status": latest["sync_status"],
            "latest_origin": latest["sync_origin"],
            "latest_requested_order_id": latest["requested_order_id"],
            "latest_requested_price": latest["requested_price"],
            "latest_open_order_count": latest["open_order_count"],
            "latest_open_position_count": latest["open_position_count"],
            "latest_history_order_count": latest["history_order_count"],
            "latest_history_deal_count": latest["history_deal_count"],
            "latest_history_deal_ticket": latest["latest_history_deal_ticket"],
            "latest_position_ticket": latest["position_ticket"],
            "latest_position_identifier": latest["position_identifier"],
            "latest_history_order_state": latest["history_order_state"],
            "latest_history_deal_entry": latest["history_deal_entry"],
            "latest_history_deal_reason": latest["history_deal_reason"],
            "latest_observed_price": latest["observed_price"],
            "latest_observed_price_source": latest["observed_price_source"],
            "latest_price_offset": latest["price_offset"],
            "latest_adverse_slippage_points": latest["adverse_slippage_points"],
            "average_adverse_slippage_points": round(
                sum(tracked_slippage_points) / len(tracked_slippage_points),
                2,
            )
            if tracked_slippage_points
            else None,
            "max_adverse_slippage_points": round(max(tracked_slippage_points), 2)
            if tracked_slippage_points
            else None,
            "tracked_sync_count": len(tracked_slippage_points),
            "recent_submission_count": recent_submission_count,
            "recent_reconcile_count": recent_reconcile_count,
            "recent_close_event_count": recent_close_event_count,
            "recent_tp_close_count": recent_tp_close_count,
            "recent_sl_close_count": recent_sl_close_count,
            "recent_manual_close_count": recent_manual_close_count,
            "recent_expert_close_count": recent_expert_close_count,
            "recent_attention_count": recent_attention_count,
            "latest_is_attention": cls._is_attention_sync_status(latest["sync_status"]),
            "latest_error_message": latest["error_message"],
        }

    @staticmethod
    def _is_close_status(status: Any) -> bool:
        if status in (None, ""):
            return False
        return str(status).startswith("position_closed")

    @staticmethod
    def _is_attention_sync_status(status: Any) -> bool:
        if status in (None, ""):
            return False
        normalized = str(status)
        if normalized.startswith("sync_"):
            return True
        return normalized in {
            "accepted_not_visible",
            "accepted_unmatched",
            "rejected",
            "order_rejected",
            "position_closed_stopout",
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

    @staticmethod
    def _first_non_empty_string(rows: list[dict[str, Any]], key: str) -> str | None:
        for row in rows:
            value = row.get(key)
            if value not in (None, ""):
                return str(value)
        return None

    @staticmethod
    def _first_non_empty_value(rows: list[dict[str, Any]], key: str) -> Any:
        for row in rows:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _execution_error_label(execution: dict[str, Any]) -> str:
        if execution.get("accepted"):
            return "accepted"

        error_message = str(execution.get("error_message") or "").strip()
        if error_message:
            return error_message

        response = execution.get("response")
        if isinstance(response, dict):
            for key in ("message", "comment", "retcode", "code"):
                value = response.get(key)
                if value not in (None, ""):
                    return f"{key}:{value}"
        return "rejected_without_error"
