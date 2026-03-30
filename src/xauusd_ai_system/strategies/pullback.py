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

        if not self._side_allowed(side):
            return None

        if not self._entry_hour_allowed(snapshot):
            return None

        if not self._required_state_reasons_present(state_decision):
            return None

        if self.config.require_m1_reversal_confirmation and not bool(
            snapshot.feature("m1_reversal_confirmed", False)
        ):
            return None

        if self._below_minimum_entry_quality(snapshot, side):
            return None

        if self._pullback_too_extended(snapshot, side):
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
                *self._signal_reasons(state_decision),
            ],
            metadata={"max_hold_bars": self.config.max_hold_bars},
        )

    def _required_state_reasons_present(self, state_decision: StateDecision) -> bool:
        required = {
            str(reason).strip().upper()
            for reason in self.config.required_state_reasons
            if str(reason).strip()
        }
        if not required:
            return True

        available = {
            str(reason).strip().upper()
            for reason in state_decision.reason_codes
            if str(reason).strip()
        }
        return required.issubset(available)

    def _side_allowed(self, side: TradeSide) -> bool:
        allowed = {
            str(value).strip().lower()
            for value in self.config.allowed_sides
            if str(value).strip()
        }
        if not allowed:
            return True
        return side.value.lower() in allowed

    def _entry_hour_allowed(self, snapshot: MarketSnapshot) -> bool:
        min_entry_hour = self.config.min_entry_hour
        max_entry_hour = self.config.max_entry_hour
        if min_entry_hour is None and max_entry_hour is None:
            return True

        hour = int(snapshot.timestamp.hour)
        if min_entry_hour is not None and hour < int(min_entry_hour):
            return False
        if max_entry_hour is not None and hour > int(max_entry_hour):
            return False
        return True

    def _signal_reasons(self, state_decision: StateDecision) -> list[str]:
        reasons: list[str] = []
        if self.config.require_m1_reversal_confirmation:
            reasons.append("M1_REVERSAL_CONFIRMED")
        reasons.extend(
            reason
            for reason in self.config.required_state_reasons
            if reason in state_decision.reason_codes and reason not in reasons
        )
        reasons.append("REFERENCE_DISTANCE_OK")
        return reasons

    def _pullback_too_extended(
        self,
        snapshot: MarketSnapshot,
        side: TradeSide,
    ) -> bool:
        if self._reference_distance_too_large(snapshot):
            return True
        return self._directional_entry_too_stretched(snapshot, side)

    def _below_minimum_entry_quality(
        self,
        snapshot: MarketSnapshot,
        side: TradeSide,
    ) -> bool:
        if (
            float(snapshot.feature("pullback_depth", 0.0))
            < float(self.config.min_pullback_depth)
        ):
            return True

        if abs(float(snapshot.feature("atr_m1_14", 0.0))) < float(self.config.min_atr_m1):
            return True

        if abs(float(snapshot.feature("atr_m5_14", 0.0))) < float(self.config.min_atr_m5):
            return True

        if (
            float(snapshot.feature("volatility_ratio", 0.0))
            < float(self.config.min_volatility_ratio)
        ):
            return True

        return self._directional_distance_too_small(snapshot, side)

    def _directional_distance_too_small(
        self,
        snapshot: MarketSnapshot,
        side: TradeSide,
    ) -> bool:
        min_distance_atr = float(self.config.min_directional_distance_to_ema20_atr)
        if min_distance_atr <= 0:
            return False

        atr_reference = max(
            abs(float(snapshot.feature("atr_m5_14", 0.0))),
            abs(float(snapshot.feature("atr_m1_14", 0.0))),
        )
        if atr_reference <= 0:
            return False

        min_distance = atr_reference * min_distance_atr
        ema_distance = float(snapshot.feature("price_distance_to_ema20", 0.0))
        if side == TradeSide.BUY:
            return ema_distance < min_distance
        return ema_distance > -min_distance

    def _reference_distance_too_large(self, snapshot: MarketSnapshot) -> bool:
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

    def _directional_entry_too_stretched(
        self,
        snapshot: MarketSnapshot,
        side: TradeSide,
    ) -> bool:
        directional_extension_atr = float(
            self.config.max_directional_extension_atr
        )
        if directional_extension_atr <= 0:
            return False

        atr_reference = max(
            abs(float(snapshot.feature("atr_m5_14", 0.0))),
            abs(float(snapshot.feature("atr_m1_14", 0.0))),
        )
        if atr_reference <= 0:
            return False

        max_extension = atr_reference * directional_extension_atr
        ema_distance = float(snapshot.feature("price_distance_to_ema20", 0.0))
        vwap_distance = float(snapshot.feature("vwap_deviation", 0.0))
        range_position = float(snapshot.feature("range_position", 0.5))
        bollinger_position = float(snapshot.feature("bollinger_position", 0.5))
        edge_threshold = float(self.config.edge_position_threshold)

        if side == TradeSide.BUY:
            return (
                ema_distance > max_extension
                and vwap_distance > max_extension
                and max(range_position, bollinger_position) >= edge_threshold
            )

        return (
            ema_distance < -max_extension
            and vwap_distance < -max_extension
            and min(range_position, bollinger_position) <= 1.0 - edge_threshold
        )

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
