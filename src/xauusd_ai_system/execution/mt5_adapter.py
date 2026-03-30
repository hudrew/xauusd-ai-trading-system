from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

from ..config.schema import ExecutionConfig
from ..core.models import RiskDecision, TradeSignal
from ..mt5_session import initialize_mt5_session
from .base import ExecutionAdapter, ExecutionOrder, ExecutionResult, ExecutionSyncResult


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

        try:
            self._initialize_terminal(mt5)
        except RuntimeError as exc:
            return ExecutionResult(
                accepted=False,
                platform=self.platform,
                error_message=str(exc),
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

    def sync_execution_state(
        self,
        *,
        order: ExecutionOrder,
        execution_result: ExecutionResult,
    ) -> ExecutionSyncResult:
        return self._capture_execution_state(
            symbol=order.symbol,
            requested_order_id=execution_result.order_id,
            requested_price=self._float_or_none(order.payload.get("price")),
            accepted=execution_result.accepted,
            order_payload=order.payload,
            execution_result=execution_result,
            sync_origin="submission",
            use_recent_history=False,
        )

    def reconcile_execution_state(
        self,
        *,
        symbol: str,
    ) -> ExecutionSyncResult:
        return self._capture_execution_state(
            symbol=symbol,
            requested_order_id=None,
            requested_price=None,
            accepted=True,
            order_payload=None,
            execution_result=None,
            sync_origin="reconcile",
            use_recent_history=True,
        )

    def _capture_execution_state(
        self,
        *,
        symbol: str,
        requested_order_id: str | None,
        requested_price: float | None,
        accepted: bool,
        order_payload: dict[str, Any] | None,
        execution_result: ExecutionResult | None,
        sync_origin: str,
        use_recent_history: bool,
    ) -> ExecutionSyncResult:
        mt5 = self._mt5()
        try:
            self._initialize_terminal(mt5)
        except RuntimeError as exc:
            return ExecutionSyncResult(
                platform=self.platform,
                symbol=symbol,
                requested_order_id=requested_order_id,
                accepted=False if sync_origin == "reconcile" else accepted,
                sync_status="sync_initialize_failed",
                sync_origin=sync_origin,
                requested_price=requested_price,
                error_message=str(exc),
            )

        try:
            if not mt5.symbol_select(symbol, True):
                return ExecutionSyncResult(
                    platform=self.platform,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                    accepted=False if sync_origin == "reconcile" else accepted,
                    sync_status="sync_symbol_select_failed",
                    sync_origin=sync_origin,
                    requested_price=requested_price,
                    error_message=f"symbol_select failed for {symbol}",
                )

            symbol_info = mt5.symbol_info(symbol)
            point_value = self._point_value(symbol_info) if symbol_info is not None else 0.0
            orders_get = getattr(mt5, "orders_get", None)
            if orders_get is None:
                return ExecutionSyncResult(
                    platform=self.platform,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                    accepted=False if sync_origin == "reconcile" else accepted,
                    sync_status="sync_orders_get_unsupported",
                    sync_origin=sync_origin,
                    requested_price=requested_price,
                    error_message="mt5.orders_get is unavailable",
                )

            positions_get = getattr(mt5, "positions_get", None)
            if positions_get is None:
                return ExecutionSyncResult(
                    platform=self.platform,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                    accepted=False if sync_origin == "reconcile" else accepted,
                    sync_status="sync_positions_get_unsupported",
                    sync_origin=sync_origin,
                    requested_price=requested_price,
                    error_message="mt5.positions_get is unavailable",
                )

            open_orders_raw = orders_get(symbol=symbol)
            if open_orders_raw is None:
                return ExecutionSyncResult(
                    platform=self.platform,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                    accepted=False if sync_origin == "reconcile" else accepted,
                    sync_status="sync_orders_get_failed",
                    sync_origin=sync_origin,
                    requested_price=requested_price,
                    error_message=f"orders_get failed for {symbol}: {mt5.last_error()}",
                )

            open_positions_raw = positions_get(symbol=symbol)
            if open_positions_raw is None:
                return ExecutionSyncResult(
                    platform=self.platform,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                    accepted=False if sync_origin == "reconcile" else accepted,
                    sync_status="sync_positions_get_failed",
                    sync_origin=sync_origin,
                    requested_price=requested_price,
                    error_message=f"positions_get failed for {symbol}: {mt5.last_error()}",
                )

            filtered_orders = self._sorted_records(
                self._filter_orders(
                    open_orders_raw,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                )
            )
            filtered_positions = self._sorted_records(
                self._filter_positions(
                    open_positions_raw,
                    symbol=symbol,
                )
            )
            if use_recent_history or requested_order_id is None:
                history_orders_raw, history_orders_error = self._load_recent_history_orders(
                    mt5,
                    symbol=symbol,
                )
                history_deals_raw, history_deals_error = self._load_recent_history_deals(
                    mt5,
                    symbol=symbol,
                )
            else:
                history_orders_raw, history_orders_error = self._load_history_orders(
                    mt5,
                    requested_order_id=requested_order_id,
                )
                history_deals_raw, history_deals_error = self._load_history_deals(
                    mt5,
                    requested_order_id=requested_order_id,
                )
            filtered_history_orders = self._sorted_records(
                self._filter_orders(
                    history_orders_raw,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                )
            )
            filtered_history_deals = self._sorted_records(
                self._filter_deals(
                    history_deals_raw,
                    symbol=symbol,
                    requested_order_id=requested_order_id,
                )
            )

            resolved_requested_order_id = self._resolve_requested_order_id(
                requested_order_id=requested_order_id,
                filtered_orders=filtered_orders,
                filtered_history_orders=filtered_history_orders,
                filtered_history_deals=filtered_history_deals,
            )

            history_order_state = self._describe_order_state(
                mt5,
                self._value_from_records(filtered_history_orders, keys=("state",)),
            )
            history_deal_ticket = self._string_from_records(
                filtered_history_deals,
                keys=("ticket",),
            )
            history_deal_entry = self._describe_deal_entry(
                mt5,
                self._value_from_records(filtered_history_deals, keys=("entry",)),
            )
            history_deal_reason = self._describe_deal_reason(
                mt5,
                self._value_from_records(filtered_history_deals, keys=("reason",)),
            )
            sync_status = self._resolve_sync_status(
                sync_origin=sync_origin,
                accepted=accepted,
                filtered_orders=filtered_orders,
                filtered_positions=filtered_positions,
                filtered_history_orders=filtered_history_orders,
                filtered_history_deals=filtered_history_deals,
                requested_order_id=resolved_requested_order_id,
                total_open_orders=len(open_orders_raw),
                total_open_positions=len(open_positions_raw),
                history_order_state=history_order_state,
                history_deal_entry=history_deal_entry,
                history_deal_reason=history_deal_reason,
            )
            observed_price, observed_price_source = self._resolve_observed_price(
                filtered_orders=filtered_orders,
                filtered_positions=filtered_positions,
                filtered_history_orders=filtered_history_orders,
                filtered_history_deals=filtered_history_deals,
                execution_result=execution_result,
            )
            position_ticket = self._string_from_records(
                filtered_positions,
                keys=("ticket",),
            )
            position_identifier = self._string_from_records(
                filtered_positions,
                keys=("identifier", "ticket"),
            ) or self._string_from_records(
                filtered_history_deals,
                keys=("position_id", "position"),
            ) or self._string_from_records(
                filtered_history_orders,
                keys=("position_id",),
            )
            price_offset = self._calculate_price_offset(
                requested_price=requested_price,
                observed_price=observed_price,
            )
            adverse_slippage = self._calculate_adverse_slippage(
                side=self._resolve_order_side(order_payload or {}),
                price_offset=price_offset,
            )
            adverse_slippage_points = (
                round(adverse_slippage / point_value, 2)
                if adverse_slippage is not None and point_value > 0
                else None
            )
            return ExecutionSyncResult(
                platform=self.platform,
                symbol=symbol,
                requested_order_id=resolved_requested_order_id,
                accepted=accepted,
                sync_status=sync_status,
                sync_origin=sync_origin,
                requested_price=requested_price,
                observed_price=observed_price,
                observed_price_source=observed_price_source,
                position_ticket=position_ticket,
                position_identifier=position_identifier,
                history_order_state=history_order_state,
                history_deal_ticket=history_deal_ticket,
                history_deal_entry=history_deal_entry,
                history_deal_reason=history_deal_reason,
                price_offset=price_offset,
                adverse_slippage=adverse_slippage,
                adverse_slippage_points=adverse_slippage_points,
                open_orders=filtered_orders,
                open_positions=filtered_positions,
                history_orders=filtered_history_orders,
                history_deals=filtered_history_deals,
                raw_response={
                    "open_orders_total": len(open_orders_raw),
                    "open_positions_total": len(open_positions_raw),
                    "history_orders_total": len(history_orders_raw),
                    "history_deals_total": len(history_deals_raw),
                    "requested_order_id": resolved_requested_order_id,
                    "sync_origin": sync_origin,
                    "requested_price": requested_price,
                    "observed_price": observed_price,
                    "observed_price_source": observed_price_source,
                    "position_ticket": position_ticket,
                    "position_identifier": position_identifier,
                    "history_order_state": history_order_state,
                    "history_deal_ticket": history_deal_ticket,
                    "history_deal_entry": history_deal_entry,
                    "history_deal_reason": history_deal_reason,
                    "price_offset": price_offset,
                    "adverse_slippage": adverse_slippage,
                    "adverse_slippage_points": adverse_slippage_points,
                    "history_orders_error": history_orders_error,
                    "history_deals_error": history_deals_error,
                },
                error_message=(
                    None
                    if execution_result is None or execution_result.accepted
                    else execution_result.error_message
                ),
            )
        finally:
            mt5.shutdown()

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

    def _initialize_terminal(self, mt5: Any) -> None:
        initialize_mt5_session(
            mt5,
            path=self.config.mt5.path,
            login=self.config.mt5.login,
            password=self.config.mt5.password,
            server=self.config.mt5.server,
        )

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

    def _filter_orders(
        self,
        records: Any,
        *,
        symbol: str,
        requested_order_id: str | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in records or ():
            if not self._record_matches_order(
                record,
                symbol=symbol,
                requested_order_id=requested_order_id,
            ):
                continue
            rows.append(self._namedtuple_to_dict(record))
        return rows

    @staticmethod
    def _sorted_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=MT5ExecutionAdapter._record_sort_key,
            reverse=True,
        )

    @staticmethod
    def _record_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
        for key in (
            "time_msc",
            "time_done_msc",
            "time_setup_msc",
            "time",
            "time_done",
            "time_setup",
            "ticket",
            "order",
            "identifier",
            "position_id",
        ):
            value = row.get(key)
            if value in (None, ""):
                continue
            try:
                return (1, float(value), "")
            except (TypeError, ValueError):
                return (0, 0.0, str(value))
        return (0, 0.0, "")

    def _filter_positions(
        self,
        records: Any,
        *,
        symbol: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in records or ():
            if not self._record_matches_position(record, symbol=symbol):
                continue
            rows.append(self._namedtuple_to_dict(record))
        return rows

    def _filter_deals(
        self,
        records: Any,
        *,
        symbol: str,
        requested_order_id: str | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in records or ():
            if not self._record_matches_deal(
                record,
                symbol=symbol,
                requested_order_id=requested_order_id,
            ):
                continue
            rows.append(self._namedtuple_to_dict(record))
        return rows

    def _record_matches_order(
        self,
        record: Any,
        *,
        symbol: str,
        requested_order_id: str | None,
    ) -> bool:
        if self._string_attr(record, "symbol") != symbol:
            return False
        if requested_order_id and self._record_has_ticket(record, requested_order_id):
            return True
        return self._record_matches_magic_or_comment(record)

    def _record_matches_position(
        self,
        record: Any,
        *,
        symbol: str,
    ) -> bool:
        if self._string_attr(record, "symbol") != symbol:
            return False
        return self._record_matches_magic_or_comment(record)

    def _record_matches_deal(
        self,
        record: Any,
        *,
        symbol: str,
        requested_order_id: str | None,
    ) -> bool:
        if self._string_attr(record, "symbol") != symbol:
            return False
        if requested_order_id and self._record_has_ticket(record, requested_order_id):
            return True
        return self._record_matches_magic_or_comment(record)

    def _record_matches_magic_or_comment(self, record: Any) -> bool:
        expected_magic = int(self.config.mt5.magic)
        record_magic = getattr(record, "magic", None)
        if record_magic is not None and int(record_magic) == expected_magic:
            return True
        comment = self._string_attr(record, "comment")
        return comment.startswith(f"{self.config.order_comment_prefix}:")

    @staticmethod
    def _record_has_ticket(record: Any, requested_order_id: str) -> bool:
        for attr in ("ticket", "order", "identifier"):
            value = getattr(record, attr, None)
            if value is not None and str(value) == str(requested_order_id):
                return True
        return False

    @staticmethod
    def _string_attr(record: Any, name: str) -> str:
        value = getattr(record, name, "")
        return str(value or "")

    @staticmethod
    def _resolve_requested_order_id(
        *,
        requested_order_id: str | None,
        filtered_orders: list[dict[str, Any]],
        filtered_history_orders: list[dict[str, Any]],
        filtered_history_deals: list[dict[str, Any]],
    ) -> str | None:
        return (
            requested_order_id
            or MT5ExecutionAdapter._string_from_records(
                filtered_orders,
                keys=("ticket", "order"),
            )
            or MT5ExecutionAdapter._string_from_records(
                filtered_history_orders,
                keys=("ticket",),
            )
            or MT5ExecutionAdapter._string_from_records(
                filtered_history_deals,
                keys=("order", "position_id", "ticket"),
            )
        )

    @staticmethod
    def _resolve_sync_status(
        *,
        sync_origin: str,
        accepted: bool,
        filtered_orders: list[dict[str, Any]],
        filtered_positions: list[dict[str, Any]],
        filtered_history_orders: list[dict[str, Any]],
        filtered_history_deals: list[dict[str, Any]],
        requested_order_id: str | None,
        total_open_orders: int,
        total_open_positions: int,
        history_order_state: str | None,
        history_deal_entry: str | None,
        history_deal_reason: str | None,
    ) -> str:
        if sync_origin == "reconcile":
            return MT5ExecutionAdapter._resolve_reconcile_sync_status(
                filtered_orders=filtered_orders,
                filtered_positions=filtered_positions,
                filtered_history_orders=filtered_history_orders,
                filtered_history_deals=filtered_history_deals,
                history_order_state=history_order_state,
                history_deal_entry=history_deal_entry,
                history_deal_reason=history_deal_reason,
            )
        return MT5ExecutionAdapter._resolve_submission_sync_status(
            accepted=accepted,
            filtered_orders=filtered_orders,
            filtered_positions=filtered_positions,
            filtered_history_orders=filtered_history_orders,
            filtered_history_deals=filtered_history_deals,
            requested_order_id=requested_order_id,
            total_open_orders=total_open_orders,
            total_open_positions=total_open_positions,
        )

    @staticmethod
    def _resolve_submission_sync_status(
        *,
        accepted: bool,
        filtered_orders: list[dict[str, Any]],
        filtered_positions: list[dict[str, Any]],
        filtered_history_orders: list[dict[str, Any]],
        filtered_history_deals: list[dict[str, Any]],
        requested_order_id: str | None,
        total_open_orders: int,
        total_open_positions: int,
    ) -> str:
        if not accepted:
            return "rejected"
        if filtered_positions:
            return "position_open"
        if filtered_orders:
            return "order_open"
        if filtered_history_deals:
            return "deal_recorded"
        if filtered_history_orders:
            return "history_order_recorded"
        if requested_order_id and (total_open_orders > 0 or total_open_positions > 0):
            return "accepted_unmatched"
        return "accepted_not_visible"

    @staticmethod
    def _resolve_reconcile_sync_status(
        *,
        filtered_orders: list[dict[str, Any]],
        filtered_positions: list[dict[str, Any]],
        filtered_history_orders: list[dict[str, Any]],
        filtered_history_deals: list[dict[str, Any]],
        history_order_state: str | None,
        history_deal_entry: str | None,
        history_deal_reason: str | None,
    ) -> str:
        if filtered_positions:
            return "position_open"
        if filtered_orders:
            return "order_open"
        if history_deal_entry in {"deal_entry_out", "deal_entry_out_by"}:
            if history_deal_reason == "deal_reason_tp":
                return "position_closed_tp"
            if history_deal_reason == "deal_reason_sl":
                return "position_closed_sl"
            if history_deal_reason == "deal_reason_so":
                return "position_closed_stopout"
            if history_deal_reason in {
                "deal_reason_client",
                "deal_reason_mobile",
                "deal_reason_web",
            }:
                return "position_closed_manual"
            if history_deal_reason == "deal_reason_expert":
                return "position_closed_expert"
            return "position_closed"
        if filtered_history_deals:
            return "deal_recorded"
        if history_order_state == "order_state_canceled":
            return "order_canceled"
        if history_order_state == "order_state_rejected":
            return "order_rejected"
        if filtered_history_orders:
            return "history_order_recorded"
        return "no_tracked_activity"

    @staticmethod
    def _resolve_observed_price(
        *,
        filtered_orders: list[dict[str, Any]],
        filtered_positions: list[dict[str, Any]],
        filtered_history_orders: list[dict[str, Any]],
        filtered_history_deals: list[dict[str, Any]],
        execution_result: ExecutionResult | None,
    ) -> tuple[float | None, str | None]:
        if filtered_history_deals:
            price = MT5ExecutionAdapter._first_price(
                filtered_history_deals[0],
                keys=("price",),
            )
            if price is not None:
                return price, "history_deal"
        if filtered_positions:
            price = MT5ExecutionAdapter._first_price(
                filtered_positions[0],
                keys=("price_open", "price_current", "price"),
            )
            if price is not None:
                return price, "position_open"
        if filtered_history_orders:
            price = MT5ExecutionAdapter._first_price(
                filtered_history_orders[0],
                keys=("price_current", "price_open", "price"),
            )
            if price is not None:
                return price, "history_order"
        if filtered_orders:
            price = MT5ExecutionAdapter._first_price(
                filtered_orders[0],
                keys=("price_open", "price_current", "price"),
            )
            if price is not None:
                return price, "order_open"
        if execution_result is not None and execution_result.raw_response:
            price = MT5ExecutionAdapter._first_price(
                execution_result.raw_response,
                keys=("price",),
            )
            if price is not None:
                return price, "execution_response"
        return None, None

    @staticmethod
    def _first_price(record: dict[str, Any], *, keys: tuple[str, ...]) -> float | None:
        for key in keys:
            value = MT5ExecutionAdapter._float_or_none(record.get(key))
            if value is not None:
                return value
        nested_request = record.get("request")
        if isinstance(nested_request, dict):
            for key in keys:
                value = MT5ExecutionAdapter._float_or_none(nested_request.get(key))
                if value is not None:
                    return value
        return None

    @staticmethod
    def _calculate_price_offset(
        *,
        requested_price: float | None,
        observed_price: float | None,
    ) -> float | None:
        if requested_price is None or observed_price is None:
            return None
        return round(observed_price - requested_price, 6)

    @staticmethod
    def _calculate_adverse_slippage(
        *,
        side: str,
        price_offset: float | None,
    ) -> float | None:
        if price_offset is None:
            return None
        normalized_side = side.upper()
        if normalized_side == "BUY":
            return round(max(price_offset, 0.0), 6)
        if normalized_side == "SELL":
            return round(max(-price_offset, 0.0), 6)
        return None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _resolve_order_side(payload: dict[str, Any]) -> str:
        for key in ("side", "type"):
            value = payload.get(key)
            if value not in (None, ""):
                return str(value)
        return ""

    def _load_history_orders(
        self,
        mt5: Any,
        *,
        requested_order_id: str | None,
    ) -> tuple[list[Any], str | None]:
        history_orders_get = getattr(mt5, "history_orders_get", None)
        if history_orders_get is None or requested_order_id is None:
            return [], None
        ticket = self._int_or_none(requested_order_id)
        if ticket is None:
            return [], f"history_orders_get skipped: invalid order id {requested_order_id}"
        rows = history_orders_get(ticket=ticket)
        if rows is None:
            return [], f"history_orders_get failed for {ticket}: {mt5.last_error()}"
        return list(rows), None

    def _load_history_deals(
        self,
        mt5: Any,
        *,
        requested_order_id: str | None,
    ) -> tuple[list[Any], str | None]:
        history_deals_get = getattr(mt5, "history_deals_get", None)
        if history_deals_get is None or requested_order_id is None:
            return [], None
        ticket = self._int_or_none(requested_order_id)
        if ticket is None:
            return [], f"history_deals_get skipped: invalid order id {requested_order_id}"
        rows = history_deals_get(ticket=ticket)
        if rows is None:
            return [], f"history_deals_get failed for {ticket}: {mt5.last_error()}"
        return list(rows), None

    def _load_recent_history_orders(
        self,
        mt5: Any,
        *,
        symbol: str,
    ) -> tuple[list[Any], str | None]:
        history_orders_get = getattr(mt5, "history_orders_get", None)
        if history_orders_get is None:
            return [], "mt5.history_orders_get is unavailable"

        window_end = datetime.now()
        window_start = window_end - timedelta(
            minutes=max(int(self.config.mt5.reconcile_history_minutes), 1)
        )
        try:
            rows = history_orders_get(
                window_start,
                window_end,
                group=f"*{symbol}*",
            )
        except TypeError:
            rows = history_orders_get(window_start, window_end)
        if rows is None:
            return [], f"history_orders_get failed for {symbol}: {mt5.last_error()}"
        return list(rows), None

    def _load_recent_history_deals(
        self,
        mt5: Any,
        *,
        symbol: str,
    ) -> tuple[list[Any], str | None]:
        history_deals_get = getattr(mt5, "history_deals_get", None)
        if history_deals_get is None:
            return [], "mt5.history_deals_get is unavailable"

        window_end = datetime.now()
        window_start = window_end - timedelta(
            minutes=max(int(self.config.mt5.reconcile_history_minutes), 1)
        )
        try:
            rows = history_deals_get(
                window_start,
                window_end,
                group=f"*{symbol}*",
            )
        except TypeError:
            rows = history_deals_get(window_start, window_end)
        if rows is None:
            return [], f"history_deals_get failed for {symbol}: {mt5.last_error()}"
        return list(rows), None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _value_from_records(
        rows: list[dict[str, Any]],
        *,
        keys: tuple[str, ...],
    ) -> Any:
        for row in rows:
            for key in keys:
                value = row.get(key)
                if value not in (None, ""):
                    return value
        return None

    @classmethod
    def _string_from_records(
        cls,
        rows: list[dict[str, Any]],
        *,
        keys: tuple[str, ...],
    ) -> str | None:
        value = cls._value_from_records(rows, keys=keys)
        if value in (None, ""):
            return None
        return str(value)

    @classmethod
    def _describe_order_state(cls, mt5: Any, value: Any) -> str | None:
        return cls._describe_constant(
            mt5,
            value,
            names=(
                "ORDER_STATE_STARTED",
                "ORDER_STATE_PLACED",
                "ORDER_STATE_CANCELED",
                "ORDER_STATE_PARTIAL",
                "ORDER_STATE_FILLED",
                "ORDER_STATE_REJECTED",
                "ORDER_STATE_EXPIRED",
                "ORDER_STATE_REQUEST_ADD",
                "ORDER_STATE_REQUEST_MODIFY",
                "ORDER_STATE_REQUEST_CANCEL",
            ),
        )

    @classmethod
    def _describe_deal_entry(cls, mt5: Any, value: Any) -> str | None:
        return cls._describe_constant(
            mt5,
            value,
            names=(
                "DEAL_ENTRY_IN",
                "DEAL_ENTRY_OUT",
                "DEAL_ENTRY_INOUT",
                "DEAL_ENTRY_OUT_BY",
            ),
        )

    @classmethod
    def _describe_deal_reason(cls, mt5: Any, value: Any) -> str | None:
        return cls._describe_constant(
            mt5,
            value,
            names=(
                "DEAL_REASON_CLIENT",
                "DEAL_REASON_MOBILE",
                "DEAL_REASON_WEB",
                "DEAL_REASON_EXPERT",
                "DEAL_REASON_SL",
                "DEAL_REASON_TP",
                "DEAL_REASON_SO",
                "DEAL_REASON_ROLLOVER",
                "DEAL_REASON_VMARGIN",
                "DEAL_REASON_SPLIT",
            ),
        )

    @staticmethod
    def _describe_constant(
        mt5: Any,
        value: Any,
        *,
        names: tuple[str, ...],
    ) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return value
        for name in names:
            constant = getattr(mt5, name, None)
            if constant is not None and constant == value:
                return name.lower()
        return str(value)
