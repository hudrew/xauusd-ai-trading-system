from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.account_state.base import BrokerAccountSnapshot
from xauusd_ai_system.account_state.service import AccountStateService
from xauusd_ai_system.config.schema import SystemConfig
from xauusd_ai_system.storage.account_state_store import SQLiteAccountStateStore


class StubProvider:
    def __init__(self, snapshots: list[BrokerAccountSnapshot]) -> None:
        self.snapshots = list(snapshots)

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        if not self.snapshots:
            raise RuntimeError("No more snapshots")
        return self.snapshots.pop(0)


class AccountStateServiceTests(unittest.TestCase):
    def test_fallback_without_provider_uses_starting_equity(self) -> None:
        config = SystemConfig()
        config.runtime.starting_equity = 12_500.0

        service = AccountStateService(config, provider=None)
        state = service.get_account_state()
        service.close()

        self.assertEqual(state.equity, 12_500.0)
        self.assertEqual(state.daily_pnl_pct, 0.0)
        self.assertEqual(state.drawdown_pct, 0.0)
        self.assertEqual(state.open_positions, 0)

    def test_tracks_daily_baseline_and_peak_equity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig()
            config.database.url = f"sqlite:///{Path(tmpdir) / 'account.db'}"
            provider = StubProvider(
                [
                    BrokerAccountSnapshot(
                        timestamp=datetime(2026, 3, 29, 9, 0),
                        equity=10_000.0,
                        balance=10_000.0,
                        open_positions=0,
                        trade_allowed=True,
                    ),
                    BrokerAccountSnapshot(
                        timestamp=datetime(2026, 3, 29, 11, 0),
                        equity=10_300.0,
                        balance=10_000.0,
                        open_positions=1,
                        trade_allowed=True,
                    ),
                    BrokerAccountSnapshot(
                        timestamp=datetime(2026, 3, 29, 13, 0),
                        equity=10_100.0,
                        balance=10_000.0,
                        open_positions=1,
                        trade_allowed=False,
                    ),
                ]
            )
            store = SQLiteAccountStateStore(config.database.url)
            service = AccountStateService(config, provider=provider, store=store)

            first = service.get_account_state(reference_time=datetime(2026, 3, 29, 9, 0))
            second = service.get_account_state(reference_time=datetime(2026, 3, 29, 11, 0))
            third = service.get_account_state(reference_time=datetime(2026, 3, 29, 13, 0))
            service.close()

        self.assertEqual(first.equity, 10_000.0)
        self.assertEqual(first.daily_pnl_pct, 0.0)
        self.assertEqual(first.drawdown_pct, 0.0)

        self.assertEqual(second.equity, 10_300.0)
        self.assertAlmostEqual(second.daily_pnl_pct, 0.03, places=6)
        self.assertEqual(second.drawdown_pct, 0.0)
        self.assertEqual(second.open_positions, 1)

        self.assertEqual(third.equity, 10_100.0)
        self.assertAlmostEqual(third.daily_pnl_pct, 0.01, places=6)
        self.assertAlmostEqual(third.drawdown_pct, (10_300.0 - 10_100.0) / 10_300.0, places=6)
        self.assertTrue(third.protective_mode)

    def test_new_day_resets_daily_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig()
            config.database.url = f"sqlite:///{Path(tmpdir) / 'account.db'}"
            provider = StubProvider(
                [
                    BrokerAccountSnapshot(
                        timestamp=datetime(2026, 3, 29, 23, 50),
                        equity=10_200.0,
                        balance=10_200.0,
                        open_positions=0,
                    ),
                    BrokerAccountSnapshot(
                        timestamp=datetime(2026, 3, 30, 9, 0),
                        equity=10_100.0,
                        balance=10_100.0,
                        open_positions=0,
                    ),
                ]
            )
            store = SQLiteAccountStateStore(config.database.url)
            service = AccountStateService(config, provider=provider, store=store)

            previous_day = service.get_account_state(
                reference_time=datetime(2026, 3, 29, 23, 50)
            )
            next_day = service.get_account_state(reference_time=datetime(2026, 3, 30, 9, 0))
            service.close()

        self.assertAlmostEqual(previous_day.daily_pnl_pct, 0.0, places=6)
        self.assertAlmostEqual(next_day.daily_pnl_pct, 0.0, places=6)
        self.assertAlmostEqual(next_day.drawdown_pct, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
