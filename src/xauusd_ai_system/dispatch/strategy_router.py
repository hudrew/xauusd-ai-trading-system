from __future__ import annotations

from dataclasses import dataclass, field

from ..config.schema import RoutingConfig
from ..core.enums import MarketState
from ..core.models import MarketSnapshot, StateDecision, TradeSignal
from ..strategies.base import Strategy


@dataclass
class RoutingDecision:
    signal: TradeSignal | None = None
    blocked_reasons: list[str] = field(default_factory=list)
    audit: dict[str, object] = field(default_factory=dict)


class StrategyRouter:
    def __init__(
        self,
        strategies: dict[MarketState, Strategy],
        config: RoutingConfig | None = None,
    ) -> None:
        self.strategies = strategies
        self.config = config or RoutingConfig()

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        state_decision: StateDecision,
    ) -> RoutingDecision:
        strategy = self.strategies.get(state_decision.state_label)
        if strategy is None:
            return RoutingDecision()

        signal = strategy.generate_signal(snapshot, state_decision)
        if signal is None:
            return RoutingDecision()

        session_allowed = self._session_allowed(snapshot.session_tag)
        strategy_enabled = self._strategy_enabled(signal.strategy_name)
        blocked_reasons: list[str] = []
        if not session_allowed:
            blocked_reasons.append("SESSION_NOT_ALLOWED")
        if not strategy_enabled:
            blocked_reasons.append("STRATEGY_DISABLED")

        return RoutingDecision(
            signal=signal,
            blocked_reasons=blocked_reasons,
            audit={
                "strategy_name": signal.strategy_name,
                "session_tag": self._normalize_name(snapshot.session_tag),
                "session_allowed": session_allowed,
                "strategy_enabled": strategy_enabled,
                "enabled_strategies": list(
                    self._normalize_collection(self.config.enabled_strategies)
                ),
                "disabled_strategies": list(
                    self._normalize_collection(self.config.disabled_strategies)
                ),
                "allowed_sessions": list(
                    self._normalize_collection(self.config.allowed_sessions)
                ),
                "blocked_sessions": list(
                    self._normalize_collection(self.config.blocked_sessions)
                ),
                "blocked_reasons": list(blocked_reasons),
            },
        )

    def _strategy_enabled(self, strategy_name: str) -> bool:
        normalized_name = self._normalize_name(strategy_name)
        enabled = self._normalize_collection(self.config.enabled_strategies)
        disabled = self._normalize_collection(self.config.disabled_strategies)
        if enabled and normalized_name not in enabled:
            return False
        return normalized_name not in disabled

    def _session_allowed(self, session_tag: str) -> bool:
        normalized_session = self._normalize_name(session_tag)
        allowed = self._normalize_collection(self.config.allowed_sessions)
        blocked = self._normalize_collection(self.config.blocked_sessions)
        if allowed and normalized_session not in allowed:
            return False
        return normalized_session not in blocked

    @staticmethod
    def _normalize_collection(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        return tuple(
            item
            for item in (StrategyRouter._normalize_name(value) for value in values)
            if item
        )

    @staticmethod
    def _normalize_name(value: object) -> str:
        return str(value or "").strip().lower()
