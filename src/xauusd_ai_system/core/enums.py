from __future__ import annotations

from enum import Enum


class MarketState(str, Enum):
    TREND_BREAKOUT = "trend_breakout"
    PULLBACK_CONTINUATION = "pullback_continuation"
    RANGE_MEAN_REVERSION = "range_mean_reversion"
    NO_TRADE = "no_trade"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class EntryType(str, Enum):
    MARKET = "market"
    RETEST = "retest"
    LIMIT = "limit"


class WarningLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
