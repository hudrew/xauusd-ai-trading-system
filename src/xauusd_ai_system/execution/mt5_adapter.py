from __future__ import annotations

import math
from typing import Any

from ..config.schema import ExecutionConfig
from ..core.models import RiskDecision, TradeSignal
from .base import ExecutionAdapter, ExecutionOrder, ExecutionResult


class MT5ExecutionAdapter(ExecutionAdapter):
    """
    MetaTrader 5 execution adapter.

    MetaQuotes documents Python integration through the `MetaTrader5` package
    with `initialize`, `login`, `order_send`, and market data functions.
    """

    platform = "mt5"

    def __init__(self, config: ExecutionConfig, mt5_module: Any | None = None) -> None:
        self.config = config
        self._mt5_module = mt5_module

    def build_order(
        self,
        signal: TradeSignal,
        risk: RiskDecision,
    ) -> ExecutionOrder:
        order_type = "BUY" if signal.side.value == "buy" else "SELL"
        payload = {
            "action": "TRADE_ACTION_DEAL",
            "symbol": self.config.mt5.symbol or self.config.symbol,
            "volume": risk.position_size,
            "type": order_type,
            "price": signal.entry_price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": self.config.mt5.deviation,
            "magic": self.config.mt5.magic,
            "comment": f"{self.config.order_comment_prefix}:{signal.strategy_name}",
            "type_time": "ORDER_TIME_GTC",
            "type_filling": "ORDER_FILLING_IOC",
        }
        return ExecutionOrder(
            platform=self.platform,
            symbol=payload["symbol"],
            volume=risk.position_size,
            payload=payload,
        )

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        mt5 = self._mt5()

        if not mt5.initialize(
            path=self.config.mt5.path,
            login=self.config.mt5.login,
            password=self.config.mt5.password,
            server=self.config.mt5.server,
        ):
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message=f"mt5.initialize failed: {mt5.last_error()}",
            )

        if not mt5.symbol_select(order.symbol, True):
            mt5.shutdown()
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message=f"symbol_select failed for {order.symbol}",
            )

        symbol_info = mt5.symbol_info(order.symbol)
        if symbol_info is None:
            mt5.shutdown()
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message=f"symbol_info failed for {order.symbol}: {mt5.last_error()}",
            )

        tick = mt5.symbol_info_tick(order.symbol)
        if tick is None:
            mt5.shutdown()
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message=f"symbol_info_tick failed for {order.symbol}: {mt5.last_error()}",
            )

        prepared_payload, payload_error = self._prepare_order_payload(
            order.payload,
            symbol_info=symbol_info,
            tick=tick,
        )
        if prepared_payload is None:
            mt5.shutdown()
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message=payload_error or "failed to prepare mt5 request payload",
            )

        order.payload = prepared_payload
        order.volume = float(prepared_payload["volume"])
        request_payload = self._resolve_mt5_constants(mt5, prepared_payload)
        response = mt5.order_send(request_payload)
        mt5.shutdown()

        if response is None:
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message="mt5.order_send returned None",
            )

        raw_response = self._namedtuple_to_dict(response)
        accepted = self._retcode_accepted(mt5, getattr(response, "retcode", None))
        return ExecutionResult(
            accepted=accepted,
            platform=self.platform,
            order_id=str(getattr(response, "order", "")) or None,
            raw_response=raw_response,
            error_message=None if accepted else str(raw_response),
        )

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
    def _resolve_mt5_constants(mt5: Any, payload: dict[str, Any]) -> dict[str, Any]:
        side_map = {
            "BUY": mt5.ORDER_TYPE_BUY,
            "SELL": mt5.ORDER_TYPE_SELL,
        }
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": payload["symbol"],
            "volume": payload["volume"],
            "type": side_map[payload["type"]],
            "price": payload["price"],
            "sl": payload["sl"],
            "tp": payload["tp"],
            "deviation": payload["deviation"],
            "magic": payload["magic"],
            "comment": payload["comment"],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

    @staticmethod
    def _namedtuple_to_dict(value: Any) -> dict[str, Any]:
        if hasattr(value, "_asdict"):
            data = value._asdict()
            return {
                str(key): MT5ExecutionAdapter._namedtuple_to_dict(item)
                for key, item in data.items()
            }
        return value

    def _prepare_order_payload(
        self,
        payload: dict[str, Any],
        *,
        symbol_info: Any,
        tick: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        prepared = dict(payload)
        prepared["price"] = self._resolve_market_price(prepared, tick)

        normalized_volume = self._normalize_volume(
            float(prepared["volume"]),
            min_volume=self._float_attr(symbol_info, "volume_min"),
            volume_step=self._float_attr(symbol_info, "volume_step"),
            max_volume=self._float_attr(symbol_info, "volume_max"),
        )
        if normalized_volume is None:
            return (
                None,
                "calculated volume is below broker minimum or invalid after step normalization",
            )
        prepared["volume"] = normalized_volume

        sl, tp = self._normalize_stops(
            side=str(prepared["type"]),
            price=float(prepared["price"]),
            stop_loss=float(prepared["sl"]),
            take_profit=float(prepared["tp"]),
            stops_level_points=self._stops_level_points(symbol_info),
            point=self._point_value(symbol_info),
            digits=int(getattr(symbol_info, "digits", 2) or 2),
        )
        prepared["sl"] = sl
        prepared["tp"] = tp
        return prepared, None

    @staticmethod
    def _resolve_market_price(payload: dict[str, Any], tick: Any) -> float:
        side = str(payload["type"]).upper()
        if side == "BUY":
            return float(getattr(tick, "ask", payload["price"]))
        return float(getattr(tick, "bid", payload["price"]))

    @staticmethod
    def _normalize_volume(
        volume: float,
        *,
        min_volume: float,
        volume_step: float,
        max_volume: float | None,
    ) -> float | None:
        epsilon = 1e-9
        if volume <= 0:
            return None
        if min_volume > 0 and volume + epsilon < min_volume:
            return None

        capped = min(volume, max_volume) if max_volume and max_volume > 0 else volume
        if volume_step > 0:
            base = min_volume if min_volume > 0 else 0.0
            steps = math.floor(((capped - base) / volume_step) + epsilon)
            normalized = base + max(steps, 0) * volume_step
        else:
            normalized = capped

        if max_volume and max_volume > 0:
            normalized = min(normalized, max_volume)
        if min_volume > 0 and normalized + epsilon < min_volume:
            return None
        return round(normalized, 8)

    @staticmethod
    def _normalize_stops(
        *,
        side: str,
        price: float,
        stop_loss: float,
        take_profit: float,
        stops_level_points: int,
        point: float,
        digits: int,
    ) -> tuple[float, float]:
        min_distance = max(stops_level_points, 0) * max(point, 0.0)
        if min_distance <= 0:
            return round(stop_loss, digits), round(take_profit, digits)

        normalized_side = side.upper()
        sl = stop_loss
        tp = take_profit
        if normalized_side == "BUY":
            sl = min(sl, price - min_distance)
            tp = max(tp, price + min_distance)
        else:
            sl = max(sl, price + min_distance)
            tp = min(tp, price - min_distance)
        return round(sl, digits), round(tp, digits)

    @staticmethod
    def _stops_level_points(symbol_info: Any) -> int:
        value = getattr(symbol_info, "trade_stops_level", None)
        if value is None:
            value = getattr(symbol_info, "stops_level", 0)
        return int(value or 0)

    @staticmethod
    def _point_value(symbol_info: Any) -> float:
        point = getattr(symbol_info, "point", None)
        if point is not None:
            return float(point)
        digits = int(getattr(symbol_info, "digits", 2) or 2)
        return 10 ** (-digits)

    @staticmethod
    def _float_attr(symbol_info: Any, name: str, default: float = 0.0) -> float:
        value = getattr(symbol_info, name, default)
        if value is None:
            return default
        return float(value)

    @staticmethod
    def _retcode_accepted(mt5: Any, retcode: Any) -> bool:
        accepted_codes = {
            getattr(mt5, "TRADE_RETCODE_DONE", None),
            getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", None),
        }
        return retcode in accepted_codes
