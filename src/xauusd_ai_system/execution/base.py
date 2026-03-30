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


@dataclass
class ExecutionSyncResult:
    platform: str
    symbol: str
    requested_order_id: str | None = None
    accepted: bool = False
    sync_status: str = "unsupported"
    sync_origin: str = "submission"
    requested_price: float | None = None
    observed_price: float | None = None
    observed_price_source: str | None = None
    position_ticket: str | None = None
    position_identifier: str | None = None
    history_order_state: str | None = None
    history_deal_ticket: str | None = None
    history_deal_entry: str | None = None
    history_deal_reason: str | None = None
    price_offset: float | None = None
    adverse_slippage: float | None = None
    adverse_slippage_points: float | None = None
    open_orders: list[dict[str, Any]] = field(default_factory=list)
    open_positions: list[dict[str, Any]] = field(default_factory=list)
    history_orders: list[dict[str, Any]] = field(default_factory=list)
    history_deals: list[dict[str, Any]] = field(default_factory=list)
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

    def sync_execution_state(
        self,
        *,
        order: ExecutionOrder,
        execution_result: ExecutionResult,
    ) -> ExecutionSyncResult | None:
        return None

    def reconcile_execution_state(
        self,
        *,
        symbol: str,
    ) -> ExecutionSyncResult | None:
        return None
