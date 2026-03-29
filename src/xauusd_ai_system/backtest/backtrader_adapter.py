from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..core.models import AccountState, MarketSnapshot, TradingDecision
from ..core.pipeline import TradingSystem

class BacktraderAdapter:
    """
    Lightweight bridge between backtest rows and the project decision pipeline.

    This class intentionally avoids a hard runtime dependency on Backtrader so
    the repository remains usable before the research stack is installed.
    """

    @staticmethod
    def dependency_hint() -> str:
        return 'Install with: pip install -e ".[research]"'

    @staticmethod
    def integration_note() -> str:
        return (
            "Wrap BacktraderAdapter.evaluate_bar inside a bt.Strategy.next method, "
            "feed synchronized M1/M5 features, and route fills back into AccountState."
        )

    @staticmethod
    def build_snapshot(
        row: Mapping[str, Any],
        *,
        symbol: str = "XAUUSD",
        session_tag: str = "unknown",
        news_flag: bool = False,
        minutes_to_event: int | None = None,
        minutes_from_event: int | None = None,
        features: dict[str, Any] | None = None,
    ) -> MarketSnapshot:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            raise ValueError("BacktraderAdapter.build_snapshot requires a datetime timestamp.")

        close = float(row["close"])
        bid = float(row.get("bid", close))
        ask = float(row.get("ask", close))

        return MarketSnapshot(
            timestamp=timestamp,
            symbol=str(row.get("symbol", symbol)),
            bid=bid,
            ask=ask,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=close,
            session_tag=str(row.get("session_tag", session_tag)),
            news_flag=bool(row.get("news_flag", news_flag)),
            minutes_to_event=row.get("minutes_to_event", minutes_to_event),
            minutes_from_event=row.get("minutes_from_event", minutes_from_event),
            features=features or {},
        )

    @staticmethod
    def build_account_state(
        *,
        equity: float,
        daily_pnl_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        consecutive_losses: int = 0,
        open_positions: int = 0,
        protective_mode: bool = False,
    ) -> AccountState:
        return AccountState(
            equity=equity,
            daily_pnl_pct=daily_pnl_pct,
            drawdown_pct=drawdown_pct,
            consecutive_losses=consecutive_losses,
            open_positions=open_positions,
            protective_mode=protective_mode,
        )

    def evaluate_bar(
        self,
        system: TradingSystem,
        row: Mapping[str, Any],
        *,
        features: dict[str, Any],
        account_state: AccountState,
    ) -> TradingDecision:
        snapshot = self.build_snapshot(row, features=features)
        return system.evaluate(snapshot, account_state)

    @staticmethod
    def decision_to_order_plan(decision: TradingDecision) -> dict[str, Any] | None:
        if decision.signal is None or not decision.risk.allowed:
            return None

        return {
            "strategy_name": decision.signal.strategy_name,
            "side": decision.signal.side.value,
            "entry_type": decision.signal.entry_type.value,
            "entry_price": decision.signal.entry_price,
            "stop_loss": decision.signal.stop_loss,
            "take_profit": decision.signal.take_profit,
            "position_size": decision.risk.position_size,
            "volatility_level": (
                decision.volatility.primary_alert.warning_level.value
                if decision.volatility is not None
                else None
            ),
        }
