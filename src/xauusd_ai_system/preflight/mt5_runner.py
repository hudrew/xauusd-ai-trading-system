from __future__ import annotations

from typing import Any

from ..config.schema import SystemConfig
from .base import PreflightCheck, PreflightReport


class MT5PreflightRunner:
    def __init__(self, config: SystemConfig, mt5_module: Any | None = None) -> None:
        self.config = config
        self._mt5_module = mt5_module

    def run(self) -> PreflightReport:
        checks: list[PreflightCheck] = []
        symbol = self._symbol()
        history_bars = self.config.market_data.mt5.history_bars
        timeframe_name = self.config.market_data.mt5.timeframe.upper()

        try:
            mt5 = self._mt5()
        except Exception as exc:
            checks.append(
                PreflightCheck(
                    name="mt5_import",
                    passed=False,
                    detail=(
                        f"{exc}. If this host cannot install MetaTrader5, run the "
                        "MT5 live adapter on a compatible execution host and keep "
                        "this repo as the strategy/orchestration node."
                    ),
                )
            )
            return PreflightReport(platform="mt5", ready=False, checks=checks)

        try:
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
            checks.append(
                PreflightCheck(
                    name="mt5_initialize",
                    passed=bool(initialized),
                    detail=(
                        "MT5 initialize succeeded."
                        if initialized
                        else f"MT5 initialize failed: {mt5.last_error()}"
                    ),
                )
            )
            if not initialized:
                return PreflightReport(platform="mt5", ready=False, checks=checks)

            account_info = mt5.account_info()
            checks.append(
                PreflightCheck(
                    name="account_info",
                    passed=account_info is not None,
                    detail=(
                        "Account info available."
                        if account_info is not None
                        else f"MT5 account_info failed: {mt5.last_error()}"
                    ),
                    metadata=(
                        {
                            "login": getattr(account_info, "login", None),
                            "equity": getattr(account_info, "equity", None),
                            "trade_allowed": getattr(account_info, "trade_allowed", None),
                        }
                        if account_info is not None
                        else {}
                    ),
                )
            )

            terminal_info = mt5.terminal_info()
            terminal_ok = terminal_info is not None
            tradeapi_disabled = bool(
                getattr(terminal_info, "tradeapi_disabled", False)
            ) if terminal_info is not None else None
            checks.append(
                PreflightCheck(
                    name="terminal_info",
                    passed=terminal_ok,
                    detail=(
                        "Terminal info available."
                        if terminal_ok
                        else f"MT5 terminal_info failed: {mt5.last_error()}"
                    ),
                    metadata={
                        "tradeapi_disabled": tradeapi_disabled,
                    }
                    if terminal_ok
                    else {},
                )
            )

            symbol_selected = mt5.symbol_select(symbol, True)
            checks.append(
                PreflightCheck(
                    name="symbol_select",
                    passed=bool(symbol_selected),
                    detail=(
                        f"Symbol {symbol} selected."
                        if symbol_selected
                        else f"MT5 symbol_select failed for {symbol}: {mt5.last_error()}"
                    ),
                    metadata={"symbol": symbol},
                )
            )

            symbol_info = mt5.symbol_info(symbol) if symbol_selected else None
            checks.append(
                PreflightCheck(
                    name="symbol_info",
                    passed=symbol_info is not None,
                    detail=(
                        f"Symbol info available for {symbol}."
                        if symbol_info is not None
                        else f"MT5 symbol_info failed for {symbol}: {mt5.last_error()}"
                    ),
                    metadata=(
                        {
                            "visible": getattr(symbol_info, "visible", None),
                            "trade_mode": getattr(symbol_info, "trade_mode", None),
                            "digits": getattr(symbol_info, "digits", None),
                            "trade_contract_size": getattr(
                                symbol_info, "trade_contract_size", None
                            ),
                            "volume_min": getattr(symbol_info, "volume_min", None),
                            "volume_step": getattr(symbol_info, "volume_step", None),
                            "volume_max": getattr(symbol_info, "volume_max", None),
                            "trade_stops_level": getattr(
                                symbol_info, "trade_stops_level", None
                            ),
                        }
                        if symbol_info is not None
                        else {}
                    ),
                )
            )

            observed_contract_size = (
                float(getattr(symbol_info, "trade_contract_size", 0.0))
                if symbol_info is not None
                and getattr(symbol_info, "trade_contract_size", None) is not None
                else None
            )
            configured_contract_size = float(self.config.risk.contract_size)
            contract_size_ok = (
                observed_contract_size is not None
                and abs(observed_contract_size - configured_contract_size) <= 1e-9
            )
            checks.append(
                PreflightCheck(
                    name="contract_size_alignment",
                    passed=contract_size_ok,
                    detail=(
                        f"Configured contract_size {configured_contract_size} matches broker "
                        f"trade_contract_size {observed_contract_size}."
                        if contract_size_ok
                        else (
                            "Configured risk.contract_size does not match broker "
                            f"trade_contract_size. configured={configured_contract_size}, "
                            f"broker={observed_contract_size}"
                        )
                    ),
                    metadata={
                        "configured_contract_size": configured_contract_size,
                        "broker_trade_contract_size": observed_contract_size,
                    },
                )
            )

            tick = mt5.symbol_info_tick(symbol) if symbol_selected else None
            tick_bid = getattr(tick, "bid", None) if tick is not None else None
            tick_ask = getattr(tick, "ask", None) if tick is not None else None
            zero_quote = (
                tick is not None
                and tick_bid in (0, 0.0)
                and tick_ask in (0, 0.0)
            )
            checks.append(
                PreflightCheck(
                    name="latest_tick",
                    passed=tick is not None,
                    detail=(
                        (
                            f"Latest tick available for {symbol}, but bid/ask are both 0. "
                            "This usually means the symbol is currently closed or no live quote is streaming."
                        )
                        if zero_quote
                        else (
                            f"Latest tick available for {symbol}."
                            if tick is not None
                            else f"MT5 symbol_info_tick failed for {symbol}: {mt5.last_error()}"
                        )
                    ),
                    metadata=(
                        {
                            "bid": tick_bid,
                            "ask": tick_ask,
                            "zero_quote": zero_quote,
                        }
                        if tick is not None
                        else {}
                    ),
                )
            )

            timeframe = getattr(mt5, self._timeframe_name(), None)
            timeframe_ok = timeframe is not None
            checks.append(
                PreflightCheck(
                    name="timeframe_mapping",
                    passed=timeframe_ok,
                    detail=(
                        f"Resolved timeframe {timeframe_name}."
                        if timeframe_ok
                        else f"Unsupported MT5 timeframe constant: {timeframe_name}"
                    ),
                )
            )

            bars = (
                mt5.copy_rates_from_pos(symbol, timeframe, 0, history_bars)
                if symbol_selected and timeframe_ok
                else None
            )
            bars_count = len(bars) if bars is not None else 0
            checks.append(
                PreflightCheck(
                    name="recent_bars",
                    passed=bars is not None and bars_count > 0,
                    detail=(
                        f"Loaded {bars_count} recent bars for {symbol}."
                        if bars is not None and bars_count > 0
                        else f"MT5 copy_rates_from_pos failed for {symbol}: {mt5.last_error()}"
                    ),
                    metadata={
                        "requested_bars": history_bars,
                        "returned_bars": bars_count,
                    },
                )
            )

            if self.config.runtime.dry_run:
                checks.append(
                    PreflightCheck(
                        name="trade_permission",
                        passed=True,
                        detail="Dry run enabled, trade permission check is informational.",
                        severity="info",
                        metadata={
                            "dry_run": True,
                            "account_trade_allowed": (
                                getattr(account_info, "trade_allowed", None)
                                if account_info is not None
                                else None
                            ),
                            "terminal_tradeapi_disabled": tradeapi_disabled,
                        },
                    )
                )
            else:
                trade_allowed = bool(
                    account_info is not None
                    and getattr(account_info, "trade_allowed", False)
                ) and not bool(tradeapi_disabled)
                checks.append(
                    PreflightCheck(
                        name="trade_permission",
                        passed=trade_allowed,
                        detail=(
                            "MT5 account and terminal allow trading."
                            if trade_allowed
                            else "Trading is disabled either on account_info or terminal_info."
                        ),
                        metadata={
                            "dry_run": False,
                            "account_trade_allowed": (
                                getattr(account_info, "trade_allowed", None)
                                if account_info is not None
                                else None
                            ),
                            "terminal_tradeapi_disabled": tradeapi_disabled,
                        },
                    )
                )
        finally:
            try:
                mt5.shutdown()
            except Exception:
                pass

        ready = all(item.passed or item.severity == "info" for item in checks)
        return PreflightReport(platform="mt5", ready=ready, checks=checks)

    def _mt5(self) -> Any:
        if self._mt5_module is not None:
            return self._mt5_module
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 is not installed. Install execution dependencies first."
            ) from exc
        return mt5

    def _symbol(self) -> str:
        return self._first_non_empty(
            self.config.execution.mt5.symbol,
            self.config.market_data.mt5.symbol,
            self.config.execution.symbol,
            self.config.market_data.symbol,
            "XAUUSD",
        )

    def _timeframe_name(self) -> str:
        timeframe = self.config.market_data.mt5.timeframe.upper()
        return {
            "M1": "TIMEFRAME_M1",
            "M5": "TIMEFRAME_M5",
            "M15": "TIMEFRAME_M15",
            "H1": "TIMEFRAME_H1",
        }.get(timeframe, f"TIMEFRAME_{timeframe}")

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None
