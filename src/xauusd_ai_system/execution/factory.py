from __future__ import annotations

from ..config.schema import ExecutionConfig
from .base import ExecutionAdapter
from .ctrader_adapter import CTraderOpenApiAdapter
from .mt5_adapter import MT5ExecutionAdapter


def build_execution_adapter(config: ExecutionConfig) -> ExecutionAdapter | None:
    platform = config.platform.lower()
    if platform == "ctrader":
        return CTraderOpenApiAdapter(config)
    if platform == "mt5":
        return MT5ExecutionAdapter(config)
    if platform == "none":
        return None
    raise ValueError(f"Unsupported execution platform: {config.platform}")

