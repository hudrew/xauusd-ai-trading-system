from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Quote:
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    metadata: dict[str, Any] = field(default_factory=dict)


class MarketDataAdapter(ABC):
    platform: str

    @abstractmethod
    def get_latest_quote(self) -> Quote:
        raise NotImplementedError

    @abstractmethod
    def get_recent_bars(self, count: int) -> list[dict[str, Any]]:
        raise NotImplementedError

