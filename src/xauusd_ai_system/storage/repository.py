from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..execution.base import ExecutionOrder, ExecutionResult


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
    def close(self) -> None:
        raise NotImplementedError
