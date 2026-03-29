from __future__ import annotations

from ..config.schema import RiskConfig, VolatilityMonitorConfig
from ..core.enums import WarningLevel
from ..core.models import (
    AccountState,
    MarketSnapshot,
    RiskDecision,
    TradeSignal,
    VolatilityAssessment,
)


class RiskManager:
    def __init__(
        self,
        config: RiskConfig,
        volatility_config: VolatilityMonitorConfig | None = None,
    ) -> None:
        self.config = config
        self.volatility_config = volatility_config or VolatilityMonitorConfig()

    def assess(
        self,
        snapshot: MarketSnapshot,
        signal: TradeSignal | None,
        account_state: AccountState,
        volatility_assessment: VolatilityAssessment | None = None,
    ) -> RiskDecision:
        reasons: list[str] = []
        advisories: list[str] = []
        position_scale = 1.0
        if signal is None:
            reasons.append("NO_SIGNAL")
            return RiskDecision(
                allowed=False,
                risk_reason=reasons,
                advisory=advisories,
                position_scale=position_scale,
            )

        if account_state.protective_mode:
            reasons.append("ACCOUNT_PROTECTIVE_MODE")
        if account_state.drawdown_pct >= self.config.protective_drawdown_pct:
            reasons.append("DRAWDOWN_LIMIT_REACHED")
        if abs(account_state.daily_pnl_pct) >= self.config.max_daily_loss_pct and (
            account_state.daily_pnl_pct < 0
        ):
            reasons.append("DAILY_LOSS_LIMIT_REACHED")
        if account_state.consecutive_losses >= self.config.max_consecutive_losses:
            reasons.append("CONSECUTIVE_LOSS_LIMIT_REACHED")
        if account_state.open_positions >= self.config.max_open_positions:
            reasons.append("MAX_OPEN_POSITIONS_REACHED")

        spread_ratio = float(snapshot.feature("spread_ratio", 1.0))
        if spread_ratio > self.config.max_spread_ratio:
            reasons.append("SPREAD_LIMIT_REACHED")
        if snapshot.news_flag or bool(snapshot.feature("news_flag", False)):
            reasons.append("NEWS_BLOCK")

        if signal.strategy_name in {"breakout", "pullback"}:
            available_votes, aligned_votes = self._trend_alignment(snapshot, signal.side)
            required_alignment = 1 if available_votes <= 1 else min(2, available_votes)
            if available_votes > 0 and aligned_votes <= 0:
                reasons.append("MTF_TREND_MISMATCH")
            elif aligned_votes < required_alignment:
                position_scale = min(position_scale, self.config.partial_alignment_scale)
                advisories.append("MTF_PARTIAL_ALIGNMENT")

        if volatility_assessment is not None:
            primary_alert = volatility_assessment.primary_alert
            if primary_alert.warning_level == WarningLevel.CRITICAL:
                if self.volatility_config.block_on_critical:
                    reasons.append("VOLATILITY_CRITICAL_BLOCK")
                else:
                    position_scale = min(
                        position_scale, self.volatility_config.warning_position_scale
                    )
                    advisories.append("VOLATILITY_CRITICAL_REDUCE_RISK")
            elif primary_alert.warning_level == WarningLevel.WARNING:
                position_scale = min(
                    position_scale, self.volatility_config.warning_position_scale
                )
                advisories.append("VOLATILITY_WARNING_REDUCE_RISK")
            elif primary_alert.warning_level == WarningLevel.INFO:
                position_scale = min(
                    position_scale, self.volatility_config.info_position_scale
                )
                advisories.append("VOLATILITY_INFO_OBSERVE")

        risk_per_unit = abs(signal.entry_price - signal.stop_loss) * self.config.contract_size
        if risk_per_unit <= 0:
            reasons.append("INVALID_STOP_DISTANCE")

        if reasons:
            return RiskDecision(
                allowed=False,
                risk_reason=reasons,
                risk_per_unit=risk_per_unit,
                max_risk_amount=account_state.equity * self.config.max_single_trade_risk_pct,
                position_scale=position_scale,
                advisory=advisories,
            )

        max_risk_amount = account_state.equity * self.config.max_single_trade_risk_pct
        position_size = (max_risk_amount / risk_per_unit) * position_scale
        return RiskDecision(
            allowed=True,
            risk_reason=[],
            position_size=round(position_size, 6),
            risk_per_unit=round(risk_per_unit, 6),
            max_risk_amount=round(max_risk_amount, 2),
            position_scale=position_scale,
            advisory=advisories,
        )

    def _trend_alignment(
        self,
        snapshot: MarketSnapshot,
        side,
    ) -> tuple[int, int]:
        side_value = getattr(side, "value", side)
        votes = [
            self._timeframe_vote(snapshot, timeframe)
            for timeframe in ("m5", "m15", "h1")
        ]
        available_votes = sum(vote is not None for vote in votes)
        aligned_votes = sum(vote == side_value for vote in votes)
        return available_votes, aligned_votes

    @staticmethod
    def _timeframe_vote(snapshot: MarketSnapshot, timeframe: str) -> str | None:
        ema20_name = f"ema20_{timeframe}"
        ema60_name = f"ema60_{timeframe}"
        slope_name = "ema_slope_20" if timeframe == "m5" else f"ema_slope_20_{timeframe}"

        ema20 = snapshot.feature(ema20_name)
        ema60 = snapshot.feature(ema60_name)
        if ema20 is None or ema60 is None:
            return None

        ema20 = float(ema20)
        ema60 = float(ema60)
        slope = snapshot.feature(slope_name, 0.0)
        slope = 0.0 if slope is None else float(slope)

        if ema20 > ema60 and slope >= 0:
            return "buy"
        if ema20 < ema60 and slope <= 0:
            return "sell"
        return None
