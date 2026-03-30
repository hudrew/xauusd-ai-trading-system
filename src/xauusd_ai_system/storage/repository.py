from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..execution.base import ExecutionOrder, ExecutionResult, ExecutionSyncResult


class AuditRepository(ABC):
    @abstractmethod
    def save_evaluation(
        self,
        snapshot: MarketSnapshot,
        account_state: AccountState,
        decision: TradingDecision,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_execution_attempt(
        self,
        snapshot: MarketSnapshot,
        decision: TradingDecision,
        order: ExecutionOrder,
        execution_result: ExecutionResult,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_execution_sync(
        self,
        snapshot: MarketSnapshot,
        order: ExecutionOrder | None,
        execution_result: ExecutionResult | None,
        sync_result: ExecutionSyncResult,
    ) -> None:
        raise NotImplementedError

    def load_latest_execution_sync_summary(
        self,
        *,
        symbol: str,
        platform: str,
    ) -> dict[str, Any] | None:
        return None

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
