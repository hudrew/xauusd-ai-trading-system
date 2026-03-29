from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..core.models import RiskDecision, TradeSignal


@dataclass
class ExecutionOrder:
    platform: str
    symbol: str
    volume: float
    payload: dict[str, Any]


@dataclass
class ExecutionResult:
    accepted: bool
    platform: str
    order_id: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class ExecutionAdapter(ABC):
    platform: str

    @abstractmethod
    def build_order(
        self,
        signal: TradeSignal,
        risk: RiskDecision,
    ) -> ExecutionOrder:
        raise NotImplementedError

    @abstractmethod
    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        raise NotImplementedError

