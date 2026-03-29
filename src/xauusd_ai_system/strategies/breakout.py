from __future__ import annotations

from ..config.schema import BreakoutStrategyConfig
from ..core.enums import EntryType, MarketState, TradeSide
from ..core.models import MarketSnapshot, StateDecision, TradeSignal
from .base import Strategy


class BreakoutStrategy(Strategy):
    name = "breakout"

    def __init__(self, config: BreakoutStrategyConfig) -> None:
        self.config = config

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        state_decision: StateDecision,
    ) -> TradeSignal | None:
        if state_decision.state_label != MarketState.TREND_BREAKOUT:
            return None

        side = state_decision.bias
        if side is None:
            return None

        if self.config.require_retest_confirmation and not bool(
            snapshot.feature("breakout_retest_confirmed", False)
        ):
            return None

        stop_distance = self._stop_distance(snapshot)
        if stop_distance <= 0:
            return None

        entry_price = snapshot.ask if side == TradeSide.BUY else snapshot.bid
        stop_loss = (
            entry_price - stop_distance
            if side == TradeSide.BUY
            else entry_price + stop_distance
        )
        take_profit = (
            entry_price + stop_distance * self.config.take_profit_rr
            if side == TradeSide.BUY
            else entry_price - stop_distance * self.config.take_profit_rr
        )

        entry_type = (
            EntryType.RETEST if self.config.entry_mode == "retest" else EntryType.MARKET
        )
        return TradeSignal(
            strategy_name=self.name,
            side=side,
            entry_type=entry_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_reason=[
                "STATE_TREND_BREAKOUT",
                "BREAKOUT_RETEST_CONFIRMED"
                if entry_type == EntryType.RETEST
                else "BREAKOUT_MARKET_ENTRY",
            ],
            metadata={
                "max_hold_bars": self.config.max_hold_bars,
                "partial_take_profit_rr": self.config.partial_take_profit_rr,
            },
        )

    def _stop_distance(self, snapshot: MarketSnapshot) -> float:
        atr_distance = abs(float(snapshot.feature("atr_m1_14", 0.0))) * float(
            self.config.stop_loss_atr_multiplier
        )
        structural_distance = abs(float(snapshot.feature("structural_stop_distance", 0.0)))
        return max(atr_distance, structural_distance)

