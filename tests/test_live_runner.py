from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import pandas as pd
except ImportError:
    pd = None
    AccountState = None
    EventContext = None
    LiveTradingRunner = None
    MarketState = None
    Quote = None
    RiskDecision = None
    StateDecision = None
    SystemConfig = None
    TradingDecision = None
else:
    from xauusd_ai_system.config.schema import SystemConfig
    from xauusd_ai_system.core.enums import MarketState
    from xauusd_ai_system.core.models import (
        AccountState,
        RiskDecision,
        StateDecision,
        TradingDecision,
    )
    from xauusd_ai_system.market_data.base import Quote
    from xauusd_ai_system.runtime.live_runner import EventContext, LiveTradingRunner


class StubRuntimeService:
    def __init__(self) -> None:
        self.snapshot = None
        self.account_state = None

    def process_snapshot(self, snapshot, account_state):
        self.snapshot = snapshot
        self.account_state = account_state
        return TradingDecision(
            state=StateDecision(
                state_label=MarketState.NO_TRADE,
                confidence_score=1.0,
                reason_codes=["TEST"],
            ),
            volatility=None,
            signal=None,
            risk=RiskDecision(allowed=False, risk_reason=["TEST"]),
        )

    def shutdown(self) -> None:
        return None


class StubAccountStateService:
    def __init__(self, account_state: AccountState) -> None:
        self.account_state = account_state
        self.reference_times: list[datetime] = []
        self.closed = False

    def get_account_state(self, reference_time: datetime | None = None) -> AccountState:
        if reference_time is not None:
            self.reference_times.append(reference_time)
        return self.account_state

    def close(self) -> None:
        self.closed = True


class StubMarketDataService:
    def __init__(self, quote: Quote, bars: list[dict]) -> None:
        self.adapter = object()
        self.quote = quote
        self.bars = bars
        self.requested_counts: list[int] = []

    def get_latest_quote(self) -> Quote:
        return self.quote

    def get_recent_bars(self, count: int) -> list[dict]:
        self.requested_counts.append(count)
        return self.bars


@unittest.skipIf(pd is None, "pandas is not installed")
class LiveTradingRunnerTests(unittest.TestCase):
    def test_run_once_builds_snapshot_from_live_bars(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.market_data.mt5.history_bars = 240

        timestamps = pd.date_range("2026-03-29 08:00:00", periods=240, freq="min")
        close = pd.Series(range(240), dtype="float64") * 0.04 + 3000.0
        bars = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close + 0.1,
                "tick_volume": 3,
            }
        ).to_dict(orient="records")
        quote = Quote(
            timestamp=datetime(2026, 3, 29, 11, 59, 30),
            symbol="XAUUSD",
            bid=3009.55,
            ask=3009.75,
        )

        runtime_service = StubRuntimeService()
        market_data_service = StubMarketDataService(quote, bars)
        account_state_service = StubAccountStateService(
            AccountState(equity=config.runtime.starting_equity)
        )
        runner = LiveTradingRunner(
            config,
            runtime_service=runtime_service,
            market_data_service=market_data_service,
            account_state_service=account_state_service,
        )

        runner.run_once()

        self.assertEqual(market_data_service.requested_counts, [240])
        self.assertIsNotNone(runtime_service.snapshot)
        self.assertEqual(runtime_service.snapshot.symbol, "XAUUSD")
        self.assertEqual(runtime_service.snapshot.timestamp, quote.timestamp)
        self.assertEqual(runtime_service.snapshot.bid, 3009.55)
        self.assertEqual(runtime_service.snapshot.ask, 3009.75)
        self.assertEqual(runtime_service.snapshot.session_tag, "eu")
        self.assertIsNotNone(runtime_service.snapshot.feature("atr_m1_14"))
        self.assertIsNotNone(runtime_service.snapshot.feature("atr_m15_14"))
        self.assertIsNotNone(runtime_service.snapshot.feature("atr_h1_14"))
        self.assertIsNotNone(runtime_service.snapshot.feature("bollinger_position"))
        self.assertIsNotNone(runtime_service.snapshot.feature("volatility_ratio"))
        self.assertEqual(runtime_service.snapshot.feature("hour_bucket"), 11)
        self.assertEqual(runtime_service.account_state.equity, config.runtime.starting_equity)
        self.assertEqual(account_state_service.reference_times, [quote.timestamp])

    def test_run_once_passes_event_context_and_account_state(self) -> None:
        config = SystemConfig()
        config.market_data.platform = "mt5"
        config.market_data.mt5.history_bars = 240

        timestamps = pd.date_range("2026-03-29 12:00:00", periods=240, freq="min")
        close = pd.Series(range(240), dtype="float64") * 0.02 + 3050.0
        bars = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": close,
                "high": close + 0.4,
                "low": close - 0.4,
                "close": close + 0.1,
                "volume": 5,
            }
        ).to_dict(orient="records")
        quote = Quote(
            timestamp=datetime(2026, 3, 29, 15, 59, 45),
            symbol="XAUUSD",
            bid=3054.2,
            ask=3054.4,
        )

        runtime_service = StubRuntimeService()
        market_data_service = StubMarketDataService(quote, bars)
        account_state_service = StubAccountStateService(
            AccountState(equity=config.runtime.starting_equity)
        )
        runner = LiveTradingRunner(
            config,
            runtime_service=runtime_service,
            market_data_service=market_data_service,
            account_state_service=account_state_service,
        )
        account_state = AccountState(equity=25_000.0, open_positions=1)
        event_context = EventContext(news_flag=True, minutes_to_event=6)

        runner.run_once(account_state=account_state, event_context=event_context)

        self.assertTrue(runtime_service.snapshot.news_flag)
        self.assertEqual(runtime_service.snapshot.minutes_to_event, 6)
        self.assertEqual(runtime_service.account_state.equity, 25_000.0)
        self.assertEqual(runtime_service.account_state.open_positions, 1)
        self.assertEqual(account_state_service.reference_times, [])


if __name__ == "__main__":
    unittest.main()
