from __future__ import annotations

from datetime import datetime
from typing import Any

from ..config.schema import MarketDataConfig
from .base import MarketDataAdapter, Quote


class MT5MarketDataAdapter(MarketDataAdapter):
    platform = "mt5"

    TIMEFRAME_MAP = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "H1": "TIMEFRAME_H1",
    }

    def __init__(self, config: MarketDataConfig) -> None:
        self.config = config

    def get_latest_quote(self) -> Quote:
        mt5 = self._initialize()
        symbol = self.config.mt5.symbol or self.config.symbol
        if not mt5.symbol_select(symbol, True):
            error = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 symbol_select failed for {symbol}: {error}")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            error = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 symbol_info_tick failed for {symbol}: {error}")

        point_in_time = datetime.fromtimestamp(tick.time)
        quote = Quote(
            timestamp=point_in_time,
            symbol=symbol,
            bid=float(tick.bid),
            ask=float(tick.ask),
            metadata={"last": float(getattr(tick, "last", 0.0))},
        )
        mt5.shutdown()
        return quote

    def get_recent_bars(self, count: int | None = None) -> list[dict[str, Any]]:
        mt5 = self._initialize()
        symbol = self.config.mt5.symbol or self.config.symbol
        if not mt5.symbol_select(symbol, True):
            error = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 symbol_select failed for {symbol}: {error}")

        timeframe_name = self.TIMEFRAME_MAP.get(
            self.config.mt5.timeframe.upper(),
            "TIMEFRAME_M1",
        )
        timeframe = getattr(mt5, timeframe_name)
        bars = mt5.copy_rates_from_pos(
            symbol,
            timeframe,
            0,
            count or self.config.mt5.history_bars,
        )
        if bars is None:
            error = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 copy_rates_from_pos failed for {symbol}: {error}")

        result = []
        for bar in bars:
            result.append(
                {
                    "timestamp": datetime.fromtimestamp(bar["time"]),
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "tick_volume": int(bar["tick_volume"]),
                    "spread": int(bar["spread"]),
                    "real_volume": int(bar["real_volume"]),
                    "symbol": symbol,
                }
            )
        mt5.shutdown()
        return result

    def _initialize(self) -> Any:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 is not installed. Install execution dependencies first."
            ) from exc

        initialized = mt5.initialize(
            path=self.config.mt5.path,
            login=self.config.mt5.login,
            password=self.config.mt5.password,
            server=self.config.mt5.server,
        )
        if not initialized:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        return mt5

