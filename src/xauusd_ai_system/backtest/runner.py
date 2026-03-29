from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.schema import SystemConfig
from ..core.models import AccountState
from ..core.pipeline import TradingSystem
from ..data.csv_loader import CSVMarketDataLoader
from ..features.calculator import FeatureCalculator
from .backtrader_adapter import BacktraderAdapter
from .reporting import DecisionAuditCollector, DecisionAuditSummary, NON_FEATURE_COLUMNS


@dataclass
class ReplaySummary(DecisionAuditSummary):
    last_decision: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        payload = super().as_dict()
        payload["last_decision"] = self.last_decision
        return payload


class HistoricalReplayRunner:
    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self.loader = CSVMarketDataLoader()
        self.calculator = FeatureCalculator()
        self.system = TradingSystem(config)
        self.adapter = BacktraderAdapter()

    def run_csv(
        self,
        path: str | Path,
        *,
        symbol: str = "XAUUSD",
        equity: float = 10_000.0,
    ) -> ReplaySummary:
        market_data = self.loader.load(path, symbol=symbol)
        feature_frame = self.calculator.calculate(market_data)
        feature_names = set(feature_frame.columns) - NON_FEATURE_COLUMNS

        account_state = AccountState(equity=equity)
        collector = DecisionAuditCollector()
        last_decision: dict[str, Any] | None = None

        for record in feature_frame.to_dict(orient="records"):
            features = {name: record.get(name) for name in feature_names}
            decision = self.adapter.evaluate_bar(
                self.system,
                record,
                features=features,
                account_state=account_state,
            )
            last_decision = decision.as_dict()
            collector.record(record, decision)

        audit_summary = collector.build_summary()
        return ReplaySummary(last_decision=last_decision, **audit_summary.as_dict())
