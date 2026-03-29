from __future__ import annotations

from datetime import datetime, timezone

from ..config.schema import SystemConfig
from ..core.models import AccountState
from ..storage.account_state_store import SQLiteAccountStateStore
from .base import AccountStateProvider
from .factory import build_account_state_provider


class AccountStateService:
    def __init__(
        self,
        config: SystemConfig,
        provider: AccountStateProvider | None = None,
        store: SQLiteAccountStateStore | None = None,
    ) -> None:
        self.config = config
        self.provider = provider or build_account_state_provider(config)
        self._store = store

    def get_account_state(self, reference_time: datetime | None = None) -> AccountState:
        if self.provider is None:
            return AccountState(equity=self.config.runtime.starting_equity)

        snapshot = self.provider.get_account_snapshot()
        effective_time = reference_time or snapshot.timestamp
        day_key = effective_time.date().isoformat()

        baseline_seed = (
            snapshot.balance
            if snapshot.balance not in (None, 0.0)
            else self.config.runtime.starting_equity or snapshot.equity
        )
        store = self._ensure_store()
        baseline = store.get_or_create(day_key, fallback_equity=float(baseline_seed))

        peak_equity = max(baseline.peak_equity, snapshot.equity)
        if peak_equity != baseline.peak_equity:
            baseline.peak_equity = peak_equity
            baseline.updated_at = datetime.now(timezone.utc)
            store.save(baseline)

        daily_pnl_pct = self._safe_ratio(
            snapshot.equity - baseline.start_equity,
            baseline.start_equity,
        )
        drawdown_pct = max(
            self._safe_ratio(peak_equity - snapshot.equity, peak_equity),
            0.0,
        )
        return AccountState(
            equity=round(snapshot.equity, 2),
            daily_pnl_pct=round(daily_pnl_pct, 6),
            drawdown_pct=round(drawdown_pct, 6),
            consecutive_losses=0,
            open_positions=snapshot.open_positions,
            protective_mode=not snapshot.trade_allowed,
        )

    def close(self) -> None:
        if self._store is not None:
            self._store.close()

    def _ensure_store(self) -> SQLiteAccountStateStore:
        if self._store is None:
            self._store = SQLiteAccountStateStore(
                self.config.database.url,
                auto_create=self.config.database.auto_create,
            )
        return self._store

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        if denominator == 0:
            return 0.0
        return numerator / denominator
