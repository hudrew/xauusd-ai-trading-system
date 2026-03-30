from __future__ import annotations

from collections import namedtuple
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import SystemConfig
from xauusd_ai_system.core.enums import EntryType, TradeSide
from xauusd_ai_system.core.models import RiskDecision, TradeSignal
from xauusd_ai_system.execution.mt5_adapter import MT5ExecutionAdapter


class FakeSymbolInfo:
    digits = 2
    point = 0.01
    volume_min = 0.01
    volume_step = 0.01
    volume_max = 80.0
    trade_stops_level = 10


class FakeTick:
    bid = 4495.56
    ask = 4495.67


class FakeMT5Module:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_FILLED = 4
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1
    DEAL_REASON_CLIENT = 0
    DEAL_REASON_EXPERT = 3
    DEAL_REASON_SL = 4
    DEAL_REASON_TP = 5

    def __init__(
        self,
        *,
        retcode: int | None = None,
        login_ok: bool = True,
        account_login: int = 60065894,
        account_server: str = "TradeMaxGlobal-Demo",
    ) -> None:
        self.retcode = retcode or self.TRADE_RETCODE_DONE
        self.login_ok = login_ok
        self.account_login = account_login
        self.account_server = account_server
        self.initialized = False
        self.last_request = None
        self.open_orders = []
        self.open_positions = []
        self.history_orders = []
        self.history_deals = []

    def initialize(self, **kwargs):
        self.initialized = True
        return True

    def login(self, **kwargs):
        return self.login_ok

    def shutdown(self):
        self.initialized = False
        return None

    def symbol_select(self, symbol, enable):
        return True

    def symbol_info(self, symbol):
        return FakeSymbolInfo()

    def symbol_info_tick(self, symbol):
        return FakeTick()

    def order_send(self, request):
        self.last_request = request
        response_type = namedtuple("MT5Response", ["retcode", "order"])
        return response_type(retcode=self.retcode, order=123456)

    def orders_get(self, symbol=None):
        return list(self.open_orders)

    def positions_get(self, symbol=None):
        return list(self.open_positions)

    def history_orders_get(self, *args, **kwargs):
        return list(self.history_orders)

    def history_deals_get(self, *args, **kwargs):
        return list(self.history_deals)

    def last_error(self):
        return (0, "OK")

    def account_info(self):
        response_type = namedtuple("MT5AccountInfo", ["login", "server"])
        return response_type(login=self.account_login, server=self.account_server)


class MT5ExecutionAdapterNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = MT5ExecutionAdapter(SystemConfig().execution)
        self.symbol_info = FakeSymbolInfo()
        self.tick = FakeTick()

    def test_prepare_order_payload_normalizes_buy_price_volume_and_stops(self) -> None:
        payload = {
            "symbol": "XAUUSD",
            "volume": 0.127,
            "type": "BUY",
            "price": 4495.60,
            "sl": 4495.64,
            "tp": 4495.72,
            "deviation": 30,
            "magic": 2026032901,
            "comment": "xauusd-ai:test",
        }

        prepared, error = self.adapter._prepare_order_payload(
            payload,
            symbol_info=self.symbol_info,
            tick=self.tick,
        )

        self.assertIsNone(error)
        assert prepared is not None
        self.assertEqual(prepared["price"], 4495.67)
        self.assertEqual(prepared["volume"], 0.12)
        self.assertEqual(prepared["sl"], 4495.57)
        self.assertEqual(prepared["tp"], 4495.77)

    def test_prepare_order_payload_rejects_volume_below_broker_minimum(self) -> None:
        payload = {
            "symbol": "XAUUSD",
            "volume": 0.005,
            "type": "SELL",
            "price": 4495.60,
            "sl": 4495.70,
            "tp": 4495.40,
            "deviation": 30,
            "magic": 2026032901,
            "comment": "xauusd-ai:test",
        }

        prepared, error = self.adapter._prepare_order_payload(
            payload,
            symbol_info=self.symbol_info,
            tick=self.tick,
        )

        self.assertIsNone(prepared)
        self.assertIn("below broker minimum", error or "")

    def test_submit_order_mutates_order_to_actual_request_and_accepts_partial_fill(self) -> None:
        config = SystemConfig().execution
        config.platform = "mt5"
        config.mt5.symbol = "XAUUSD"
        fake_mt5 = FakeMT5Module(retcode=FakeMT5Module.TRADE_RETCODE_DONE_PARTIAL)
        adapter = MT5ExecutionAdapter(config, mt5_module=fake_mt5)

        signal = TradeSignal(
            strategy_name="breakout",
            side=TradeSide.BUY,
            entry_type=EntryType.MARKET,
            entry_price=4495.60,
            stop_loss=4495.64,
            take_profit=4495.72,
        )
        risk = RiskDecision(allowed=True, position_size=0.127)
        order = adapter.build_order(signal, risk)

        result = adapter.submit_order(order)

        self.assertTrue(result.accepted)
        self.assertEqual(order.volume, 0.12)
        self.assertEqual(order.payload["price"], 4495.67)
        self.assertEqual(order.payload["sl"], 4495.57)
        self.assertEqual(order.payload["tp"], 4495.77)
        self.assertEqual(order.payload["volume"], 0.12)
        self.assertEqual(fake_mt5.last_request["volume"], 0.12)
        self.assertEqual(fake_mt5.last_request["price"], 4495.67)

    def test_submit_order_returns_clear_error_when_account_binding_is_wrong(self) -> None:
        config = SystemConfig().execution
        config.platform = "mt5"
        config.mt5.symbol = "XAUUSD"
        config.mt5.login = 60065894
        config.mt5.password = "secret"
        config.mt5.server = "TradeMaxGlobal-Demo"
        fake_mt5 = FakeMT5Module(
            account_login=50182922,
            account_server="TradeMaxGlobal-Live",
        )
        adapter = MT5ExecutionAdapter(config, mt5_module=fake_mt5)

        signal = TradeSignal(
            strategy_name="pullback",
            side=TradeSide.SELL,
            entry_type=EntryType.MARKET,
            entry_price=4495.56,
            stop_loss=4495.80,
            take_profit=4495.10,
        )
        risk = RiskDecision(allowed=True, position_size=0.12)
        order = adapter.build_order(signal, risk)

        result = adapter.submit_order(order)

        self.assertFalse(result.accepted)
        self.assertIn("unexpected account", result.error_message or "")

    def test_sync_execution_state_reports_open_position_for_matching_magic(self) -> None:
        config = SystemConfig().execution
        config.platform = "mt5"
        config.mt5.symbol = "XAUUSD"
        config.mt5.magic = 2026033003
        config.order_comment_prefix = "xauusd-ai-pbsv3"
        fake_mt5 = FakeMT5Module()
        position_type = namedtuple(
            "MT5Position",
            ["ticket", "identifier", "symbol", "magic", "comment", "volume", "price_open"],
        )
        fake_mt5.open_positions = [
            position_type(
                ticket=777001,
                identifier=880001,
                symbol="XAUUSD",
                magic=2026033003,
                comment="xauusd-ai-pbsv3:pullback",
                volume=0.12,
                price_open=4495.50,
            )
        ]
        adapter = MT5ExecutionAdapter(config, mt5_module=fake_mt5)

        signal = TradeSignal(
            strategy_name="pullback",
            side=TradeSide.SELL,
            entry_type=EntryType.MARKET,
            entry_price=4495.56,
            stop_loss=4495.80,
            take_profit=4495.10,
        )
        risk = RiskDecision(allowed=True, position_size=0.12)
        order = adapter.build_order(signal, risk)
        execution_result = adapter.submit_order(order)

        sync_result = adapter.sync_execution_state(
            order=order,
            execution_result=execution_result,
        )

        self.assertEqual(sync_result.sync_status, "position_open")
        self.assertEqual(sync_result.requested_order_id, "123456")
        self.assertEqual(sync_result.requested_price, 4495.56)
        self.assertEqual(sync_result.observed_price, 4495.50)
        self.assertEqual(sync_result.observed_price_source, "position_open")
        self.assertEqual(sync_result.position_ticket, "777001")
        self.assertEqual(sync_result.position_identifier, "880001")
        self.assertIsNone(sync_result.history_order_state)
        self.assertIsNone(sync_result.history_deal_entry)
        self.assertIsNone(sync_result.history_deal_reason)
        self.assertEqual(sync_result.price_offset, -0.06)
        self.assertEqual(sync_result.adverse_slippage, 0.06)
        self.assertEqual(sync_result.adverse_slippage_points, 6.0)
        self.assertEqual(len(sync_result.open_positions), 1)
        self.assertEqual(sync_result.open_positions[0]["ticket"], 777001)
        self.assertEqual(sync_result.history_orders, [])
        self.assertEqual(sync_result.history_deals, [])

    def test_sync_execution_state_reports_history_deal_when_order_is_already_historical(self) -> None:
        config = SystemConfig().execution
        config.platform = "mt5"
        config.mt5.symbol = "XAUUSD"
        config.mt5.magic = 2026033003
        config.order_comment_prefix = "xauusd-ai-pbsv3"
        fake_mt5 = FakeMT5Module()
        order_type = namedtuple(
            "MT5HistoryOrder",
            [
                "ticket",
                "symbol",
                "magic",
                "comment",
                "position_id",
                "state",
                "price_open",
                "price_current",
            ],
        )
        deal_type = namedtuple(
            "MT5HistoryDeal",
            [
                "ticket",
                "order",
                "symbol",
                "magic",
                "comment",
                "position_id",
                "entry",
                "reason",
                "price",
                "volume",
            ],
        )
        fake_mt5.history_orders = [
            order_type(
                ticket=123456,
                symbol="XAUUSD",
                magic=2026033003,
                comment="xauusd-ai-pbsv3:pullback",
                position_id=880001,
                state=FakeMT5Module.ORDER_STATE_FILLED,
                price_open=4495.56,
                price_current=4495.52,
            )
        ]
        fake_mt5.history_deals = [
            deal_type(
                ticket=880001,
                order=123456,
                symbol="XAUUSD",
                magic=2026033003,
                comment="xauusd-ai-pbsv3:pullback",
                position_id=880001,
                entry=FakeMT5Module.DEAL_ENTRY_IN,
                reason=FakeMT5Module.DEAL_REASON_EXPERT,
                price=4495.52,
                volume=0.12,
            )
        ]
        adapter = MT5ExecutionAdapter(config, mt5_module=fake_mt5)

        signal = TradeSignal(
            strategy_name="pullback",
            side=TradeSide.SELL,
            entry_type=EntryType.MARKET,
            entry_price=4495.56,
            stop_loss=4495.80,
            take_profit=4495.10,
        )
        risk = RiskDecision(allowed=True, position_size=0.12)
        order = adapter.build_order(signal, risk)
        execution_result = adapter.submit_order(order)

        sync_result = adapter.sync_execution_state(
            order=order,
            execution_result=execution_result,
        )

        self.assertEqual(sync_result.sync_status, "deal_recorded")
        self.assertEqual(sync_result.requested_order_id, "123456")
        self.assertEqual(sync_result.observed_price, 4495.52)
        self.assertEqual(sync_result.observed_price_source, "history_deal")
        self.assertIsNone(sync_result.position_ticket)
        self.assertEqual(sync_result.position_identifier, "880001")
        self.assertEqual(sync_result.history_order_state, "order_state_filled")
        self.assertEqual(sync_result.history_deal_ticket, "880001")
        self.assertEqual(sync_result.history_deal_entry, "deal_entry_in")
        self.assertEqual(sync_result.history_deal_reason, "deal_reason_expert")
        self.assertEqual(sync_result.price_offset, -0.04)
        self.assertEqual(sync_result.adverse_slippage_points, 4.0)
        self.assertEqual(len(sync_result.history_orders), 1)
        self.assertEqual(len(sync_result.history_deals), 1)
        self.assertEqual(sync_result.history_deals[0]["ticket"], 880001)

    def test_reconcile_execution_state_reports_recent_take_profit_close(self) -> None:
        config = SystemConfig().execution
        config.platform = "mt5"
        config.mt5.symbol = "XAUUSD"
        config.mt5.magic = 2026033003
        config.mt5.reconcile_history_minutes = 180
        config.order_comment_prefix = "xauusd-ai-pbsv3"
        fake_mt5 = FakeMT5Module()
        order_type = namedtuple(
            "MT5HistoryOrder",
            [
                "ticket",
                "symbol",
                "magic",
                "comment",
                "position_id",
                "state",
                "price_open",
                "time_done_msc",
            ],
        )
        deal_type = namedtuple(
            "MT5HistoryDeal",
            [
                "ticket",
                "order",
                "symbol",
                "magic",
                "comment",
                "position_id",
                "entry",
                "reason",
                "price",
                "time_msc",
            ],
        )
        fake_mt5.history_orders = [
            order_type(
                ticket=123456,
                symbol="XAUUSD",
                magic=2026033003,
                comment="xauusd-ai-pbsv3:pullback",
                position_id=880001,
                state=FakeMT5Module.ORDER_STATE_FILLED,
                price_open=4495.56,
                time_done_msc=1711863000100,
            )
        ]
        fake_mt5.history_deals = [
            deal_type(
                ticket=880002,
                order=123456,
                symbol="XAUUSD",
                magic=2026033003,
                comment="xauusd-ai-pbsv3:pullback",
                position_id=880001,
                entry=FakeMT5Module.DEAL_ENTRY_OUT,
                reason=FakeMT5Module.DEAL_REASON_TP,
                price=4495.10,
                time_msc=1711863000200,
            )
        ]
        adapter = MT5ExecutionAdapter(config, mt5_module=fake_mt5)

        sync_result = adapter.reconcile_execution_state(symbol="XAUUSD")

        self.assertEqual(sync_result.sync_origin, "reconcile")
        self.assertEqual(sync_result.sync_status, "position_closed_tp")
        self.assertEqual(sync_result.requested_order_id, "123456")
        self.assertEqual(sync_result.observed_price, 4495.10)
        self.assertEqual(sync_result.observed_price_source, "history_deal")
        self.assertEqual(sync_result.position_identifier, "880001")
        self.assertEqual(sync_result.history_order_state, "order_state_filled")
        self.assertEqual(sync_result.history_deal_ticket, "880002")
        self.assertEqual(sync_result.history_deal_entry, "deal_entry_out")
        self.assertEqual(sync_result.history_deal_reason, "deal_reason_tp")
        self.assertIsNone(sync_result.requested_price)
        self.assertIsNone(sync_result.price_offset)


if __name__ == "__main__":
    unittest.main()
