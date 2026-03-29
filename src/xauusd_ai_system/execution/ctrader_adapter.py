from __future__ import annotations

from typing import Any

from ..config.schema import ExecutionConfig
from ..core.models import RiskDecision, TradeSignal
from .base import ExecutionAdapter, ExecutionOrder, ExecutionResult


class CTraderOpenApiAdapter(ExecutionAdapter):
    """
    cTrader Open API execution adapter.

    Spotware documents that the official Python SDK is installed with
    `pip install ctrader-open-api`, and supports both demo and live accounts.
    """

    platform = "ctrader"

    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def build_order(
        self,
        signal: TradeSignal,
        risk: RiskDecision,
    ) -> ExecutionOrder:
        payload = {
            "account_id": self.config.ctrader.account_id,
            "symbol": self.config.ctrader.symbol or self.config.symbol,
            "side": signal.side.value,
            "order_type": "market",
            "volume": risk.position_size,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "client_comment": f"{self.config.order_comment_prefix}:{signal.strategy_name}",
        }
        return ExecutionOrder(
            platform=self.platform,
            symbol=payload["symbol"],
            volume=risk.position_size,
            payload=payload,
        )

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        try:
            from ctrader_open_api import Client  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "ctrader-open-api is not installed. Install execution dependencies first."
            ) from exc

        if not self.config.ctrader.account_id:
            raise ValueError("cTrader execution requires execution.ctrader.account_id")

        # The official SDK is asynchronous; we return the payload for the caller to
        # hand off to an event loop or orchestration layer that manages callbacks.
        _ = Client
        return ExecutionResult(
            accepted=True,
            platform=self.platform,
            order_id=None,
            raw_response={"queued_payload": order.payload},
        )
