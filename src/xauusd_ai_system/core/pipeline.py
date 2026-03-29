from __future__ import annotations

from ..config.schema import SystemConfig
from ..dispatch.strategy_router import StrategyRouter
from ..features.engine import FeatureEngine
from ..market_state.rule_classifier import RuleBasedMarketStateClassifier
from ..risk.manager import RiskManager
from ..strategies.breakout import BreakoutStrategy
from ..strategies.mean_reversion import MeanReversionStrategy
from ..strategies.pullback import PullbackStrategy
from ..volatility.monitor import VolatilityMonitor
from .enums import MarketState
from .models import (
    AccountState,
    MarketSnapshot,
    RiskDecision,
    StateDecision,
    TradingDecision,
)


class TradingSystem:
    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self.feature_engine = FeatureEngine()
        self.classifier = RuleBasedMarketStateClassifier(config.state_thresholds)
        self.volatility_monitor = VolatilityMonitor(config.volatility_monitor)
        self.router = StrategyRouter(
            strategies={
                MarketState.TREND_BREAKOUT: BreakoutStrategy(config.breakout),
                MarketState.PULLBACK_CONTINUATION: PullbackStrategy(config.pullback),
                MarketState.RANGE_MEAN_REVERSION: MeanReversionStrategy(
                    config.mean_reversion
                ),
            }
        )
        self.risk_manager = RiskManager(config.risk, config.volatility_monitor)

    def evaluate(
        self,
        snapshot: MarketSnapshot,
        account_state: AccountState,
    ) -> TradingDecision:
        validation = self.feature_engine.validate(snapshot)
        if not validation.valid:
            state = StateDecision(
                state_label=MarketState.NO_TRADE,
                confidence_score=1.0,
                reason_codes=["MISSING_FEATURES"],
            )
            risk = RiskDecision(
                allowed=False,
                risk_reason=["MISSING_FEATURES"] + validation.missing_features,
            )
            state.blocked_by_risk = True
            return TradingDecision(
                state=state,
                volatility=None,
                signal=None,
                risk=risk,
                audit={"missing_features": validation.missing_features},
            )

        state = self.classifier.classify(snapshot)
        volatility = self.volatility_monitor.assess(snapshot)
        signal = self.router.generate_signal(snapshot, state)
        risk = self.risk_manager.assess(snapshot, signal, account_state, volatility)
        state.blocked_by_risk = signal is not None and not risk.allowed
        return TradingDecision(
            state=state,
            volatility=volatility,
            signal=signal,
            risk=risk,
            audit={
                "feature_validation": validation.valid,
                "primary_volatility_level": volatility.primary_alert.warning_level.value,
            },
        )
