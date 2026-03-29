from __future__ import annotations

from ..config.schema import MeanReversionStrategyConfig
from ..core.enums import EntryType, MarketState, TradeSide
from ..core.models import MarketSnapshot, StateDecision, TradeSignal
from .base import Strategy


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"

    def __init__(self, config: MeanReversionStrategyConfig) -> None:
        self.config = config

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        state_decision: StateDecision,
    ) -> TradeSignal | None:
        if state_decision.state_label != MarketState.RANGE_MEAN_REVERSION:
            return None

        range_position = snapshot.feature("range_position")
        if range_position is None:
            return None
        range_position = float(range_position)

        side = self._resolve_side(snapshot, range_position)
        if side is None:
            return None

        stop_distance = self._stop_distance(snapshot)
        if stop_distance <= 0:
            return None

        entry_price = snapshot.ask if side == TradeSide.BUY else snapshot.bid
        rr_target = stop_distance * self.config.take_profit_rr
        midline_distance = abs(float(snapshot.feature("midline_target_distance", 0.0)))
        target_distance = midline_distance or rr_target
        take_profit = (
            entry_price + target_distance
            if side == TradeSide.BUY
            else entry_price - target_distance
        )
        stop_loss = (
            entry_price - stop_distance
            if side == TradeSide.BUY
            else entry_price + stop_distance
        )

        return TradeSignal(
            strategy_name=self.name,
            side=side,
            entry_type=EntryType.MARKET,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_reason=["STATE_RANGE_MEAN_REVERSION", "BOUNDARY_REJECTION_CONFIRMED"],
            metadata={"max_hold_bars": self.config.max_hold_bars},
        )

    def _resolve_side(
        self,
        snapshot: MarketSnapshot,
        range_position: float,
    ) -> TradeSide | None:
        rejection_up = bool(snapshot.feature("rejection_up", False))
        rejection_down = bool(snapshot.feature("rejection_down", False))

        if range_position <= self.config.lower_range_position and rejection_up:
            return TradeSide.BUY
        if range_position >= self.config.upper_range_position and rejection_down:
            return TradeSide.SELL
        return None

    def _stop_distance(self, snapshot: MarketSnapshot) -> float:
        atr_distance = abs(float(snapshot.feature("atr_m1_14", 0.0))) * float(
            self.config.stop_loss_atr_multiplier
        )
        boundary_buffer = abs(float(snapshot.feature("range_boundary_buffer", 0.0)))
        return max(atr_distance, boundary_buffer)

