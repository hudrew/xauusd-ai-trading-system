from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.mt5_session import (
    ACCOUNT_INFO_RECHECK_ATTEMPTS,
    SESSION_BIND_RETRY_ATTEMPTS,
    initialize_mt5_session,
)


class FakeMT5SessionModule:
    def __init__(
        self,
        *,
        initialize_ok: bool = True,
        login_ok: bool = True,
        account_login: int = 60065894,
        account_server: str = "TradeMaxGlobal-Demo",
        account_info_sequence: list[tuple[int, str]] | None = None,
    ) -> None:
        self.initialize_ok = initialize_ok
        self.login_ok = login_ok
        self.account_login = account_login
        self.account_server = account_server
        self.account_info_sequence = list(account_info_sequence or [])
        self.initialize_calls: list[dict[str, object]] = []
        self.login_calls: list[dict[str, object]] = []
        self.shutdown_calls = 0

    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        return self.initialize_ok

    def login(self, **kwargs):
        self.login_calls.append(kwargs)
        return self.login_ok

    def account_info(self):
        if self.account_info_sequence:
            login, server = self.account_info_sequence.pop(0)
        else:
            login, server = self.account_login, self.account_server

        class AccountInfo:
            pass

        AccountInfo.login = login
        AccountInfo.server = server

        return AccountInfo()

    def shutdown(self):
        self.shutdown_calls += 1
        return None

    def last_error(self):
        return (0, "OK")


class MT5SessionTests(unittest.TestCase):
    def test_initialize_session_logs_into_expected_account(self) -> None:
        fake_mt5 = FakeMT5SessionModule()

        initialize_mt5_session(
            fake_mt5,
            path=None,
            login=60065894,
            password="secret",
            server="TradeMaxGlobal-Demo",
        )

        self.assertEqual(len(fake_mt5.initialize_calls), 1)
        self.assertEqual(len(fake_mt5.login_calls), 1)
        self.assertEqual(fake_mt5.login_calls[0]["login"], 60065894)
        self.assertEqual(fake_mt5.login_calls[0]["server"], "TradeMaxGlobal-Demo")

    def test_initialize_session_raises_when_login_fails(self) -> None:
        fake_mt5 = FakeMT5SessionModule(login_ok=False)

        with self.assertRaisesRegex(RuntimeError, "MT5 login failed"):
            initialize_mt5_session(
                fake_mt5,
                path=None,
                login=60065894,
                password="secret",
                server="TradeMaxGlobal-Demo",
            )

        self.assertEqual(fake_mt5.shutdown_calls, SESSION_BIND_RETRY_ATTEMPTS)

    def test_initialize_session_raises_when_terminal_stays_on_wrong_account(self) -> None:
        fake_mt5 = FakeMT5SessionModule(
            account_login=50182922,
            account_server="TradeMaxGlobal-Live",
        )

        with self.assertRaisesRegex(RuntimeError, "unexpected account"):
            initialize_mt5_session(
                fake_mt5,
                path=None,
                login=60065894,
                password="secret",
                server="TradeMaxGlobal-Demo",
            )

        self.assertEqual(fake_mt5.shutdown_calls, SESSION_BIND_RETRY_ATTEMPTS)

    def test_initialize_session_rechecks_account_binding_before_failing(self) -> None:
        fake_mt5 = FakeMT5SessionModule(
            account_info_sequence=[
                (50182922, "TradeMaxGlobal-Live"),
                (60065894, "TradeMaxGlobal-Demo"),
            ]
        )

        initialize_mt5_session(
            fake_mt5,
            path=None,
            login=60065894,
            password="secret",
            server="TradeMaxGlobal-Demo",
        )

        self.assertEqual(fake_mt5.shutdown_calls, 0)
        self.assertEqual(len(fake_mt5.login_calls), 1)

    def test_initialize_session_retries_when_account_info_is_unbound(self) -> None:
        fake_mt5 = FakeMT5SessionModule(
            account_info_sequence=[
                (0, ""),
                (60065894, "TradeMaxGlobal-Demo"),
            ]
        )

        initialize_mt5_session(
            fake_mt5,
            path=None,
            login=60065894,
            password="secret",
            server="TradeMaxGlobal-Demo",
        )

        self.assertEqual(fake_mt5.shutdown_calls, 0)
        self.assertEqual(len(fake_mt5.login_calls), 1)

    def test_initialize_session_raises_when_account_info_never_binds(self) -> None:
        fake_mt5 = FakeMT5SessionModule(
            account_info_sequence=[
                (0, "")
            ] * (SESSION_BIND_RETRY_ATTEMPTS * ACCOUNT_INFO_RECHECK_ATTEMPTS),
        )

        with self.assertRaisesRegex(RuntimeError, "returned no login"):
            initialize_mt5_session(
                fake_mt5,
                path=None,
                login=60065894,
                password="secret",
                server="TradeMaxGlobal-Demo",
            )

        self.assertEqual(fake_mt5.shutdown_calls, SESSION_BIND_RETRY_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
