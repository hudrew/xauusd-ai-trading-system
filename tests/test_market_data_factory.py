from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import MarketDataConfig, SystemConfig
from xauusd_ai_system.market_data.ctrader_adapter import CTraderMarketDataAdapter
from xauusd_ai_system.market_data.factory import build_market_data_adapter
from xauusd_ai_system.market_data.mt5_adapter import MT5MarketDataAdapter


class MarketDataFactoryTests(unittest.TestCase):
    def test_builds_ctrader_market_data_adapter(self) -> None:
        config = MarketDataConfig(platform="ctrader")
        adapter = build_market_data_adapter(config)
        self.assertIsInstance(adapter, CTraderMarketDataAdapter)

    def test_builds_mt5_market_data_adapter(self) -> None:
        config = MarketDataConfig(platform="mt5")
        adapter = build_market_data_adapter(config)
        self.assertIsInstance(adapter, MT5MarketDataAdapter)

    def test_ctrader_subscription_request_requires_symbol_id(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "ctrader"
        config.market_data.ctrader.client_id = "client-id"
        config.market_data.ctrader.client_secret = "client-secret"
        config.market_data.ctrader.account_id = 123
        config.market_data.ctrader.access_token = "token"
        adapter = CTraderMarketDataAdapter(config.market_data)

        with self.assertRaises(ValueError):
            adapter.build_spot_subscription_requests()


if __name__ == "__main__":
    unittest.main()
