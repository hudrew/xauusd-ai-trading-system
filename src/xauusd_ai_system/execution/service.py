from __future__ import annotations

from ..config.schema import ExecutionConfig
from ..core.models import RiskDecision, TradeSignal
from .base import ExecutionAdapter, ExecutionOrder, ExecutionResult
from .factory import build_execution_adapter


class ExecutionService:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config
        self.adapter = build_execution_adapter(config)

    def build_order(
        self,
        signal: TradeSignal,
        risk: RiskDecision,
    ) -> ExecutionOrder | None:
        if self.adapter is None:
            return None
        return self.adapter.build_order(signal, risk)

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        if self.adapter is None:
            raise RuntimeError("Execution platform is not configured.")
        return self.adapter.submit_order(order)
