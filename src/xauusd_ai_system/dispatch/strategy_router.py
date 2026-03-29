from __future__ import annotations

from ..core.enums import MarketState
from ..core.models import MarketSnapshot, StateDecision, TradeSignal
from ..strategies.base import Strategy


class StrategyRouter:
    def __init__(self, strategies: dict[MarketState, Strategy]) -> None:
        self.strategies = strategies

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        state_decision: StateDecision,
    ) -> TradeSignal | None:
        strategy = self.strategies.get(state_decision.state_label)
        if strategy is None:
            return None
        return strategy.generate_signal(snapshot, state_decision)

