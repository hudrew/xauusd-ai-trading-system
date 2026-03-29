from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BrokerAccountSnapshot:
    timestamp: datetime
    equity: float
    balance: float | None = None
    open_positions: int = 0
    trade_allowed: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class AccountStateProvider(ABC):
    platform: str

    @abstractmethod
    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        raise NotImplementedError
