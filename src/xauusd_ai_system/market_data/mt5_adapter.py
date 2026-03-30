from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config.schema import MarketDataConfig
from ..mt5_session import initialize_mt5_session
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

        symbol_info = mt5.symbol_info(symbol)
        point = float(getattr(symbol_info, "point", 0.0) or 0.0)

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
            result.append(self.normalize_bar(bar, symbol=symbol, point=point))
        mt5.shutdown()
        return result

    @staticmethod
    def normalize_bar(
        bar: Any,
        *,
        symbol: str,
        point: float,
    ) -> dict[str, Any]:
        close = float(MT5MarketDataAdapter._bar_value(bar, "close", 0.0))
        spread_points = float(MT5MarketDataAdapter._bar_value(bar, "spread", 0.0))
        spread = (
            spread_points * point
            if point > 0.0
            else spread_points
        )
        bid = close - spread / 2.0
        ask = close + spread / 2.0
        return {
            "timestamp": datetime.fromtimestamp(
                int(MT5MarketDataAdapter._bar_value(bar, "time", 0)),
                tz=timezone.utc,
            ),
            "open": float(MT5MarketDataAdapter._bar_value(bar, "open", close)),
            "high": float(MT5MarketDataAdapter._bar_value(bar, "high", close)),
            "low": float(MT5MarketDataAdapter._bar_value(bar, "low", close)),
            "close": close,
            "bid": bid,
            "ask": ask,
            "volume": float(MT5MarketDataAdapter._bar_value(bar, "tick_volume", 0.0)),
            "tick_volume": int(MT5MarketDataAdapter._bar_value(bar, "tick_volume", 0)),
            "spread": spread,
            "real_volume": int(MT5MarketDataAdapter._bar_value(bar, "real_volume", 0)),
            "symbol": symbol,
        }

    @staticmethod
    def _bar_value(bar: Any, field: str, default: Any) -> Any:
        if isinstance(bar, dict):
            return bar.get(field, default)

        try:
            return bar[field]
        except (KeyError, IndexError, TypeError, ValueError):
            return getattr(bar, field, default)

    def _initialize(self) -> Any:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 is not installed. Install execution dependencies first."
            ) from exc

        initialize_mt5_session(
            mt5,
            path=self.config.mt5.path,
            login=self.config.mt5.login,
            password=self.config.mt5.password,
            server=self.config.mt5.server,
        )
        return mt5
