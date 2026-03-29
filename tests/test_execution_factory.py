from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import ExecutionConfig, SystemConfig
from xauusd_ai_system.core.enums import EntryType, TradeSide
from xauusd_ai_system.core.models import RiskDecision, TradeSignal
from xauusd_ai_system.execution.ctrader_adapter import CTraderOpenApiAdapter
from xauusd_ai_system.execution.factory import build_execution_adapter
from xauusd_ai_system.execution.mt5_adapter import MT5ExecutionAdapter


class ExecutionFactoryTests(unittest.TestCase):
    def test_builds_ctrader_adapter(self) -> None:
        config = ExecutionConfig(platform="ctrader")
        adapter = build_execution_adapter(config)
        self.assertIsInstance(adapter, CTraderOpenApiAdapter)

    def test_builds_mt5_adapter(self) -> None:
        config = ExecutionConfig(platform="mt5")
        adapter = build_execution_adapter(config)
        self.assertIsInstance(adapter, MT5ExecutionAdapter)

    def test_builds_none_adapter(self) -> None:
        config = ExecutionConfig(platform="none")
        adapter = build_execution_adapter(config)
        self.assertIsNone(adapter)

    def test_ctrader_payload_uses_risk_position_size(self) -> None:
        config = SystemConfig()
        config.execution.platform = "ctrader"
        config.execution.ctrader.account_id = 12345
        signal = TradeSignal(
            strategy_name="breakout",
            side=TradeSide.BUY,
            entry_type=EntryType.MARKET,
            entry_price=3063.0,
            stop_loss=3061.5,
            take_profit=3066.0,
        )
        risk = RiskDecision(allowed=True, position_size=0.12)

        order = CTraderOpenApiAdapter(config.execution).build_order(signal, risk)
        self.assertEqual(order.payload["account_id"], 12345)
        self.assertEqual(order.payload["volume"], 0.12)

    def test_mt5_payload_contains_magic_and_symbol(self) -> None:
        config = SystemConfig()
        config.execution.platform = "mt5"
        config.execution.mt5.symbol = "XAUUSD"
        signal = TradeSignal(
            strategy_name="breakout",
            side=TradeSide.SELL,
            entry_type=EntryType.MARKET,
            entry_price=3063.0,
            stop_loss=3064.0,
            take_profit=3060.0,
        )
        risk = RiskDecision(allowed=True, position_size=0.2)

        order = MT5ExecutionAdapter(config.execution).build_order(signal, risk)
        self.assertEqual(order.payload["symbol"], "XAUUSD")
        self.assertEqual(order.payload["magic"], config.execution.mt5.magic)
        self.assertEqual(order.payload["type"], "SELL")


if __name__ == "__main__":
    unittest.main()
