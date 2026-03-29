from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import MarketSnapshot

CORE_REQUIRED_FEATURES = {
    "atr_m1_14",
    "breakout_distance",
    "ema_slope_20",
    "false_break_count",
    "spread_ratio",
    "volatility_ratio",
}


@dataclass
class FeatureValidation:
    valid: bool
    missing_features: list[str] = field(default_factory=list)


class FeatureEngine:
    """Validates that the minimum feature set exists before routing decisions."""

    def __init__(self, required_features: set[str] | None = None) -> None:
        self.required_features = required_features or set(CORE_REQUIRED_FEATURES)

    def validate(self, snapshot: MarketSnapshot) -> FeatureValidation:
        missing = [
            feature_name
            for feature_name in sorted(self.required_features)
            if snapshot.feature(feature_name) is None
        ]
        return FeatureValidation(valid=not missing, missing_features=missing)

