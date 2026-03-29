from __future__ import annotations

import logging

from ..alerts.notifier import AlertNotifier
from ..config.schema import NotificationConfig
from ..core.enums import WarningLevel
from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..core.pipeline import TradingSystem
from ..execution.base import ExecutionOrder, ExecutionResult
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
        self.repository.save_evaluation(snapshot, account_state, decision)
        if order is not None and execution_result is not None:
            self.repository.save_execution_attempt(
                snapshot,
                decision,
                order,
                execution_result,
            )
        self._log_decision(snapshot, decision, execution_result)
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
