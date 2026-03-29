from __future__ import annotations

from ..config.schema import MarketDataConfig
from .base import MarketDataAdapter
from .ctrader_adapter import CTraderMarketDataAdapter
from .mt5_adapter import MT5MarketDataAdapter


def build_market_data_adapter(config: MarketDataConfig) -> MarketDataAdapter | None:
    platform = config.platform.lower()
    if platform == "ctrader":
        return CTraderMarketDataAdapter(config)
    if platform == "mt5":
        return MT5MarketDataAdapter(config)
    if platform == "none":
        return None
    raise ValueError(f"Unsupported market data platform: {config.platform}")

