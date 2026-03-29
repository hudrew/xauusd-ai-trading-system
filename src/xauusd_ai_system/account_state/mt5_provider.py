from __future__ import annotations

from datetime import datetime
from typing import Any

from ..config.schema import SystemConfig
from .base import AccountStateProvider, BrokerAccountSnapshot


class MT5AccountStateProvider(AccountStateProvider):
    platform = "mt5"

    def __init__(self, config: SystemConfig) -> None:
        self.config = config

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        mt5 = self._initialize()
        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 account_info failed: {error}")

        terminal_info = mt5.terminal_info()
        symbol = self._symbol()
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            error = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 positions_get failed for {symbol}: {error}")

        trade_allowed = bool(getattr(account_info, "trade_allowed", True))
        if terminal_info is not None and bool(
            getattr(terminal_info, "tradeapi_disabled", False)
        ):
            trade_allowed = False

        snapshot = BrokerAccountSnapshot(
            timestamp=datetime.now(),
            equity=float(getattr(account_info, "equity", 0.0)),
            balance=float(getattr(account_info, "balance", 0.0)),
            open_positions=len(positions),
            trade_allowed=trade_allowed,
            metadata={
                "symbol": symbol,
                "profit": float(getattr(account_info, "profit", 0.0)),
                "margin_free": float(getattr(account_info, "margin_free", 0.0)),
                "margin_level": float(getattr(account_info, "margin_level", 0.0)),
            },
        )
        mt5.shutdown()
        return snapshot

    def _initialize(self) -> Any:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 is not installed. Install execution dependencies first."
            ) from exc

        initialized = mt5.initialize(
            path=self._first_non_empty(
                self.config.execution.mt5.path,
                self.config.market_data.mt5.path,
            ),
            login=self._first_non_empty(
                self.config.execution.mt5.login,
                self.config.market_data.mt5.login,
            ),
            password=self._first_non_empty(
                self.config.execution.mt5.password,
                self.config.market_data.mt5.password,
            ),
            server=self._first_non_empty(
                self.config.execution.mt5.server,
                self.config.market_data.mt5.server,
            ),
        )
        if not initialized:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        return mt5

    def _symbol(self) -> str:
        return self._first_non_empty(
            self.config.execution.mt5.symbol,
            self.config.market_data.mt5.symbol,
            self.config.execution.symbol,
            self.config.market_data.symbol,
            "XAUUSD",
        )

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None
