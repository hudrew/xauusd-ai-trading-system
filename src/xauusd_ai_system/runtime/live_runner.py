from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import time as time_module
from typing import Any

from ..account_state.service import AccountStateService
from ..backtest.backtrader_adapter import BacktraderAdapter
from ..config.schema import SystemConfig
from ..core.models import AccountState, TradingDecision
from ..market_data.base import Quote
from ..market_data.service import MarketDataService
from .service import TradingRuntimeService


LOGGER = logging.getLogger(__name__)

BASE_RECORD_COLUMNS = {
    "timestamp",
    "symbol",
    "bid",
    "ask",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "tick_volume",
    "spread",
    "real_volume",
    "session_tag",
    "news_flag",
    "minutes_to_event",
    "minutes_from_event",
}


@dataclass
class EventContext:
    news_flag: bool = False
    minutes_to_event: int | None = None
    minutes_from_event: int | None = None


class LiveTradingRunner:
    def __init__(
        self,
        config: SystemConfig,
        runtime_service: TradingRuntimeService,
        market_data_service: MarketDataService | None = None,
        account_state_service: AccountStateService | None = None,
        calculator: Any | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config
        self.runtime_service = runtime_service
        self.market_data_service = market_data_service or MarketDataService(config.market_data)
        self.account_state_service = account_state_service or AccountStateService(config)
        self.sleep_fn = sleep_fn or time_module.sleep
        if calculator is None:
            try:
                from ..features.calculator import FeatureCalculator
            except ImportError as exc:
                raise RuntimeError(
                    "Live trading runner requires pandas/numpy. Install runtime "
                    "dependencies first."
                ) from exc
            self.calculator = FeatureCalculator()
        else:
            self.calculator = calculator

    def run_once(
        self,
        *,
        account_state: AccountState | None = None,
        event_context: EventContext | None = None,
    ) -> TradingDecision:
        if self.market_data_service.adapter is None:
            raise RuntimeError("Market data platform is not configured.")

        latest_quote = self.market_data_service.get_latest_quote()
        recent_bars = self.market_data_service.get_recent_bars(self._history_bars())
        snapshot = self.build_snapshot(
            recent_bars,
            latest_quote,
            event_context=event_context,
        )
        effective_account_state = account_state or self.account_state_service.get_account_state(
            reference_time=latest_quote.timestamp
        )
        return self.runtime_service.process_snapshot(snapshot, effective_account_state)

    def run_loop(
        self,
        *,
        iterations: int | None = None,
        account_state: AccountState | None = None,
        event_context_provider: Callable[[], EventContext] | None = None,
    ) -> None:
        cycle_count = 0
        while iterations is None or cycle_count < iterations:
            try:
                decision = self.run_once(
                    account_state=account_state,
                    event_context=(
                        event_context_provider() if event_context_provider else None
                    ),
                )
                LOGGER.info(
                    "live_cycle_completed",
                    extra={
                        "extra_payload": {
                            "symbol": self._configured_symbol(),
                            "state_label": decision.state.state_label.value,
                            "risk_allowed": decision.risk.allowed,
                            "signal_strategy": (
                                decision.signal.strategy_name
                                if decision.signal is not None
                                else None
                            ),
                        }
                    },
                )
            except KeyboardInterrupt:
                LOGGER.info("live_cycle_interrupted")
                raise
            except Exception:
                LOGGER.exception(
                    "live_cycle_failed",
                    extra={
                        "extra_payload": {
                            "symbol": self._configured_symbol(),
                            "platform": self.config.market_data.platform,
                        }
                    },
                )

            cycle_count += 1
            if iterations is not None and cycle_count >= iterations:
                break
            self.sleep_fn(float(self.config.runtime.poll_interval_seconds))

    def shutdown(self) -> None:
        self.account_state_service.close()
        self.runtime_service.shutdown()

    def build_snapshot(
        self,
        bars: list[dict[str, Any]],
        latest_quote: Quote,
        *,
        event_context: EventContext | None = None,
    ):
        if not bars:
            raise RuntimeError("Market data service returned no bars for snapshot building.")

        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Live trading runner requires pandas/numpy. Install runtime dependencies first."
            ) from exc

        context = event_context or EventContext()
        frame = pd.DataFrame.from_records(bars).copy()
        required = {"timestamp", "open", "high", "low", "close"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"Live market data bars are missing columns: {missing}")

        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=False)
        frame = frame.sort_values("timestamp").reset_index(drop=True)

        if "volume" not in frame.columns:
            frame["volume"] = frame.get("tick_volume", 0.0)
        frame["volume"] = frame["volume"].fillna(frame.get("tick_volume", 0.0)).astype(float)

        if "symbol" not in frame.columns:
            frame["symbol"] = latest_quote.symbol
        else:
            frame["symbol"] = frame["symbol"].fillna(latest_quote.symbol)

        if "spread" not in frame.columns:
            frame["spread"] = 0.0
        frame["spread"] = frame["spread"].fillna(0.0).astype(float)

        if "bid" not in frame.columns and "ask" not in frame.columns:
            frame["bid"] = frame["close"].astype(float) - frame["spread"] / 2.0
            frame["ask"] = frame["close"].astype(float) + frame["spread"] / 2.0
        else:
            if "bid" not in frame.columns:
                frame["ask"] = frame["ask"].astype(float)
                frame["bid"] = frame["ask"] - frame["spread"]
            if "ask" not in frame.columns:
                frame["bid"] = frame["bid"].astype(float)
                frame["ask"] = frame["bid"] + frame["spread"]
            frame["bid"] = frame["bid"].fillna(
                frame["close"].astype(float) - frame["spread"] / 2.0
            ).astype(float)
            frame["ask"] = frame["ask"].fillna(
                frame["close"].astype(float) + frame["spread"] / 2.0
            ).astype(float)

        if "session_tag" not in frame.columns:
            frame["session_tag"] = ""
        frame["session_tag"] = frame["session_tag"].fillna("")
        frame["session_tag"] = frame["session_tag"].where(
            frame["session_tag"].astype(bool),
            self._derive_sessions(frame["timestamp"]),
        )

        frame["news_flag"] = context.news_flag
        frame["minutes_to_event"] = context.minutes_to_event
        frame["minutes_from_event"] = context.minutes_from_event

        last_index = frame.index[-1]
        frame.at[last_index, "symbol"] = latest_quote.symbol
        frame.at[last_index, "bid"] = latest_quote.bid
        frame.at[last_index, "ask"] = latest_quote.ask

        feature_frame = self.calculator.calculate(frame)
        record = feature_frame.iloc[-1].to_dict()
        record["timestamp"] = latest_quote.timestamp

        feature_names = set(feature_frame.columns) - BASE_RECORD_COLUMNS
        features = {name: record.get(name) for name in sorted(feature_names)}
        return BacktraderAdapter.build_snapshot(
            record,
            symbol=latest_quote.symbol,
            session_tag=str(record.get("session_tag", "unknown")),
            news_flag=bool(record.get("news_flag", False)),
            minutes_to_event=record.get("minutes_to_event"),
            minutes_from_event=record.get("minutes_from_event"),
            features=features,
        )

    def _history_bars(self) -> int:
        if self.config.market_data.platform.lower() == "mt5":
            return self.config.market_data.mt5.history_bars
        return 500

    def _configured_symbol(self) -> str:
        platform = self.config.market_data.platform.lower()
        if platform == "mt5":
            return self.config.market_data.mt5.symbol or self.config.market_data.symbol
        if platform == "ctrader":
            return self.config.market_data.ctrader.symbol_name or self.config.market_data.symbol
        return self.config.market_data.symbol

    @staticmethod
    def _derive_sessions(timestamp_series: Any) -> Any:
        hours = timestamp_series.dt.hour
        conditions = [
            (hours >= 0) & (hours < 7),
            (hours >= 7) & (hours < 12),
            (hours >= 12) & (hours < 17),
            (hours >= 17) & (hours < 24),
        ]
        labels = ["asia", "eu", "overlap", "us"]
        session = timestamp_series.astype("object").copy()
        for condition, label in zip(conditions, labels):
            session.loc[condition] = label
        return session.fillna("unknown")
