from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config.schema import SystemConfig
from ..market_data.mt5_adapter import MT5MarketDataAdapter
from ..mt5_session import initialize_mt5_session


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


@dataclass
class MT5HistoryCapacityProbeResult:
    symbol: str
    timeframe: str
    batch_size: int
    max_bars: int
    bars_available: int
    batches_loaded: int
    probe_complete: bool
    point: float
    oldest_timestamp: str | None
    newest_timestamp: str | None
    stopped_reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "batch_size": self.batch_size,
            "max_bars": self.max_bars,
            "bars_available": self.bars_available,
            "batches_loaded": self.batches_loaded,
            "probe_complete": self.probe_complete,
            "point": self.point,
            "oldest_timestamp": self.oldest_timestamp,
            "newest_timestamp": self.newest_timestamp,
            "stopped_reason": self.stopped_reason,
        }


class MT5HistoryCsvExporter:
    # MT5 terminals on some hosts reject large single copy_rates_from_pos calls,
    # so we fetch recent history in smaller slices and stitch it back together.
    MAX_BARS_PER_REQUEST = 50000

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
        if requested_bars <= 0:
            raise ValueError("bars must be positive for MT5 history export.")

        initialize_mt5_session(
            mt5,
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

            bars_payload = self._load_bars_in_batches(
                mt5=mt5,
                symbol=resolved_symbol,
                timeframe_value=timeframe_value,
                requested_bars=requested_bars,
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

    def probe_capacity(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        batch_size: int | None = None,
        max_bars: int | None = None,
    ) -> MT5HistoryCapacityProbeResult:
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
        resolved_batch_size = int(batch_size or self.MAX_BARS_PER_REQUEST)
        resolved_max_bars = int(max_bars or (resolved_batch_size * 10))
        if resolved_batch_size <= 0:
            raise ValueError("batch_size must be positive for MT5 history probe.")
        if resolved_max_bars <= 0:
            raise ValueError("max_bars must be positive for MT5 history probe.")

        initialize_mt5_session(
            mt5,
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

            bars_available = 0
            batches_loaded = 0
            start_pos = 0
            newest_timestamp: str | None = None
            oldest_timestamp: str | None = None
            stopped_reason: str | None = None
            probe_complete = False

            while bars_available < resolved_max_bars:
                request_count = min(
                    resolved_batch_size,
                    resolved_max_bars - bars_available,
                )
                batch = mt5.copy_rates_from_pos(
                    resolved_symbol,
                    timeframe_value,
                    start_pos,
                    request_count,
                )
                if batch is None:
                    if bars_available == 0:
                        raise RuntimeError(
                            f"MT5 copy_rates_from_pos failed for {resolved_symbol}: {mt5.last_error()}"
                        )
                    stopped_reason = str(mt5.last_error())
                    probe_complete = True
                    break

                batch_rows = list(batch)
                if not batch_rows:
                    stopped_reason = "copy_rates_from_pos returned no additional bars"
                    probe_complete = True
                    break

                batches_loaded += 1
                bars_available += len(batch_rows)
                start_pos += len(batch_rows)

                if newest_timestamp is None:
                    newest_timestamp = self._bar_timestamp_iso(
                        batch_rows[-1],
                        symbol=resolved_symbol,
                        point=point,
                    )
                oldest_timestamp = self._bar_timestamp_iso(
                    batch_rows[0],
                    symbol=resolved_symbol,
                    point=point,
                )

                if len(batch_rows) < request_count:
                    stopped_reason = (
                        f"requested batch_size={request_count}, returned={len(batch_rows)}"
                    )
                    probe_complete = True
                    break

            if bars_available >= resolved_max_bars and not probe_complete:
                stopped_reason = f"probe_limit_reached max_bars={resolved_max_bars}"

            return MT5HistoryCapacityProbeResult(
                symbol=resolved_symbol,
                timeframe=resolved_timeframe,
                batch_size=resolved_batch_size,
                max_bars=resolved_max_bars,
                bars_available=bars_available,
                batches_loaded=batches_loaded,
                probe_complete=probe_complete,
                point=point,
                oldest_timestamp=oldest_timestamp,
                newest_timestamp=newest_timestamp,
                stopped_reason=stopped_reason,
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

    def _load_bars_in_batches(
        self,
        *,
        mt5: Any,
        symbol: str,
        timeframe_value: Any,
        requested_bars: int,
    ) -> list[Any]:
        chunks: list[list[Any]] = []
        collected_bars = 0
        start_pos = 0

        while collected_bars < requested_bars:
            batch_size = min(
                requested_bars - collected_bars,
                int(self.MAX_BARS_PER_REQUEST),
            )
            batch = mt5.copy_rates_from_pos(
                symbol,
                timeframe_value,
                start_pos,
                batch_size,
            )
            if batch is None:
                raise RuntimeError(
                    self._format_partial_history_error(
                        symbol=symbol,
                        requested_bars=requested_bars,
                        collected_bars=collected_bars,
                        error=mt5.last_error(),
                    )
                )

            batch_rows = list(batch)
            if not batch_rows:
                raise RuntimeError(
                    self._format_partial_history_error(
                        symbol=symbol,
                        requested_bars=requested_bars,
                        collected_bars=collected_bars,
                        error="copy_rates_from_pos returned no additional bars",
                    )
                )

            chunks.append(batch_rows)
            collected_bars += len(batch_rows)
            start_pos += len(batch_rows)

            if len(batch_rows) < batch_size and collected_bars < requested_bars:
                raise RuntimeError(
                    self._format_partial_history_error(
                        symbol=symbol,
                        requested_bars=requested_bars,
                        collected_bars=collected_bars,
                        error=(
                            f"requested batch_size={batch_size}, "
                            f"returned={len(batch_rows)}"
                        ),
                    )
                )

        merged: list[Any] = []
        for chunk in reversed(chunks):
            merged.extend(chunk)

        return merged

    @staticmethod
    def _format_partial_history_error(
        *,
        symbol: str,
        requested_bars: int,
        collected_bars: int,
        error: Any,
    ) -> str:
        if collected_bars > 0:
            return (
                f"MT5 history export stopped for {symbol} after collecting "
                f"{collected_bars} of {requested_bars} bars: {error}. "
                "The terminal likely has fewer bars loaded for this symbol/timeframe. "
                "Load more history in MT5 and retry."
            )

        return f"MT5 copy_rates_from_pos failed for {symbol}: {error}"

    @staticmethod
    def _bar_timestamp_iso(
        bar: Any,
        *,
        symbol: str,
        point: float,
    ) -> str:
        normalized = MT5MarketDataAdapter.normalize_bar(
            bar,
            symbol=symbol,
            point=point,
        )
        timestamp = normalized["timestamp"]
        if isinstance(timestamp, datetime):
            return timestamp.astimezone(timezone.utc).isoformat()
        raise TypeError("Normalized MT5 bar timestamp is not a datetime.")

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None
