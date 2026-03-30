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

        if self.config.require_m1_reversal_confirmation and not bool(
            snapshot.feature("m1_reversal_confirmed", False)
        ):
            return None

        if self._breakout_too_extended(snapshot):
            return None

        if self._mean_reversion_entry_too_stretched(snapshot):
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

    def _breakout_too_extended(self, snapshot: MarketSnapshot) -> bool:
        max_breakout_distance_atr = float(self.config.max_breakout_distance_atr)
        if max_breakout_distance_atr <= 0:
            return False

        atr_reference = abs(float(snapshot.feature("atr_m1_14", 0.0)))
        if atr_reference <= 0:
            return False

        breakout_distance = abs(float(snapshot.feature("breakout_distance", 0.0)))
        return breakout_distance > atr_reference * max_breakout_distance_atr

    def _mean_reversion_entry_too_stretched(self, snapshot: MarketSnapshot) -> bool:
        max_price_distance_atr = float(self.config.max_price_distance_to_ema20_atr)
        if max_price_distance_atr <= 0:
            return False

        atr_reference = abs(float(snapshot.feature("atr_m1_14", 0.0)))
        if atr_reference <= 0:
            return False

        distance_to_ema = abs(float(snapshot.feature("price_distance_to_ema20", 0.0)))
        return distance_to_ema > atr_reference * max_price_distance_atr

    def _stop_distance(self, snapshot: MarketSnapshot) -> float:
        atr_distance = abs(float(snapshot.feature("atr_m1_14", 0.0))) * float(
            self.config.stop_loss_atr_multiplier
        )
        boundary_buffer = abs(float(snapshot.feature("range_boundary_buffer", 0.0)))
        return max(atr_distance, boundary_buffer)
