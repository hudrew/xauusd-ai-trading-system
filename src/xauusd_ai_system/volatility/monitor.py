from __future__ import annotations

from ..config.schema import VolatilityMonitorConfig
from ..core.enums import WarningLevel
from ..core.models import MarketSnapshot, VolatilityAlert, VolatilityAssessment


class VolatilityMonitor:
    def __init__(self, config: VolatilityMonitorConfig) -> None:
        self.config = config

    def assess(self, snapshot: MarketSnapshot) -> VolatilityAssessment:
        alerts = [self._build_alert(snapshot, horizon) for horizon in self.config.horizons_minutes]
        primary_alert = max(alerts, key=self._severity_key)
        return VolatilityAssessment(primary_alert=primary_alert, horizon_alerts=alerts)

    def _build_alert(self, snapshot: MarketSnapshot, horizon: int) -> VolatilityAlert:
        reasons: list[str] = []
        score = 0.0

        atr_expansion = max(
            self._float(snapshot, "atr_expansion_ratio"),
            self._float(snapshot, "volatility_ratio"),
        )
        spread_ratio = self._float(snapshot, "spread_ratio", 1.0)
        tick_speed = self._float(snapshot, "tick_speed", 1.0)
        breakout_pressure = abs(
            max(
                self._float(snapshot, "breakout_pressure"),
                self._float(snapshot, "breakout_distance"),
            )
        )
        minutes_to_event = snapshot.minutes_to_event

        if atr_expansion >= self.config.atr_expansion_trigger:
            reasons.append("ATR_EXPAND")
            score += self._bounded_ratio(
                atr_expansion,
                self.config.atr_expansion_trigger,
                self.config.atr_expansion_trigger * 1.8,
                weight=0.34,
            )

        if spread_ratio >= self.config.spread_ratio_trigger:
            reasons.append("SPREAD_EXPAND")
            score += self._bounded_ratio(
                spread_ratio,
                self.config.spread_ratio_trigger,
                self.config.spread_ratio_trigger * 1.6,
                weight=0.18,
            )

        if tick_speed >= self.config.tick_speed_trigger:
            reasons.append("TICK_SPEED_UP")
            score += self._bounded_ratio(
                tick_speed,
                self.config.tick_speed_trigger,
                self.config.tick_speed_trigger * 1.6,
                weight=0.16,
            )

        if breakout_pressure >= self.config.breakout_pressure_trigger:
            reasons.append("BREAKOUT_PRESSURE")
            score += self._bounded_ratio(
                breakout_pressure,
                self.config.breakout_pressure_trigger,
                self.config.breakout_pressure_trigger * 2.5,
                weight=0.18,
            )

        if snapshot.news_flag or self._near_event(minutes_to_event):
            reasons.append("NEWS_NEAR")
            score += 0.22

        if snapshot.session_tag.lower() in {"eu", "us", "overlap", "london", "newyork"}:
            reasons.append("ACTIVE_SESSION")
            score += 0.06

        horizon_multiplier = self._horizon_multiplier(horizon)
        score = min(round(score * horizon_multiplier, 2), 1.0)
        level = self._warning_level(score)
        action = self._suggested_action(level)
        if not reasons:
            reasons.append("VOLATILITY_NORMAL")

        return VolatilityAlert(
            warning_level=level,
            forecast_horizon_minutes=horizon,
            risk_score=score,
            reason_codes=reasons,
            suggested_action=action,
        )

    def _warning_level(self, score: float) -> WarningLevel:
        if score >= self.config.critical_score_min:
            return WarningLevel.CRITICAL
        if score >= self.config.warning_score_min:
            return WarningLevel.WARNING
        return WarningLevel.INFO

    def _suggested_action(self, level: WarningLevel) -> str:
        if level == WarningLevel.CRITICAL:
            return "block_new_trade" if self.config.block_on_critical else "reduce_risk"
        if level == WarningLevel.WARNING:
            return "reduce_risk"
        return "observe"

    @staticmethod
    def _bounded_ratio(
        value: float,
        threshold: float,
        ceiling: float,
        weight: float,
    ) -> float:
        if value <= threshold:
            return 0.0
        span = max(ceiling - threshold, 1e-9)
        normalized = min((value - threshold) / span, 1.0)
        return normalized * weight

    def _near_event(self, minutes_to_event: int | None) -> bool:
        return (
            minutes_to_event is not None
            and 0 <= minutes_to_event <= self.config.news_proximity_minutes
        )

    @staticmethod
    def _float(snapshot: MarketSnapshot, name: str, default: float = 0.0) -> float:
        value = snapshot.feature(name, default)
        if value is None:
            return default
        return float(value)

    @staticmethod
    def _severity_key(alert: VolatilityAlert) -> tuple[int, float, int]:
        return (
            {"info": 0, "warning": 1, "critical": 2}[alert.warning_level.value],
            alert.risk_score,
            alert.forecast_horizon_minutes,
        )

    @staticmethod
    def _horizon_multiplier(horizon: int) -> float:
        if horizon <= 5:
            return 1.00
        if horizon <= 15:
            return 0.95
        return 0.88
