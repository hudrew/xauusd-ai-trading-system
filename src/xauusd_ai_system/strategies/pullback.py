from __future__ import annotations

from ..config.schema import PullbackStrategyConfig
from ..core.enums import EntryType, MarketState, TradeSide
from ..core.models import MarketSnapshot, StateDecision, TradeSignal
from .base import Strategy


class PullbackStrategy(Strategy):
    name = "pullback"

    def __init__(self, config: PullbackStrategyConfig) -> None:
        self.config = config

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        state_decision: StateDecision,
    ) -> TradeSignal | None:
        if state_decision.state_label != MarketState.PULLBACK_CONTINUATION:
            return None

        side = state_decision.bias
        if side is None:
            return None

        if self.config.require_m1_reversal_confirmation and not bool(
            snapshot.feature("m1_reversal_confirmed", False)
        ):
            return None

        if self._pullback_too_extended(snapshot):
            return None

        stop_distance = self._stop_distance(snapshot)
        if stop_distance <= 0:
            return None

        entry_price = snapshot.ask if side == TradeSide.BUY else snapshot.bid
        target_distance = self._target_distance(snapshot, side, entry_price, stop_distance)
        if target_distance <= 0:
            return None

        stop_loss = (
            entry_price - stop_distance
            if side == TradeSide.BUY
            else entry_price + stop_distance
        )
        take_profit = (
            entry_price + target_distance
            if side == TradeSide.BUY
            else entry_price - target_distance
        )

        return TradeSignal(
            strategy_name=self.name,
            side=side,
            entry_type=EntryType.MARKET,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_reason=[
                "STATE_PULLBACK_CONTINUATION",
                "M1_REVERSAL_CONFIRMED",
                "VALUE_AREA_RETEST",
            ],
            metadata={"max_hold_bars": self.config.max_hold_bars},
        )

    def _pullback_too_extended(self, snapshot: MarketSnapshot) -> bool:
        atr_reference = max(
            abs(float(snapshot.feature("atr_m5_14", 0.0))),
            abs(float(snapshot.feature("atr_m1_14", 0.0))),
        )
        if atr_reference <= 0:
            return False

        max_allowed_distance = atr_reference * float(
            self.config.max_reference_distance_atr
        )
        ema_distance = abs(float(snapshot.feature("price_distance_to_ema20", 0.0)))
        vwap_distance = abs(float(snapshot.feature("vwap_deviation", 0.0)))
        return ema_distance > max_allowed_distance and vwap_distance > max_allowed_distance

    def _stop_distance(self, snapshot: MarketSnapshot) -> float:
        atr_distance = abs(float(snapshot.feature("atr_m1_14", 0.0))) * float(
            self.config.stop_loss_atr_multiplier
        )
        structural_distance = abs(float(snapshot.feature("structural_stop_distance", 0.0)))
        return max(atr_distance, structural_distance)

    def _target_distance(
        self,
        snapshot: MarketSnapshot,
        side: TradeSide,
        entry_price: float,
        stop_distance: float,
    ) -> float:
        rr_target = stop_distance * float(self.config.take_profit_rr)
        if side == TradeSide.BUY:
            structural_target = float(snapshot.feature("recent_high_n", entry_price)) - entry_price
        else:
            structural_target = entry_price - float(snapshot.feature("recent_low_n", entry_price))
        if structural_target > 0:
            return max(rr_target, structural_target)
        return rr_target
