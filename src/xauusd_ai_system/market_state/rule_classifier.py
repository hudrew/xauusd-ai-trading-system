from __future__ import annotations

from ..config.schema import StateThresholds
from ..core.enums import MarketState, TradeSide
from ..core.models import MarketSnapshot, StateDecision


class RuleBasedMarketStateClassifier:
    """Rule-first classifier aligned with the supplied design documents."""

    def __init__(self, thresholds: StateThresholds) -> None:
        self.thresholds = thresholds

    def classify(self, snapshot: MarketSnapshot) -> StateDecision:
        if self._is_no_trade(snapshot):
            return StateDecision(
                state_label=MarketState.NO_TRADE,
                confidence_score=1.0,
                reason_codes=self._no_trade_reasons(snapshot),
            )

        breakout_decision = self._classify_breakout(snapshot)
        if breakout_decision is not None:
            return breakout_decision

        pullback_decision = self._classify_pullback(snapshot)
        if pullback_decision is not None:
            return pullback_decision

        range_decision = self._classify_range(snapshot)
        if range_decision is not None:
            return range_decision

        return StateDecision(
            state_label=MarketState.NO_TRADE,
            confidence_score=0.55,
            reason_codes=["STATE_UNCLEAR"],
        )

    def _classify_breakout(self, snapshot: MarketSnapshot) -> StateDecision | None:
        bias = self._trend_bias(snapshot)
        if bias is None:
            return None

        breakout_distance = abs(self._float(snapshot, "breakout_distance"))
        ema_spread = abs(self._ema_spread(snapshot))
        ema_slope = abs(self._float(snapshot, "ema_slope_20"))
        volatility_ratio = self._float(snapshot, "volatility_ratio", default=1.0)
        false_break_count = self._int(snapshot, "false_break_count")
        breakout_hold_ok = not self._bool(snapshot, "breakout_failed")
        alignment_count = self._trend_alignment_count(snapshot, bias)
        required_alignment = self._required_alignment_count(snapshot)

        checks = {
            "BREAKOUT_DISTANCE_OK": breakout_distance
            >= self.thresholds.breakout_distance_min,
            "TREND_ALIGNMENT_OK": ema_spread >= self.thresholds.trend_ema_spread_min,
            "EMA_SLOPE_OK": ema_slope >= self.thresholds.ema_slope_min,
            "VOLATILITY_EXPANSION_OK": volatility_ratio
            >= self.thresholds.volatility_ratio_min,
            "FALSE_BREAK_OK": false_break_count
            <= self.thresholds.breakout_false_break_max,
            "MTF_ALIGNMENT_OK": alignment_count >= required_alignment,
            "BREAKOUT_HOLD_OK": breakout_hold_ok,
        }

        passed = [reason for reason, matched in checks.items() if matched]
        if len(passed) < 6:
            return None

        return StateDecision(
            state_label=MarketState.TREND_BREAKOUT,
            confidence_score=round(len(passed) / len(checks), 2),
            reason_codes=passed + self._alignment_reason_codes(snapshot, bias),
            bias=bias,
        )

    def _classify_pullback(self, snapshot: MarketSnapshot) -> StateDecision | None:
        bias = self._trend_bias(snapshot)
        if bias is None:
            return None

        pullback_depth = abs(self._float(snapshot, "pullback_depth"))
        structure_intact = self._bool(snapshot, "structure_intact", default=True)
        reversal_confirmed = self._bool(snapshot, "m1_reversal_confirmed")
        volatility_ratio = self._float(snapshot, "volatility_ratio", default=1.0)
        alignment_count = self._trend_alignment_count(snapshot, bias)
        required_alignment = self._required_alignment_count(snapshot)

        checks = {
            "TREND_CONTEXT_OK": True,
            "MTF_ALIGNMENT_OK": alignment_count >= required_alignment,
            "PULLBACK_DEPTH_OK": self.thresholds.pullback_depth_min
            <= pullback_depth
            <= self.thresholds.pullback_depth_max,
            "STRUCTURE_INTACT": structure_intact,
            "REVERSAL_CONFIRMED": reversal_confirmed,
            "VOLATILITY_NOT_DEAD": volatility_ratio >= self.thresholds.volatility_floor,
        }

        passed = [reason for reason, matched in checks.items() if matched]
        if len(passed) < 4:
            return None

        return StateDecision(
            state_label=MarketState.PULLBACK_CONTINUATION,
            confidence_score=round(len(passed) / len(checks), 2),
            reason_codes=passed + self._alignment_reason_codes(snapshot, bias),
            bias=bias,
        )

    def _classify_range(self, snapshot: MarketSnapshot) -> StateDecision | None:
        ema_spread = abs(self._ema_spread(snapshot))
        ema_slope = abs(self._float(snapshot, "ema_slope_20"))
        volatility_ratio = self._float(snapshot, "volatility_ratio", default=1.0)
        false_break_count = self._int(snapshot, "false_break_count")
        boundary_touch_count = self._int(snapshot, "boundary_touch_count")
        range_defined = self._bool(snapshot, "range_defined", default=True)
        directional_bias_count = self._dominant_trend_bias_count(snapshot)

        checks = {
            "RANGE_DEFINED": range_defined,
            "EMA_COMPRESSION_OK": ema_spread <= self.thresholds.range_ema_spread_max,
            "EMA_FLAT_OK": ema_slope <= self.thresholds.range_ema_slope_max,
            "VOLATILITY_CONTAINED": volatility_ratio
            <= self.thresholds.range_volatility_max,
            "FALSE_BREAK_COUNT_OK": false_break_count
            >= self.thresholds.range_false_break_min,
            "BOUNDARY_TOUCH_OK": boundary_touch_count
            >= self.thresholds.range_boundary_touch_min,
            "HTF_TREND_FILTER_OK": directional_bias_count
            <= self.thresholds.range_timeframe_bias_max,
        }

        passed = [reason for reason, matched in checks.items() if matched]
        if len(passed) < 6:
            return None

        return StateDecision(
            state_label=MarketState.RANGE_MEAN_REVERSION,
            confidence_score=round(len(passed) / len(checks), 2),
            reason_codes=passed,
        )

    def _is_no_trade(self, snapshot: MarketSnapshot) -> bool:
        return bool(self._no_trade_reasons(snapshot))

    def _no_trade_reasons(self, snapshot: MarketSnapshot) -> list[str]:
        spread_ratio = self._float(snapshot, "spread_ratio", default=1.0)
        volatility_ratio = self._float(snapshot, "volatility_ratio", default=1.0)
        conflict_score = self._float(snapshot, "regime_conflict_score")
        liquidity_flag = self._bool(snapshot, "liquidity_flag")
        trade_block_flag = self._bool(snapshot, "trade_block_flag")

        reasons: list[str] = []
        if snapshot.news_flag or self._bool(snapshot, "news_flag"):
            reasons.append("NEWS_BLOCK")
        if spread_ratio > self.thresholds.spread_ratio_max:
            reasons.append("SPREAD_TOO_WIDE")
        if volatility_ratio < self.thresholds.volatility_floor:
            reasons.append("VOLATILITY_TOO_LOW")
        if conflict_score > self.thresholds.conflict_score_max:
            reasons.append("STATE_CONFLICT")
        if liquidity_flag:
            reasons.append("LIQUIDITY_BAD")
        if trade_block_flag:
            reasons.append("TRADE_BLOCK_FLAG")
        return reasons

    def _trend_bias(self, snapshot: MarketSnapshot) -> TradeSide | None:
        m5_vote = self._timeframe_vote(snapshot, "m5")
        if m5_vote is None:
            return None

        higher_votes = [
            vote
            for vote in (
                self._timeframe_vote(snapshot, "m15"),
                self._timeframe_vote(snapshot, "h1"),
            )
            if vote is not None
        ]
        if any(vote != m5_vote for vote in higher_votes):
            return None

        breakout_distance = self._float(snapshot, "breakout_distance")
        if breakout_distance > 0 and m5_vote != TradeSide.BUY:
            return None
        if breakout_distance < 0 and m5_vote != TradeSide.SELL:
            return None
        return m5_vote

    @staticmethod
    def _float(snapshot: MarketSnapshot, name: str, default: float = 0.0) -> float:
        value = snapshot.feature(name, default)
        if value is None:
            return default
        return float(value)

    @staticmethod
    def _int(snapshot: MarketSnapshot, name: str, default: int = 0) -> int:
        value = snapshot.feature(name, default)
        if value is None:
            return default
        return int(value)

    @staticmethod
    def _bool(snapshot: MarketSnapshot, name: str, default: bool = False) -> bool:
        value = snapshot.feature(name, default)
        return bool(value)

    def _ema_spread(self, snapshot: MarketSnapshot) -> float:
        spread = snapshot.feature("ema_spread")
        if spread is not None:
            return float(spread)
        ema20 = self._float(snapshot, "ema20_m5")
        ema60 = self._float(snapshot, "ema60_m5")
        return ema20 - ema60

    def _timeframe_vote(
        self,
        snapshot: MarketSnapshot,
        timeframe: str,
    ) -> TradeSide | None:
        ema20_name = f"ema20_{timeframe}"
        ema60_name = f"ema60_{timeframe}"
        slope_name = "ema_slope_20" if timeframe == "m5" else f"ema_slope_20_{timeframe}"

        ema20 = snapshot.feature(ema20_name)
        ema60 = snapshot.feature(ema60_name)
        if ema20 is None or ema60 is None:
            return None

        ema20 = float(ema20)
        ema60 = float(ema60)
        slope = self._float(snapshot, slope_name, default=0.0)
        if ema20 > ema60 and slope >= 0:
            return TradeSide.BUY
        if ema20 < ema60 and slope <= 0:
            return TradeSide.SELL
        return None

    def _trend_alignment_count(
        self,
        snapshot: MarketSnapshot,
        bias: TradeSide,
    ) -> int:
        return sum(
            1
            for timeframe in ("m5", "m15", "h1")
            if self._timeframe_vote(snapshot, timeframe) == bias
        )

    def _required_alignment_count(self, snapshot: MarketSnapshot) -> int:
        directional_count = sum(
            self._timeframe_vote(snapshot, timeframe) is not None
            for timeframe in ("m5", "m15", "h1")
        )
        if directional_count <= 1:
            return 1
        return min(self.thresholds.trend_timeframe_alignment_min, directional_count)

    def _dominant_trend_bias_count(self, snapshot: MarketSnapshot) -> int:
        votes = [
            self._timeframe_vote(snapshot, timeframe)
            for timeframe in ("m5", "m15", "h1")
        ]
        buy_count = sum(vote == TradeSide.BUY for vote in votes)
        sell_count = sum(vote == TradeSide.SELL for vote in votes)
        return max(buy_count, sell_count)

    def _alignment_reason_codes(
        self,
        snapshot: MarketSnapshot,
        bias: TradeSide,
    ) -> list[str]:
        reasons: list[str] = []
        if self._timeframe_vote(snapshot, "m15") == bias:
            reasons.append("M15_ALIGNMENT_OK")
        if self._timeframe_vote(snapshot, "h1") == bias:
            reasons.append("H1_ALIGNMENT_OK")
        return reasons
