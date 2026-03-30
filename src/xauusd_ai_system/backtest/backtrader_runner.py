from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any

import pandas as pd

from ..config.schema import SystemConfig
from ..core.models import AccountState
from ..core.pipeline import TradingSystem
from ..data.csv_loader import CSVMarketDataLoader
from ..features.calculator import FeatureCalculator
from .backtrader_adapter import BacktraderAdapter
from .reporting import (
    DecisionAuditCollector,
    DecisionAuditSummary,
    NON_FEATURE_COLUMNS,
    TradeAuditSummary,
    TradeSegmentationSummary,
    TradePerformanceCollector,
)


TRADE_AUDIT_FEATURES = (
    "pullback_depth",
    "structure_intact",
    "m1_reversal_confirmed",
    "volatility_ratio",
    "spread_ratio",
    "price_distance_to_ema20",
    "vwap_deviation",
    "breakout_distance",
    "ema_slope_20",
    "tick_speed",
    "bollinger_position",
    "wick_ratio_up",
    "wick_ratio_down",
    "range_position",
    "midline_return_speed",
    "atr_m1_14",
    "atr_m5_14",
)


def _normalize_backtest_datetime(value: datetime | Any | None) -> datetime | None:
    if value is None:
        return None

    timestamp = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
    if not isinstance(timestamp, datetime):
        timestamp = pd.Timestamp(timestamp).to_pydatetime()
    if timestamp.tzinfo is not None:
        return timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    return timestamp


@dataclass
class BacktraderRunResult:
    initial_cash: float
    final_value: float
    cash: float
    net_pnl: float
    return_pct: float
    total_decisions: int
    orders_submitted: int
    orders_completed: int
    orders_cancelled: int
    orders_rejected: int
    orders_margin: int
    closed_trades: int
    won_trades: int
    lost_trades: int
    win_rate: float
    average_trade_pnl: float
    average_win_pnl: float
    average_loss_pnl: float
    payoff_ratio: float | None
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    max_drawdown_pct: float
    max_drawdown_amount: float
    average_hold_bars: float
    average_hold_minutes: float
    max_consecutive_losses: int
    commission_paid: float
    decision_summary: DecisionAuditSummary
    trade_segmentation: TradeSegmentationSummary
    trade_audit: TradeAuditSummary = field(default_factory=TradeAuditSummary)

    def as_dict(self) -> dict[str, Any]:
        return {
            "initial_cash": self.initial_cash,
            "final_value": self.final_value,
            "cash": self.cash,
            "net_pnl": self.net_pnl,
            "return_pct": self.return_pct,
            "total_decisions": self.total_decisions,
            "orders_submitted": self.orders_submitted,
            "orders_completed": self.orders_completed,
            "orders_cancelled": self.orders_cancelled,
            "orders_rejected": self.orders_rejected,
            "orders_margin": self.orders_margin,
            "closed_trades": self.closed_trades,
            "won_trades": self.won_trades,
            "lost_trades": self.lost_trades,
            "win_rate": self.win_rate,
            "average_trade_pnl": self.average_trade_pnl,
            "average_win_pnl": self.average_win_pnl,
            "average_loss_pnl": self.average_loss_pnl,
            "payoff_ratio": self.payoff_ratio,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_drawdown_amount": self.max_drawdown_amount,
            "average_hold_bars": self.average_hold_bars,
            "average_hold_minutes": self.average_hold_minutes,
            "max_consecutive_losses": self.max_consecutive_losses,
            "commission_paid": self.commission_paid,
            "decision_summary": self.decision_summary.as_dict(),
            "trade_segmentation": self.trade_segmentation.as_dict(),
            "trade_audit": self.trade_audit.as_dict(),
        }


def run_backtrader_csv(
    path: str | Path,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
) -> BacktraderRunResult:
    market_data = CSVMarketDataLoader().load(
        path,
        symbol=(
            symbol
            or config.market_data.symbol
            or config.execution.symbol
            or config.market_data.mt5.symbol
            or "XAUUSD"
        ),
    )
    return run_backtrader_market_data(
        market_data,
        config,
        symbol=symbol,
        initial_cash=initial_cash,
        commission=commission,
        slippage_perc=slippage_perc,
        slippage_fixed=slippage_fixed,
    )


def run_backtrader_market_data(
    market_data: pd.DataFrame,
    config: SystemConfig,
    *,
    symbol: str | None = None,
    initial_cash: float | None = None,
    commission: float | None = None,
    slippage_perc: float | None = None,
    slippage_fixed: float | None = None,
    evaluation_start: datetime | None = None,
    evaluation_end: datetime | None = None,
) -> BacktraderRunResult:
    try:
        import backtrader as bt
    except ImportError as exc:
        raise RuntimeError(
            "Backtrader is not installed. Install research dependencies first."
        ) from exc

    resolved_symbol = (
        symbol
        or config.market_data.symbol
        or config.execution.symbol
        or config.market_data.mt5.symbol
        or "XAUUSD"
    )
    initial_cash = (
        config.backtest.initial_cash if initial_cash is None else float(initial_cash)
    )
    commission = config.backtest.commission if commission is None else float(commission)
    slippage_perc = (
        config.backtest.slippage_perc
        if slippage_perc is None
        else float(slippage_perc)
    )
    slippage_fixed = (
        config.backtest.slippage_fixed
        if slippage_fixed is None
        else float(slippage_fixed)
    )
    evaluation_start = _normalize_backtest_datetime(evaluation_start)
    evaluation_end = _normalize_backtest_datetime(evaluation_end)

    if slippage_perc > 0 and slippage_fixed > 0:
        raise ValueError("Use either slippage_perc or slippage_fixed, not both.")
    if evaluation_start and evaluation_end and evaluation_start > evaluation_end:
        raise ValueError("evaluation_start must be earlier than evaluation_end.")

    market_data = market_data.copy().sort_values("timestamp").reset_index(drop=True)
    market_data["timestamp"] = pd.to_datetime(market_data["timestamp"], utc=True).dt.tz_localize(None)
    feature_frame = FeatureCalculator().calculate(market_data)
    records_by_timestamp = {
        row["timestamp"].to_pydatetime().replace(tzinfo=None): row
        for row in feature_frame.to_dict(orient="records")
    }

    class MarketPandasFeed(bt.feeds.PandasData):
        params = (
            ("datetime", None),
            ("open", "open"),
            ("high", "high"),
            ("low", "low"),
            ("close", "close"),
            ("volume", "volume"),
            ("openinterest", -1),
        )

    class Strategy(bt.Strategy):
        params = (
            ("config", config),
            ("records_by_timestamp", records_by_timestamp),
            ("evaluation_start", evaluation_start),
            ("evaluation_end", evaluation_end),
        )

        def __init__(self) -> None:
            self.system = TradingSystem(self.p.config)
            self.adapter = BacktraderAdapter()
            self.pending_orders: list[Any] = []
            self.pending_entry: dict[str, Any] | None = None
            self.market_exit_slippage_override_active = False
            self.total_decisions = 0
            self.decision_collector = DecisionAuditCollector()
            self.trade_collector = TradePerformanceCollector()

            self.orders_submitted = 0
            self.orders_completed = 0
            self.orders_cancelled = 0
            self.orders_rejected = 0
            self.orders_margin = 0

            self.closed_trades = 0
            self.won_trades = 0
            self.lost_trades = 0
            self.trade_pnls: list[float] = []
            self.trade_wins: list[float] = []
            self.trade_losses: list[float] = []
            self.trade_hold_bars: list[int] = []
            self.trade_hold_minutes: list[float] = []
            self.commission_paid = 0.0

            self.current_consecutive_losses = 0
            self.max_consecutive_losses = 0

            self.equity_curve: list[float] = []
            self.peak_value = float(initial_cash)
            self.day_start_value = float(initial_cash)
            self.current_session_date = None
            self.current_session_tag = None
            self.next_tradeid = 1
            self.trade_context_by_id: dict[int, dict[str, Any]] = {}
            self.active_tradeid: int | None = None
            self.active_entry_bar: int | None = None

        def next(self) -> None:
            current_value = float(self.broker.getvalue())
            self.equity_curve.append(current_value)

            timestamp = self.data.datetime.datetime(0).replace(tzinfo=None)
            current_date = timestamp.date()
            if self.current_session_date != current_date:
                self.current_session_date = current_date
                self.day_start_value = current_value
            self.peak_value = max(self.peak_value, current_value)

            self._process_forced_exit()

            if any(order.alive() for order in self.pending_orders):
                return

            record = self.p.records_by_timestamp.get(timestamp)
            if record is None:
                return
            if self.p.evaluation_start is not None and timestamp < self.p.evaluation_start:
                return
            if self.p.evaluation_end is not None and timestamp > self.p.evaluation_end:
                return

            session_tag = str(record.get("session_tag", "unknown") or "unknown")
            self._maybe_reset_consecutive_losses(session_tag)

            feature_names = set(record.keys()) - NON_FEATURE_COLUMNS
            features = {name: record.get(name) for name in feature_names}
            account_state = AccountState(
                equity=current_value,
                daily_pnl_pct=_safe_ratio(current_value - self.day_start_value, self.day_start_value),
                drawdown_pct=_safe_ratio(self.peak_value - current_value, self.peak_value),
                consecutive_losses=self.current_consecutive_losses,
                open_positions=int(self.position.size != 0),
            )
            decision = self.adapter.evaluate_bar(
                self.system,
                record,
                features=features,
                account_state=account_state,
            )
            self.total_decisions += 1
            self.decision_collector.record(record, decision)

            if self.position.size != 0:
                return

            # Delay submission by one or more bars so research fills are less idealized.
            if self.pending_entry is not None and timestamp >= self.pending_entry["submit_after"]:
                self._submit_pending_entry()
                return

            order_plan = self.adapter.decision_to_order_plan(decision)
            if order_plan is None:
                return

            size = max(float(order_plan["position_size"]), 0.0)
            if size <= 0:
                return

            tradeid = self.next_tradeid
            self.next_tradeid += 1
            trade_context = {
                "entry_timestamp": timestamp.isoformat(),
                "entry_month": timestamp.strftime("%Y-%m"),
                "session_tag": session_tag,
                "strategy_name": decision.signal.strategy_name,
                "state_label": decision.state.state_label.value,
                "side": decision.signal.side.value,
                "state_reason_codes": list(decision.state.reason_codes),
                "signal_reason": list(decision.signal.signal_reason),
                "risk_advisory": list(decision.risk.advisory),
                "volatility_level": (
                    decision.volatility.primary_alert.warning_level.value
                    if decision.volatility is not None
                    else "unavailable"
                ),
                "state_confidence_score": float(decision.state.confidence_score),
                "volatility_risk_score": (
                    float(decision.volatility.primary_alert.risk_score)
                    if decision.volatility is not None
                    else None
                ),
                "entry_price": float(decision.signal.entry_price),
                "stop_loss": float(decision.signal.stop_loss),
                "take_profit": float(decision.signal.take_profit),
                "position_size": float(order_plan["position_size"]),
                "position_scale": float(decision.risk.position_scale),
                "entry_features": _extract_trade_audit_features(record),
                "max_hold_bars": int(decision.signal.metadata.get("max_hold_bars", 0) or 0),
                "exit_reason": "pending",
                "exit_price": None,
            }
            self.pending_entry = {
                "submit_after": timestamp + pd.Timedelta(
                    minutes=max(int(self.p.config.backtest.fill_delay_bars), 1)
                ),
                "tradeid": tradeid,
                "order_plan": order_plan,
                "trade_context": trade_context,
                "size": size,
            }

        def _maybe_reset_consecutive_losses(self, session_tag: str) -> None:
            if self.current_session_tag is None:
                self.current_session_tag = session_tag
                return

            if (
                self.p.config.backtest.reset_consecutive_losses_on_session_change
                and session_tag != self.current_session_tag
            ):
                self.current_consecutive_losses = 0

            self.current_session_tag = session_tag

        def _process_forced_exit(self) -> None:
            if self.position.size == 0 or self.active_tradeid is None or self.active_entry_bar is None:
                return

            trade_context = self.trade_context_by_id.get(self.active_tradeid)
            if trade_context is None:
                return

            max_hold_bars = int(trade_context.get("max_hold_bars", 0) or 0)
            if max_hold_bars <= 0:
                return

            held_bars = len(self) - self.active_entry_bar
            if held_bars < max_hold_bars:
                return

            trade_context["exit_reason"] = "max_hold_timeout"
            self._cancel_pending_protection_orders()
            self._apply_timed_exit_slippage_override()
            self.close(tradeid=self.active_tradeid)

        def _cancel_pending_protection_orders(self) -> None:
            for order in list(self.pending_orders):
                if order.alive():
                    self.cancel(order)

        def _submit_pending_entry(self) -> None:
            if self.pending_entry is None:
                return

            pending_entry = self.pending_entry
            self.pending_entry = None
            order_plan = pending_entry["order_plan"]
            tradeid = int(pending_entry["tradeid"])
            size = float(pending_entry["size"])
            stop_loss = self._apply_directional_slippage(
                float(order_plan["stop_loss"]),
                side=str(order_plan["side"]),
                slippage_perc=float(self.p.config.backtest.stop_loss_slippage_perc),
            )
            take_profit = self._apply_directional_slippage(
                float(order_plan["take_profit"]),
                side=str(order_plan["side"]),
                slippage_perc=float(self.p.config.backtest.take_profit_slippage_perc),
            )
            self.trade_context_by_id[tradeid] = pending_entry["trade_context"]

            if order_plan["side"] == "buy":
                orders = self.buy_bracket(
                    size=size,
                    exectype=bt.Order.Market,
                    tradeid=tradeid,
                    stopprice=stop_loss,
                    limitprice=take_profit,
                )
            else:
                orders = self.sell_bracket(
                    size=size,
                    exectype=bt.Order.Market,
                    tradeid=tradeid,
                    stopprice=stop_loss,
                    limitprice=take_profit,
                )

            self.pending_orders = [order for order in orders if order is not None]
            self.orders_submitted += len(self.pending_orders)

        def _apply_timed_exit_slippage_override(self) -> None:
            timed_exit_slippage = max(
                float(self.p.config.backtest.timed_exit_slippage_perc),
                0.0,
            )
            if timed_exit_slippage <= 0 or slippage_fixed > 0:
                return
            self.broker.set_slippage_perc(timed_exit_slippage)
            self.market_exit_slippage_override_active = True

        def _restore_default_slippage(self) -> None:
            if not self.market_exit_slippage_override_active:
                return
            if slippage_perc > 0:
                self.broker.set_slippage_perc(slippage_perc)
            elif slippage_fixed > 0:
                self.broker.set_slippage_fixed(slippage_fixed)
            else:
                self.broker.set_slippage_perc(0.0)
            self.market_exit_slippage_override_active = False

        def _apply_directional_slippage(
            self,
            price: float,
            *,
            side: str,
            slippage_perc: float,
        ) -> float:
            slippage_perc = max(float(slippage_perc), 0.0)
            if slippage_perc <= 0:
                return price

            if side == "buy":
                direction = -1.0
            else:
                direction = 1.0
            return price * (1.0 + direction * slippage_perc)

        def _mark_trade_context(
            self,
            tradeid: int,
            *,
            entry_timestamp: datetime | None = None,
            entry_price: float | None = None,
            exit_reason: str | None = None,
            exit_price: float | None = None,
        ) -> None:
            trade_context = self.trade_context_by_id.get(tradeid)
            if trade_context is None:
                return

            if entry_timestamp is not None:
                trade_context["entry_timestamp"] = entry_timestamp.isoformat()
                trade_context["entry_month"] = entry_timestamp.strftime("%Y-%m")
            if entry_price is not None:
                trade_context["entry_price"] = float(entry_price)
            if exit_reason is not None:
                trade_context["exit_reason"] = exit_reason
            if exit_price is not None:
                trade_context["exit_price"] = float(exit_price)

        def notify_order(self, order: Any) -> None:
            if order.status == order.Completed:
                self.orders_completed += 1
                tradeid = int(getattr(order, "tradeid", 0) or 0)
                executed_at = self.data.datetime.datetime(0).replace(tzinfo=None)
                executed_price = float(getattr(order.executed, "price", 0.0) or 0.0)

                if (
                    self.position.size != 0
                    and getattr(order, "parent", None) is None
                    and self.active_tradeid is None
                ):
                    self.active_tradeid = tradeid
                    self.active_entry_bar = len(self)
                    self._mark_trade_context(
                        tradeid,
                        entry_timestamp=executed_at,
                        entry_price=executed_price if executed_price > 0 else None,
                        exit_reason="open",
                    )
                elif self.position.size == 0 and tradeid > 0:
                    self._mark_trade_context(
                        tradeid,
                        exit_reason=self._resolve_exit_reason(order),
                        exit_price=executed_price if executed_price > 0 else None,
                    )
                    self._restore_default_slippage()
            elif order.status == order.Cancelled:
                self.orders_cancelled += 1
                self._restore_default_slippage()
            elif order.status == order.Margin:
                self.orders_margin += 1
                self._restore_default_slippage()
            elif order.status == order.Rejected:
                self.orders_rejected += 1
                self._restore_default_slippage()

            terminal_statuses = [
                order.Completed,
                order.Cancelled,
                order.Expired,
                order.Margin,
                order.Rejected,
            ]
            if order.status in terminal_statuses:
                self.pending_orders = [
                    item for item in self.pending_orders if item.ref != order.ref
                ]

        def _resolve_exit_reason(self, order: Any) -> str:
            tradeid = int(getattr(order, "tradeid", 0) or 0)
            trade_context = self.trade_context_by_id.get(tradeid, {})
            existing_reason = str(trade_context.get("exit_reason", "") or "")
            if existing_reason and existing_reason not in {"pending", "open"}:
                return existing_reason

            exectype = getattr(order, "exectype", None)
            if exectype == bt.Order.Stop:
                return "stop_loss"
            if exectype == bt.Order.Limit:
                return "take_profit"
            if exectype == bt.Order.Market:
                return "market_exit"
            return "unknown"

        def notify_trade(self, trade: Any) -> None:
            if not trade.isclosed:
                return

            net_pnl = float(trade.pnlcomm)
            self.closed_trades += 1
            self.trade_pnls.append(net_pnl)
            self.commission_paid += float(trade.commission)
            self.trade_hold_bars.append(int(trade.barlen))

            open_dt = trade.open_datetime()
            close_dt = trade.close_datetime()
            hold_minutes = max((close_dt - open_dt).total_seconds() / 60.0, 0.0)
            self.trade_hold_minutes.append(hold_minutes)
            trade_context = self.trade_context_by_id.pop(
                int(getattr(trade, "tradeid", 0)),
                {
                    "entry_timestamp": open_dt.isoformat(),
                    "entry_month": open_dt.strftime("%Y-%m"),
                    "session_tag": "unknown",
                    "strategy_name": "unknown",
                    "state_label": "unknown",
                    "side": "unknown",
                    "state_reason_codes": [],
                    "signal_reason": [],
                    "risk_advisory": [],
                    "volatility_level": "unavailable",
                    "state_confidence_score": None,
                    "volatility_risk_score": None,
                    "entry_price": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "position_size": None,
                    "position_scale": None,
                    "entry_features": {},
                    "max_hold_bars": 0,
                    "exit_reason": "unknown",
                    "exit_price": None,
                },
            )
            self.trade_collector.record(
                trade_context,
                close_timestamp=close_dt,
                net_pnl=net_pnl,
                commission_paid=float(trade.commission),
                hold_bars=int(trade.barlen),
                hold_minutes=hold_minutes,
            )

            if net_pnl > 0:
                self.won_trades += 1
                self.trade_wins.append(net_pnl)
                self.current_consecutive_losses = 0
            elif net_pnl < 0:
                self.lost_trades += 1
                self.trade_losses.append(net_pnl)
                self.current_consecutive_losses += 1
                self.max_consecutive_losses = max(
                    self.max_consecutive_losses, self.current_consecutive_losses
                )
            else:
                self.current_consecutive_losses = 0

            self.active_tradeid = None
            self.active_entry_bar = None

        def stop(self) -> None:
            self.equity_curve.append(float(self.broker.getvalue()))

    cerebro = bt.Cerebro()
    data = market_data.copy().set_index("timestamp")
    feed = MarketPandasFeed(dataname=data)
    cerebro.adddata(feed)
    cerebro.addstrategy(Strategy)
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission, percabs=True)
    if slippage_perc > 0:
        cerebro.broker.set_slippage_perc(slippage_perc)
    elif slippage_fixed > 0:
        cerebro.broker.set_slippage_fixed(slippage_fixed)

    strategies = cerebro.run()
    strategy = strategies[0]

    final_value = float(cerebro.broker.getvalue())
    decision_summary = strategy.decision_collector.build_summary()
    trade_segmentation = strategy.trade_collector.build_summary()
    trade_audit = strategy.trade_collector.build_audit_summary()
    gross_profit = sum(strategy.trade_wins)
    gross_loss = abs(sum(strategy.trade_losses))
    return BacktraderRunResult(
        initial_cash=round(initial_cash, 2),
        final_value=round(final_value, 2),
        cash=round(float(cerebro.broker.getcash()), 2),
        net_pnl=round(final_value - initial_cash, 2),
        return_pct=round(_safe_ratio(final_value - initial_cash, initial_cash), 4),
        total_decisions=int(strategy.total_decisions),
        orders_submitted=int(strategy.orders_submitted),
        orders_completed=int(strategy.orders_completed),
        orders_cancelled=int(strategy.orders_cancelled),
        orders_rejected=int(strategy.orders_rejected),
        orders_margin=int(strategy.orders_margin),
        closed_trades=int(strategy.closed_trades),
        won_trades=int(strategy.won_trades),
        lost_trades=int(strategy.lost_trades),
        win_rate=round(
            _safe_ratio(strategy.won_trades, strategy.closed_trades),
            4,
        ),
        average_trade_pnl=round(_average(strategy.trade_pnls), 4),
        average_win_pnl=round(_average(strategy.trade_wins), 4),
        average_loss_pnl=round(_average(strategy.trade_losses), 4),
        payoff_ratio=_round_optional(_payoff_ratio(strategy.trade_wins, strategy.trade_losses)),
        gross_profit=round(gross_profit, 4),
        gross_loss=round(gross_loss, 4),
        profit_factor=_round_optional(_profit_factor(gross_profit, gross_loss)),
        max_drawdown_pct=round(_max_drawdown_pct(strategy.equity_curve), 4),
        max_drawdown_amount=round(_max_drawdown_amount(strategy.equity_curve), 4),
        average_hold_bars=round(_average(strategy.trade_hold_bars), 2),
        average_hold_minutes=round(_average(strategy.trade_hold_minutes), 2),
        max_consecutive_losses=int(strategy.max_consecutive_losses),
        commission_paid=round(strategy.commission_paid, 4),
        decision_summary=decision_summary,
        trade_segmentation=trade_segmentation,
        trade_audit=trade_audit,
    )


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return numerator / denominator


def _average(values: list[float] | list[int]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _profit_factor(gross_profit: float, gross_loss: float) -> float | None:
    if gross_profit <= 0:
        return 0.0 if gross_loss > 0 else None
    if gross_loss <= 0:
        return None
    return gross_profit / gross_loss


def _payoff_ratio(wins: list[float], losses: list[float]) -> float | None:
    if not wins or not losses:
        return None
    avg_win = _average(wins)
    avg_loss = abs(_average(losses))
    return _safe_ratio(avg_win, avg_loss)


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _max_drawdown_amount(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, peak - value)
    return max_drawdown


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_drawdown_pct = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_drawdown_pct = max(
            max_drawdown_pct,
            _safe_ratio(peak - value, peak),
        )
    return max_drawdown_pct


def _extract_trade_audit_features(record: dict[str, Any]) -> dict[str, Any]:
    return {
        name: _serialize_trade_feature(record.get(name))
        for name in TRADE_AUDIT_FEATURES
        if name in record
    }


def _serialize_trade_feature(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        return _serialize_trade_feature(value.item())
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, 6)
    if isinstance(value, str):
        return value
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(numeric):
        return None
    return round(numeric, 6)
