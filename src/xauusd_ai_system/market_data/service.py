from __future__ import annotations

from ..config.schema import MarketDataConfig
from .base import MarketDataAdapter, Quote
from .factory import build_market_data_adapter


class MarketDataService:
    def __init__(self, config: MarketDataConfig) -> None:
        self.config = config
        self.adapter = build_market_data_adapter(config)

    def get_latest_quote(self) -> Quote | None:
        if self.adapter is None:
            return None
        return self.adapter.get_latest_quote()

    def get_recent_bars(self, count: int) -> list[dict]:
        if self.adapter is None:
            return []
        return self.adapter.get_recent_bars(count)
