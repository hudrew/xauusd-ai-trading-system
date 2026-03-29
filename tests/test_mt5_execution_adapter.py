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

    def __init__(self, *, retcode: int | None = None) -> None:
        self.retcode = retcode or self.TRADE_RETCODE_DONE
        self.initialized = False
        self.last_request = None

    def initialize(self, **kwargs):
        self.initialized = True
        return True

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

    def last_error(self):
        return (0, "OK")


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


if __name__ == "__main__":
    unittest.main()
