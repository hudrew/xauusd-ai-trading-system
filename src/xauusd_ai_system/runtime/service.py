from __future__ import annotations

import logging

from ..alerts.notifier import AlertNotifier
from ..config.schema import NotificationConfig
from ..core.enums import WarningLevel
from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..core.pipeline import TradingSystem
from ..execution.base import ExecutionOrder, ExecutionResult, ExecutionSyncResult
from ..execution.service import ExecutionService
from ..storage.repository import AuditRepository


LOGGER = logging.getLogger(__name__)


class TradingRuntimeService:
    def __init__(
        self,
        system: TradingSystem,
        repository: AuditRepository,
        notifier: AlertNotifier,
        notification_config: NotificationConfig,
        execution_service: ExecutionService | None = None,
        dry_run: bool = True,
    ) -> None:
        self.system = system
        self.repository = repository
        self.notifier = notifier
        self.notification_config = notification_config
        self.execution_service = execution_service
        self.dry_run = dry_run

    def process_snapshot(
        self,
        snapshot: MarketSnapshot,
        account_state: AccountState,
    ) -> TradingDecision:
        decision = self.system.evaluate(snapshot, account_state)
        execution_result: ExecutionResult | None = None
        execution_sync_result: ExecutionSyncResult | None = None
        order: ExecutionOrder | None = None
        if (
            self.execution_service is not None
            and not self.dry_run
            and decision.signal is not None
            and decision.risk.allowed
        ):
            order = self.execution_service.build_order(decision.signal, decision.risk)
            if order is not None:
                execution_result = self.execution_service.submit_order(order)
                execution_sync_result = self.execution_service.sync_execution_state(
                    order=order,
                    execution_result=execution_result,
                )
        if (
            self.execution_service is not None
            and not self.dry_run
            and execution_sync_result is None
        ):
            execution_sync_result = self.execution_service.reconcile_execution_state(
                symbol=snapshot.symbol
            )
        self.repository.save_evaluation(snapshot, account_state, decision)
        if order is not None and execution_result is not None:
            self.repository.save_execution_attempt(
                snapshot,
                decision,
                order,
                execution_result,
            )
            if execution_sync_result is not None:
                self.repository.save_execution_sync(
                    snapshot,
                    order,
                    execution_result,
                    execution_sync_result,
                )
        elif execution_sync_result is not None and self._should_persist_execution_sync(
            execution_sync_result
        ):
            self.repository.save_execution_sync(
                snapshot,
                None,
                None,
                execution_sync_result,
            )
        self._log_decision(snapshot, decision, execution_result, execution_sync_result)
        self._dispatch_notifications(snapshot, decision)
        return decision

    def shutdown(self) -> None:
        self.repository.close()

    def _dispatch_notifications(
        self,
        snapshot: MarketSnapshot,
        decision: TradingDecision,
    ) -> None:
        if not self.notification_config.enabled or decision.volatility is None:
            return

        primary_alert = decision.volatility.primary_alert
        min_level = WarningLevel(self.notification_config.min_warning_level)
        if self._compare_levels(primary_alert.warning_level, min_level) < 0:
            return

        message = self.notifier.format_message(snapshot, decision.volatility)
        self.notifier.send(message, self.notification_config)

    def _log_decision(
        self,
        snapshot: MarketSnapshot,
        decision: TradingDecision,
        execution_result: object | None = None,
        execution_sync_result: object | None = None,
    ) -> None:
        LOGGER.info(
            "decision_processed",
            extra={
                "extra_payload": {
                    "symbol": snapshot.symbol,
                    "timestamp": snapshot.timestamp.isoformat(),
                    "state_label": decision.state.state_label.value,
                    "risk_allowed": decision.risk.allowed,
                    "volatility_level": (
                        decision.volatility.primary_alert.warning_level.value
                        if decision.volatility is not None
                        else None
                    ),
                    "execution_accepted": (
                        execution_result.accepted if execution_result is not None else None
                    ),
                    "execution_order_id": (
                        execution_result.order_id if execution_result is not None else None
                    ),
                    "execution_error": (
                        execution_result.error_message
                        if execution_result is not None
                        else None
                    ),
                    "execution_result": getattr(execution_result, "raw_response", None),
                    "execution_sync_status": (
                        execution_sync_result.sync_status
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_open_orders": (
                        len(execution_sync_result.open_orders)
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_open_positions": (
                        len(execution_sync_result.open_positions)
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_position_ticket": (
                        execution_sync_result.position_ticket
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_position_identifier": (
                        execution_sync_result.position_identifier
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_history_orders": (
                        len(execution_sync_result.history_orders)
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_history_deals": (
                        len(execution_sync_result.history_deals)
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_history_order_state": (
                        execution_sync_result.history_order_state
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_history_deal_ticket": (
                        execution_sync_result.history_deal_ticket
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_history_deal_entry": (
                        execution_sync_result.history_deal_entry
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_history_deal_reason": (
                        execution_sync_result.history_deal_reason
                        if execution_sync_result is not None
                        else None
                    ),
                    "execution_sync_error": (
                        execution_sync_result.error_message
                        if execution_sync_result is not None
                        else None
                    ),
                }
            },
        )

    @staticmethod
    def _compare_levels(left: WarningLevel, right: WarningLevel) -> int:
        ranking = {
            WarningLevel.INFO: 0,
            WarningLevel.WARNING: 1,
            WarningLevel.CRITICAL: 2,
        }
        return ranking[left] - ranking[right]

    def _should_persist_execution_sync(
        self,
        sync_result: ExecutionSyncResult,
    ) -> bool:
        if sync_result.sync_origin != "reconcile":
            return True

        latest_summary = self.repository.load_latest_execution_sync_summary(
            symbol=sync_result.symbol,
            platform=sync_result.platform,
        )
        if latest_summary is None:
            return sync_result.sync_status != "no_tracked_activity"

        return self._execution_sync_fingerprint_from_result(
            sync_result
        ) != self._execution_sync_fingerprint_from_summary(latest_summary)

    @staticmethod
    def _execution_sync_fingerprint_from_result(
        sync_result: ExecutionSyncResult,
    ) -> dict[str, object | None]:
        return {
            "sync_origin": sync_result.sync_origin,
            "sync_status": sync_result.sync_status,
            "requested_order_id": sync_result.requested_order_id,
            "requested_price": TradingRuntimeService._round_float(
                sync_result.requested_price,
                digits=6,
            ),
            "observed_price": TradingRuntimeService._round_float(
                sync_result.observed_price,
                digits=6,
            ),
            "observed_price_source": sync_result.observed_price_source,
            "position_ticket": sync_result.position_ticket,
            "position_identifier": sync_result.position_identifier,
            "history_order_state": sync_result.history_order_state,
            "history_deal_ticket": sync_result.history_deal_ticket,
            "history_deal_entry": sync_result.history_deal_entry,
            "history_deal_reason": sync_result.history_deal_reason,
            "price_offset": TradingRuntimeService._round_float(
                sync_result.price_offset,
                digits=6,
            ),
            "adverse_slippage_points": TradingRuntimeService._round_float(
                sync_result.adverse_slippage_points,
                digits=2,
            ),
            "open_order_count": len(sync_result.open_orders),
            "open_position_count": len(sync_result.open_positions),
            "history_order_count": len(sync_result.history_orders),
            "history_deal_count": len(sync_result.history_deals),
            "error_message": sync_result.error_message,
        }

    @staticmethod
    def _execution_sync_fingerprint_from_summary(
        summary: dict[str, object],
    ) -> dict[str, object | None]:
        return {
            "sync_origin": summary.get("sync_origin"),
            "sync_status": summary.get("sync_status"),
            "requested_order_id": summary.get("requested_order_id"),
            "requested_price": TradingRuntimeService._round_float(
                summary.get("requested_price"),
                digits=6,
            ),
            "observed_price": TradingRuntimeService._round_float(
                summary.get("observed_price"),
                digits=6,
            ),
            "observed_price_source": summary.get("observed_price_source"),
            "position_ticket": summary.get("position_ticket"),
            "position_identifier": summary.get("position_identifier"),
            "history_order_state": summary.get("history_order_state"),
            "history_deal_ticket": summary.get("history_deal_ticket"),
            "history_deal_entry": summary.get("history_deal_entry"),
            "history_deal_reason": summary.get("history_deal_reason"),
            "price_offset": TradingRuntimeService._round_float(
                summary.get("price_offset"),
                digits=6,
            ),
            "adverse_slippage_points": TradingRuntimeService._round_float(
                summary.get("adverse_slippage_points"),
                digits=2,
            ),
            "open_order_count": summary.get("open_order_count"),
            "open_position_count": summary.get("open_position_count"),
            "history_order_count": summary.get("history_order_count"),
            "history_deal_count": summary.get("history_deal_count"),
            "error_message": summary.get("error_message"),
        }

    @staticmethod
    def _round_float(value: object | None, *, digits: int) -> float | None:
        if value is None:
            return None
        try:
            return round(float(value), digits)
        except (TypeError, ValueError):
            return None
