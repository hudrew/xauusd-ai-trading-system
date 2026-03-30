from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import SystemConfig
from xauusd_ai_system.preflight.mt5_runner import MT5PreflightRunner


class FakeAccountInfo:
    login = 10001
    equity = 10500.0
    trade_allowed = True
    server = "TradeMaxGlobal-Demo"


class FakeTerminalInfo:
    tradeapi_disabled = False


class FakeSymbolInfo:
    visible = True
    trade_mode = 4
    digits = 2
    trade_contract_size = 100.0
    volume_min = 0.01
    volume_step = 0.01
    volume_max = 80.0
    trade_stops_level = 0


class FakeTick:
    bid = 3060.1
    ask = 3060.3


class FakeZeroTick:
    bid = 0.0
    ask = 0.0


class FakeMT5:
    TIMEFRAME_M1 = 1

    def __init__(
        self,
        *,
        initialize_ok: bool = True,
        login_ok: bool = True,
        tradeapi_disabled: bool = False,
        zero_tick: bool = False,
        account_login: int = 10001,
        account_server: str = "TradeMaxGlobal-Demo",
    ) -> None:
        self.initialize_ok = initialize_ok
        self.login_ok = login_ok
        self._tradeapi_disabled = tradeapi_disabled
        self.trade_contract_size = 100.0
        self.zero_tick = zero_tick
        self.account_login = account_login
        self.account_server = account_server

    def initialize(self, **kwargs):
        return self.initialize_ok

    def login(self, **kwargs):
        return self.login_ok

    def shutdown(self):
        return None

    def last_error(self):
        return (0, "OK")

    def account_info(self):
        info = FakeAccountInfo()
        info.login = self.account_login
        info.server = self.account_server
        return info

    def terminal_info(self):
        info = FakeTerminalInfo()
        info.tradeapi_disabled = self._tradeapi_disabled
        return info

    def symbol_select(self, symbol, enable):
        return True

    def symbol_info(self, symbol):
        info = FakeSymbolInfo()
        info.trade_contract_size = self.trade_contract_size
        return info

    def symbol_info_tick(self, symbol):
        if self.zero_tick:
            return FakeZeroTick()
        return FakeTick()

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        return [{"time": 1}] * count


class MT5PreflightRunnerTests(unittest.TestCase):
    def test_preflight_ready_in_dry_run(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.runtime.dry_run = True
        config.market_data.mt5.timeframe = "M1"
        config.market_data.mt5.history_bars = 10

        report = MT5PreflightRunner(config, mt5_module=FakeMT5()).run()

        self.assertTrue(report.ready)
        self.assertEqual(report.platform, "mt5")
        self.assertTrue(any(item.name == "mt5_initialize" and item.passed for item in report.checks))
        self.assertTrue(any(item.name == "recent_bars" and item.passed for item in report.checks))
        self.assertTrue(
            any(item.name == "contract_size_alignment" and item.passed for item in report.checks)
        )

    def test_preflight_fails_when_trade_disabled_in_live_mode(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.runtime.dry_run = False
        config.market_data.mt5.timeframe = "M1"
        config.market_data.mt5.history_bars = 10

        report = MT5PreflightRunner(
            config,
            mt5_module=FakeMT5(tradeapi_disabled=True),
        ).run()

        self.assertFalse(report.ready)
        trade_check = next(item for item in report.checks if item.name == "trade_permission")
        self.assertFalse(trade_check.passed)

    def test_preflight_fails_when_contract_size_mismatches_broker_spec(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.market_data.mt5.timeframe = "M1"
        config.market_data.mt5.history_bars = 10
        config.risk.contract_size = 50.0

        report = MT5PreflightRunner(
            config,
            mt5_module=FakeMT5(),
        ).run()

        self.assertFalse(report.ready)
        contract_check = next(
            item for item in report.checks if item.name == "contract_size_alignment"
        )
        self.assertFalse(contract_check.passed)

    def test_preflight_fails_when_initialize_fails(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"

        report = MT5PreflightRunner(
            config,
            mt5_module=FakeMT5(initialize_ok=False),
        ).run()

        self.assertFalse(report.ready)
        init_check = next(item for item in report.checks if item.name == "mt5_initialize")
        self.assertFalse(init_check.passed)

    def test_preflight_marks_zero_quote_tick_as_informative_detail(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.runtime.dry_run = True
        config.market_data.mt5.timeframe = "M1"
        config.market_data.mt5.history_bars = 10

        report = MT5PreflightRunner(
            config,
            mt5_module=FakeMT5(zero_tick=True),
        ).run()

        self.assertTrue(report.ready)
        tick_check = next(item for item in report.checks if item.name == "latest_tick")
        self.assertTrue(tick_check.passed)
        self.assertTrue(tick_check.metadata["zero_quote"])
        self.assertIn("bid/ask are both 0", tick_check.detail)

    def test_preflight_fails_when_terminal_stays_on_unexpected_account(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.execution.platform = "mt5"
        config.runtime.dry_run = True
        config.execution.mt5.login = 60065894
        config.execution.mt5.password = "secret"
        config.execution.mt5.server = "TradeMaxGlobal-Demo"

        report = MT5PreflightRunner(
            config,
            mt5_module=FakeMT5(account_login=50182922, account_server="TradeMaxGlobal-Live"),
        ).run()

        self.assertFalse(report.ready)
        init_check = next(item for item in report.checks if item.name == "mt5_initialize")
        self.assertFalse(init_check.passed)
        self.assertIn("unexpected account", init_check.detail)


if __name__ == "__main__":
    unittest.main()
