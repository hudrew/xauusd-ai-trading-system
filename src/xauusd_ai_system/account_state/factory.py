from __future__ import annotations

from ..config.schema import SystemConfig
from .base import AccountStateProvider
from .ctrader_provider import CTraderAccountStateProvider
from .mt5_provider import MT5AccountStateProvider


def build_account_state_provider(config: SystemConfig) -> AccountStateProvider | None:
    execution_platform = config.execution.platform.lower()
    market_data_platform = config.market_data.platform.lower()
    platform = execution_platform if execution_platform != "none" else market_data_platform

    if platform == "mt5":
        return MT5AccountStateProvider(config)
    if platform == "ctrader":
        return CTraderAccountStateProvider(config)
    if platform == "none":
        return None
    raise ValueError(f"Unsupported account state platform: {platform}")
