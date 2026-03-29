from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

from ..config.schema import SystemConfig
from ..market_data.mt5_adapter import MT5MarketDataAdapter


@dataclass
class MT5HistoryExportResult:
    output_path: str
    symbol: str
    timeframe: str
    bars_requested: int
    bars_exported: int
    point: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bars_requested": self.bars_requested,
            "bars_exported": self.bars_exported,
            "point": self.point,
        }


class MT5HistoryCsvExporter:
    def __init__(self, config: SystemConfig, mt5_module: Any | None = None) -> None:
        self.config = config
        self._mt5_module = mt5_module

    def export_csv(
        self,
        output_path: str | Path,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        bars: int | None = None,
    ) -> MT5HistoryExportResult:
        mt5 = self._mt5()
        resolved_symbol = (
            symbol
            or self.config.market_data.mt5.symbol
            or self.config.market_data.symbol
            or self.config.execution.mt5.symbol
            or self.config.execution.symbol
            or "XAUUSD"
        )
        resolved_timeframe = (
            timeframe
            or self.config.market_data.mt5.timeframe
            or "M1"
        ).upper()
        requested_bars = int(bars or self.config.market_data.mt5.history_bars)

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

        try:
            if not mt5.symbol_select(resolved_symbol, True):
                raise RuntimeError(
                    f"MT5 symbol_select failed for {resolved_symbol}: {mt5.last_error()}"
                )

            symbol_info = mt5.symbol_info(resolved_symbol)
            point = float(getattr(symbol_info, "point", 0.0) or 0.0)

            timeframe_name = MT5MarketDataAdapter.TIMEFRAME_MAP.get(
                resolved_timeframe,
                f"TIMEFRAME_{resolved_timeframe}",
            )
            timeframe_value = getattr(mt5, timeframe_name, None)
            if timeframe_value is None:
                raise ValueError(f"Unsupported MT5 timeframe constant: {resolved_timeframe}")

            bars_payload = mt5.copy_rates_from_pos(
                resolved_symbol,
                timeframe_value,
                0,
                requested_bars,
            )
            if bars_payload is None:
                raise RuntimeError(
                    f"MT5 copy_rates_from_pos failed for {resolved_symbol}: {mt5.last_error()}"
                )
            if len(bars_payload) == 0:
                raise RuntimeError(
                    f"MT5 copy_rates_from_pos returned no bars for {resolved_symbol}."
                )

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "symbol",
                        "open",
                        "high",
                        "low",
                        "close",
                        "bid",
                        "ask",
                        "spread",
                        "volume",
                        "tick_volume",
                        "real_volume",
                    ],
                )
                writer.writeheader()
                for bar in bars_payload:
                    normalized = MT5MarketDataAdapter.normalize_bar(
                        bar,
                        symbol=resolved_symbol,
                        point=point,
                    )
                    writer.writerow(
                        {
                            "timestamp": normalized["timestamp"].astimezone(
                                timezone.utc
                            ).isoformat(),
                            "symbol": normalized["symbol"],
                            "open": normalized["open"],
                            "high": normalized["high"],
                            "low": normalized["low"],
                            "close": normalized["close"],
                            "bid": normalized["bid"],
                            "ask": normalized["ask"],
                            "spread": normalized["spread"],
                            "volume": normalized["volume"],
                            "tick_volume": normalized["tick_volume"],
                            "real_volume": normalized["real_volume"],
                        }
                    )

            return MT5HistoryExportResult(
                output_path=str(output),
                symbol=resolved_symbol,
                timeframe=resolved_timeframe,
                bars_requested=requested_bars,
                bars_exported=len(bars_payload),
                point=point,
            )
        finally:
            try:
                mt5.shutdown()
            except Exception:
                pass

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

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None
