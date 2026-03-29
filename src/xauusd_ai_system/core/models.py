from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import EntryType, MarketState, TradeSide, WarningLevel


def _to_primitive(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {key: _to_primitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_primitive(item) for item in value]
    return value


@dataclass
class MarketSnapshot:
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    open: float
    high: float
    low: float
    close: float
    session_tag: str = "unknown"
    news_flag: bool = False
    minutes_to_event: int | None = None
    minutes_from_event: int | None = None
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.features = {str(key).lower(): value for key, value in self.features.items()}

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def mid_price(self) -> float:
        return (self.ask + self.bid) / 2.0

    def feature(self, name: str, default: Any = None) -> Any:
        return self.features.get(name.lower(), default)


@dataclass
class StateDecision:
    state_label: MarketState
    confidence_score: float
    reason_codes: list[str] = field(default_factory=list)
    bias: TradeSide | None = None
    blocked_by_risk: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "state_label": self.state_label.value,
            "confidence_score": self.confidence_score,
            "reason_codes": list(self.reason_codes),
            "bias": self.bias.value if self.bias else None,
            "blocked_by_risk": self.blocked_by_risk,
        }


@dataclass
class TradeSignal:
    strategy_name: str
    side: TradeSide
    entry_type: EntryType
    entry_price: float
    stop_loss: float
    take_profit: float
    signal_reason: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "side": self.side.value,
            "entry_type": self.entry_type.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "signal_reason": list(self.signal_reason),
            "metadata": _to_primitive(self.metadata),
        }


@dataclass
class RiskDecision:
    allowed: bool
    risk_reason: list[str] = field(default_factory=list)
    position_size: float = 0.0
    risk_per_unit: float = 0.0
    max_risk_amount: float = 0.0
    position_scale: float = 1.0
    advisory: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_reason": list(self.risk_reason),
            "position_size": self.position_size,
            "risk_per_unit": self.risk_per_unit,
            "max_risk_amount": self.max_risk_amount,
            "position_scale": self.position_scale,
            "advisory": list(self.advisory),
        }


@dataclass
class AccountState:
    equity: float
    daily_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    consecutive_losses: int = 0
    open_positions: int = 0
    protective_mode: bool = False


@dataclass
class VolatilityAlert:
    warning_level: WarningLevel
    forecast_horizon_minutes: int
    risk_score: float
    reason_codes: list[str] = field(default_factory=list)
    suggested_action: str = "observe"

    def as_dict(self) -> dict[str, Any]:
        return {
            "warning_level": self.warning_level.value,
            "forecast_horizon_minutes": self.forecast_horizon_minutes,
            "risk_score": self.risk_score,
            "reason_codes": list(self.reason_codes),
            "suggested_action": self.suggested_action,
        }


@dataclass
class VolatilityAssessment:
    primary_alert: VolatilityAlert
    horizon_alerts: list[VolatilityAlert] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "primary_alert": self.primary_alert.as_dict(),
            "horizon_alerts": [alert.as_dict() for alert in self.horizon_alerts],
        }


@dataclass
class TradingDecision:
    state: StateDecision
    volatility: VolatilityAssessment | None
    signal: TradeSignal | None
    risk: RiskDecision
    audit: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.as_dict(),
            "volatility": self.volatility.as_dict() if self.volatility else None,
            "signal": self.signal.as_dict() if self.signal else None,
            "risk": self.risk.as_dict(),
            "audit": _to_primitive(self.audit),
        }
