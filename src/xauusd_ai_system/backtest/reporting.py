from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from ..core.models import TradingDecision

NON_FEATURE_COLUMNS = {
    "timestamp",
    "symbol",
    "bid",
    "ask",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "session_tag",
    "news_flag",
    "minutes_to_event",
    "minutes_from_event",
    "spread",
}


@dataclass
class DecisionAuditSummary:
    rows_processed: int
    signals_generated: int
    trades_allowed: int
    blocked_trades: int
    no_signal_rows: int
    high_volatility_alerts: int
    signal_rate: float
    trade_allow_rate: float
    blocked_signal_rate: float
    high_volatility_alert_rate: float
    states_by_label: dict[str, int]
    signals_by_strategy: dict[str, int]
    signals_by_side: dict[str, int]
    blocked_reasons: dict[str, int]
    risk_advisories: dict[str, int]
    volatility_levels: dict[str, int]
    sessions_by_count: dict[str, int]
    states_by_session: dict[str, dict[str, int]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows_processed": self.rows_processed,
            "signals_generated": self.signals_generated,
            "trades_allowed": self.trades_allowed,
            "blocked_trades": self.blocked_trades,
            "no_signal_rows": self.no_signal_rows,
            "high_volatility_alerts": self.high_volatility_alerts,
            "signal_rate": self.signal_rate,
            "trade_allow_rate": self.trade_allow_rate,
            "blocked_signal_rate": self.blocked_signal_rate,
            "high_volatility_alert_rate": self.high_volatility_alert_rate,
            "states_by_label": dict(self.states_by_label),
            "signals_by_strategy": dict(self.signals_by_strategy),
            "signals_by_side": dict(self.signals_by_side),
            "blocked_reasons": dict(self.blocked_reasons),
            "risk_advisories": dict(self.risk_advisories),
            "volatility_levels": dict(self.volatility_levels),
            "sessions_by_count": dict(self.sessions_by_count),
            "states_by_session": {
                session: dict(states)
                for session, states in self.states_by_session.items()
            },
        }


class DecisionAuditCollector:
    def __init__(self) -> None:
        self.rows_processed = 0
        self.signals_generated = 0
        self.trades_allowed = 0
        self.blocked_trades = 0
        self.high_volatility_alerts = 0
        self.states_by_label: Counter[str] = Counter()
        self.signals_by_strategy: Counter[str] = Counter()
        self.signals_by_side: Counter[str] = Counter()
        self.blocked_reasons: Counter[str] = Counter()
        self.risk_advisories: Counter[str] = Counter()
        self.volatility_levels: Counter[str] = Counter()
        self.sessions_by_count: Counter[str] = Counter()
        self.states_by_session: dict[str, Counter[str]] = defaultdict(Counter)

    def record(self, record: Mapping[str, Any], decision: TradingDecision) -> None:
        self.rows_processed += 1
        session_tag = str(record.get("session_tag", "unknown") or "unknown")
        state_label = decision.state.state_label.value
        self.states_by_label[state_label] += 1
        self.sessions_by_count[session_tag] += 1
        self.states_by_session[session_tag][state_label] += 1

        for advisory in decision.risk.advisory:
            self.risk_advisories[advisory] += 1

        if decision.volatility and decision.volatility.primary_alert.warning_level.value in {
            "warning",
            "critical",
        }:
            self.high_volatility_alerts += 1

        if decision.volatility is not None:
            self.volatility_levels[decision.volatility.primary_alert.warning_level.value] += 1
        else:
            self.volatility_levels["unavailable"] += 1

        if decision.signal is None:
            return

        self.signals_generated += 1
        self.signals_by_strategy[decision.signal.strategy_name] += 1
        self.signals_by_side[decision.signal.side.value] += 1
        if decision.risk.allowed:
            self.trades_allowed += 1
            return

        self.blocked_trades += 1
        for reason in decision.risk.risk_reason:
            self.blocked_reasons[reason] += 1

    def build_summary(self) -> DecisionAuditSummary:
        no_signal_rows = self.rows_processed - self.signals_generated
        return DecisionAuditSummary(
            rows_processed=self.rows_processed,
            signals_generated=self.signals_generated,
            trades_allowed=self.trades_allowed,
            blocked_trades=self.blocked_trades,
            no_signal_rows=no_signal_rows,
            high_volatility_alerts=self.high_volatility_alerts,
            signal_rate=self._ratio(self.signals_generated, self.rows_processed),
            trade_allow_rate=self._ratio(self.trades_allowed, self.signals_generated),
            blocked_signal_rate=self._ratio(self.blocked_trades, self.signals_generated),
            high_volatility_alert_rate=self._ratio(
                self.high_volatility_alerts, self.rows_processed
            ),
            states_by_label=self._sorted_counts(self.states_by_label),
            signals_by_strategy=self._sorted_counts(self.signals_by_strategy),
            signals_by_side=self._sorted_counts(self.signals_by_side),
            blocked_reasons=self._sorted_counts(self.blocked_reasons),
            risk_advisories=self._sorted_counts(self.risk_advisories),
            volatility_levels=self._sorted_counts(self.volatility_levels),
            sessions_by_count=self._sorted_counts(self.sessions_by_count),
            states_by_session={
                session: self._sorted_counts(state_counts)
                for session, state_counts in sorted(self.states_by_session.items())
            },
        )

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)

    @staticmethod
    def _sorted_counts(counter: Counter[str]) -> dict[str, int]:
        return {
            key: counter[key]
            for key in sorted(counter, key=lambda item: (-counter[item], item))
        }


@dataclass
class TradeSegmentSummary:
    closed_trades: int
    won_trades: int
    lost_trades: int
    win_rate: float
    net_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    average_trade_pnl: float
    average_win_pnl: float
    average_loss_pnl: float
    average_hold_bars: float
    average_hold_minutes: float
    commission_paid: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "closed_trades": self.closed_trades,
            "won_trades": self.won_trades,
            "lost_trades": self.lost_trades,
            "win_rate": self.win_rate,
            "net_pnl": self.net_pnl,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "average_trade_pnl": self.average_trade_pnl,
            "average_win_pnl": self.average_win_pnl,
            "average_loss_pnl": self.average_loss_pnl,
            "average_hold_bars": self.average_hold_bars,
            "average_hold_minutes": self.average_hold_minutes,
            "commission_paid": self.commission_paid,
        }


@dataclass
class TradeSegmentationSummary:
    performance_by_close_month: dict[str, TradeSegmentSummary]
    performance_by_strategy: dict[str, TradeSegmentSummary]
    performance_by_state: dict[str, TradeSegmentSummary]
    performance_by_session: dict[str, TradeSegmentSummary]
    performance_by_side: dict[str, TradeSegmentSummary]
    performance_by_exit_reason: dict[str, TradeSegmentSummary]

    def as_dict(self) -> dict[str, Any]:
        return {
            "performance_by_close_month": {
                key: summary.as_dict()
                for key, summary in self.performance_by_close_month.items()
            },
            "performance_by_strategy": {
                key: summary.as_dict()
                for key, summary in self.performance_by_strategy.items()
            },
            "performance_by_state": {
                key: summary.as_dict()
                for key, summary in self.performance_by_state.items()
            },
            "performance_by_session": {
                key: summary.as_dict()
                for key, summary in self.performance_by_session.items()
            },
            "performance_by_side": {
                key: summary.as_dict()
                for key, summary in self.performance_by_side.items()
            },
            "performance_by_exit_reason": {
                key: summary.as_dict()
                for key, summary in self.performance_by_exit_reason.items()
            },
        }


@dataclass
class TradeAuditRecord:
    entry_timestamp: str
    close_timestamp: str
    entry_month: str
    close_month: str
    session_tag: str
    strategy_name: str
    state_label: str
    side: str
    volatility_level: str
    state_reason_codes: list[str] = field(default_factory=list)
    signal_reason: list[str] = field(default_factory=list)
    risk_advisory: list[str] = field(default_factory=list)
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = None
    position_scale: float | None = None
    state_confidence_score: float | None = None
    volatility_risk_score: float | None = None
    net_pnl: float = 0.0
    commission_paid: float = 0.0
    hold_bars: int = 0
    hold_minutes: float = 0.0
    outcome: str = "flat"
    exit_reason: str = "unknown"
    exit_price: float | None = None
    entry_features: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "entry_timestamp": self.entry_timestamp,
            "close_timestamp": self.close_timestamp,
            "entry_month": self.entry_month,
            "close_month": self.close_month,
            "session_tag": self.session_tag,
            "strategy_name": self.strategy_name,
            "state_label": self.state_label,
            "side": self.side,
            "volatility_level": self.volatility_level,
            "state_reason_codes": list(self.state_reason_codes),
            "signal_reason": list(self.signal_reason),
            "risk_advisory": list(self.risk_advisory),
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "position_scale": self.position_scale,
            "state_confidence_score": self.state_confidence_score,
            "volatility_risk_score": self.volatility_risk_score,
            "net_pnl": self.net_pnl,
            "commission_paid": self.commission_paid,
            "hold_bars": self.hold_bars,
            "hold_minutes": self.hold_minutes,
            "outcome": self.outcome,
            "exit_reason": self.exit_reason,
            "exit_price": self.exit_price,
            "entry_features": dict(self.entry_features),
        }


@dataclass
class TradeAuditSummary:
    records_count: int = 0
    latest_closed: list[TradeAuditRecord] = field(default_factory=list)
    worst_losses: list[TradeAuditRecord] = field(default_factory=list)
    best_wins: list[TradeAuditRecord] = field(default_factory=list)
    all_closed: list[TradeAuditRecord] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "records_count": self.records_count,
            "latest_closed": [record.as_dict() for record in self.latest_closed],
            "worst_losses": [record.as_dict() for record in self.worst_losses],
            "best_wins": [record.as_dict() for record in self.best_wins],
            "all_closed": [record.as_dict() for record in self.all_closed],
        }


@dataclass
class _TradeBucket:
    closed_trades: int = 0
    won_trades: int = 0
    lost_trades: int = 0
    net_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    win_pnl_total: float = 0.0
    loss_pnl_total: float = 0.0
    hold_bars_total: int = 0
    hold_minutes_total: float = 0.0
    commission_paid: float = 0.0

    def record(
        self,
        *,
        net_pnl: float,
        commission_paid: float,
        hold_bars: int,
        hold_minutes: float,
    ) -> None:
        self.closed_trades += 1
        self.net_pnl += net_pnl
        self.hold_bars_total += hold_bars
        self.hold_minutes_total += hold_minutes
        self.commission_paid += commission_paid

        if net_pnl > 0:
            self.won_trades += 1
            self.gross_profit += net_pnl
            self.win_pnl_total += net_pnl
        elif net_pnl < 0:
            self.lost_trades += 1
            self.gross_loss += abs(net_pnl)
            self.loss_pnl_total += net_pnl


class TradePerformanceCollector:
    def __init__(self) -> None:
        self.by_close_month: dict[str, _TradeBucket] = defaultdict(_TradeBucket)
        self.by_strategy: dict[str, _TradeBucket] = defaultdict(_TradeBucket)
        self.by_state: dict[str, _TradeBucket] = defaultdict(_TradeBucket)
        self.by_session: dict[str, _TradeBucket] = defaultdict(_TradeBucket)
        self.by_side: dict[str, _TradeBucket] = defaultdict(_TradeBucket)
        self.by_exit_reason: dict[str, _TradeBucket] = defaultdict(_TradeBucket)
        self.trade_records: list[TradeAuditRecord] = []

    def record(
        self,
        trade_context: Mapping[str, Any],
        *,
        close_timestamp: datetime,
        net_pnl: float,
        commission_paid: float,
        hold_bars: int,
        hold_minutes: float,
    ) -> None:
        close_month = close_timestamp.strftime("%Y-%m")
        strategy_name = str(trade_context.get("strategy_name", "unknown") or "unknown")
        state_label = str(trade_context.get("state_label", "unknown") or "unknown")
        session_tag = str(trade_context.get("session_tag", "unknown") or "unknown")
        side = str(trade_context.get("side", "unknown") or "unknown")
        exit_reason = str(trade_context.get("exit_reason", "unknown") or "unknown")

        payload = {
            "net_pnl": float(net_pnl),
            "commission_paid": float(commission_paid),
            "hold_bars": int(hold_bars),
            "hold_minutes": float(hold_minutes),
        }
        self.by_close_month[close_month].record(**payload)
        self.by_strategy[strategy_name].record(**payload)
        self.by_state[state_label].record(**payload)
        self.by_session[session_tag].record(**payload)
        self.by_side[side].record(**payload)
        self.by_exit_reason[exit_reason].record(**payload)
        self.trade_records.append(
            TradeAuditRecord(
                entry_timestamp=str(
                    trade_context.get("entry_timestamp", close_timestamp.isoformat())
                ),
                close_timestamp=close_timestamp.isoformat(),
                entry_month=str(
                    trade_context.get("entry_month", close_timestamp.strftime("%Y-%m"))
                ),
                close_month=close_month,
                session_tag=session_tag,
                strategy_name=strategy_name,
                state_label=state_label,
                side=side,
                volatility_level=str(
                    trade_context.get("volatility_level", "unavailable") or "unavailable"
                ),
                state_reason_codes=[
                    str(item)
                    for item in trade_context.get("state_reason_codes", []) or []
                ],
                signal_reason=[
                    str(item) for item in trade_context.get("signal_reason", []) or []
                ],
                risk_advisory=[
                    str(item) for item in trade_context.get("risk_advisory", []) or []
                ],
                entry_price=_optional_float(trade_context.get("entry_price")),
                stop_loss=_optional_float(trade_context.get("stop_loss")),
                take_profit=_optional_float(trade_context.get("take_profit")),
                position_size=_optional_float(trade_context.get("position_size")),
                position_scale=_optional_float(trade_context.get("position_scale")),
                state_confidence_score=_optional_float(
                    trade_context.get("state_confidence_score")
                ),
                volatility_risk_score=_optional_float(
                    trade_context.get("volatility_risk_score")
                ),
                net_pnl=round(float(net_pnl), 4),
                commission_paid=round(float(commission_paid), 4),
                hold_bars=int(hold_bars),
                hold_minutes=round(float(hold_minutes), 2),
                outcome=_trade_outcome(net_pnl),
                exit_reason=str(trade_context.get("exit_reason", "unknown") or "unknown"),
                exit_price=_optional_float(trade_context.get("exit_price")),
                entry_features={
                    str(key): value
                    for key, value in (
                        trade_context.get("entry_features", {}) or {}
                    ).items()
                },
            )
        )

    def build_summary(self) -> TradeSegmentationSummary:
        return TradeSegmentationSummary(
            performance_by_close_month=self._build_bucket_map(self.by_close_month),
            performance_by_strategy=self._build_bucket_map(self.by_strategy),
            performance_by_state=self._build_bucket_map(self.by_state),
            performance_by_session=self._build_bucket_map(self.by_session),
            performance_by_side=self._build_bucket_map(self.by_side),
            performance_by_exit_reason=self._build_bucket_map(self.by_exit_reason),
        )

    def build_audit_summary(self, *, limit: int = 5) -> TradeAuditSummary:
        latest_closed = list(reversed(self.trade_records[-limit:]))
        worst_losses = sorted(
            (record for record in self.trade_records if record.net_pnl < 0),
            key=lambda item: item.net_pnl,
        )[:limit]
        best_wins = sorted(
            (record for record in self.trade_records if record.net_pnl > 0),
            key=lambda item: item.net_pnl,
            reverse=True,
        )[:limit]
        return TradeAuditSummary(
            records_count=len(self.trade_records),
            latest_closed=latest_closed,
            worst_losses=worst_losses,
            best_wins=best_wins,
            all_closed=list(self.trade_records),
        )

    def _build_bucket_map(
        self,
        buckets: Mapping[str, _TradeBucket],
    ) -> dict[str, TradeSegmentSummary]:
        summaries = {
            key: self._build_bucket_summary(bucket)
            for key, bucket in buckets.items()
        }
        return {
            key: summaries[key]
            for key in sorted(
                summaries,
                key=lambda item: (-abs(summaries[item].net_pnl), item),
            )
        }

    @staticmethod
    def _build_bucket_summary(bucket: _TradeBucket) -> TradeSegmentSummary:
        return TradeSegmentSummary(
            closed_trades=bucket.closed_trades,
            won_trades=bucket.won_trades,
            lost_trades=bucket.lost_trades,
            win_rate=_ratio(bucket.won_trades, bucket.closed_trades),
            net_pnl=round(bucket.net_pnl, 4),
            gross_profit=round(bucket.gross_profit, 4),
            gross_loss=round(bucket.gross_loss, 4),
            profit_factor=_round_optional(_profit_factor(bucket.gross_profit, bucket.gross_loss)),
            average_trade_pnl=round(_ratio(bucket.net_pnl, bucket.closed_trades), 4),
            average_win_pnl=round(_ratio(bucket.win_pnl_total, bucket.won_trades), 4),
            average_loss_pnl=round(_ratio(bucket.loss_pnl_total, bucket.lost_trades), 4),
            average_hold_bars=round(_ratio(bucket.hold_bars_total, bucket.closed_trades), 2),
            average_hold_minutes=round(
                _ratio(bucket.hold_minutes_total, bucket.closed_trades),
                2,
            ),
            commission_paid=round(bucket.commission_paid, 4),
        )


def _ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return numerator / denominator


def _profit_factor(gross_profit: float, gross_loss: float) -> float | None:
    if gross_profit <= 0:
        return 0.0 if gross_loss > 0 else None
    if gross_loss <= 0:
        return None
    return gross_profit / gross_loss


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _trade_outcome(net_pnl: float) -> str:
    if net_pnl > 0:
        return "win"
    if net_pnl < 0:
        return "loss"
    return "flat"
