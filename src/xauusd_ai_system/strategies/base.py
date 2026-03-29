from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.models import MarketSnapshot, StateDecision, TradeSignal


class Strategy(ABC):
    name: str

    @abstractmethod
    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        state_decision: StateDecision,
    ) -> TradeSignal | None:
        raise NotImplementedError

