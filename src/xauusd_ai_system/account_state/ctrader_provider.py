from __future__ import annotations

from .base import AccountStateProvider, BrokerAccountSnapshot


class CTraderAccountStateProvider(AccountStateProvider):
    platform = "ctrader"

    def __init__(self, config) -> None:
        self.config = config

    def get_account_snapshot(self) -> BrokerAccountSnapshot:
        raise RuntimeError(
            "cTrader account state retrieval requires a persistent async Open API "
            "session. Complete the cTrader session manager before using live "
            "account-driven risk control on this path."
        )
