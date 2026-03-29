from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    TradeSegmentationSummary,
    TradePerformanceCollector,
)


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

    if slippage_perc > 0 and slippage_fixed > 0:
        raise ValueError("Use either slippage_perc or slippage_fixed, not both.")
    if evaluation_start and evaluation_end and evaluation_start > evaluation_end:
        raise ValueError("evaluation_start must be earlier than evaluation_end.")

    market_data = market_data.copy().sort_values("timestamp").reset_index(drop=True)
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
            self.next_tradeid = 1
            self.trade_context_by_id: dict[int, dict[str, Any]] = {}

        def next(self) -> None:
            current_value = float(self.broker.getvalue())
            self.equity_curve.append(current_value)

            timestamp = self.data.datetime.datetime(0).replace(tzinfo=None)
            current_date = timestamp.date()
            if self.current_session_date != current_date:
                self.current_session_date = current_date
                self.day_start_value = current_value
            self.peak_value = max(self.peak_value, current_value)

            if any(order.alive() for order in self.pending_orders):
                return

            record = self.p.records_by_timestamp.get(timestamp)
            if record is None:
                return
            if self.p.evaluation_start is not None and timestamp < self.p.evaluation_start:
                return
            if self.p.evaluation_end is not None and timestamp > self.p.evaluation_end:
                return

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

            order_plan = self.adapter.decision_to_order_plan(decision)
            if order_plan is None:
                return

            size = max(float(order_plan["position_size"]), 0.0)
            if size <= 0:
                return

            tradeid = self.next_tradeid
            self.next_tradeid += 1
            self.trade_context_by_id[tradeid] = {
                "entry_timestamp": timestamp.isoformat(),
                "entry_month": timestamp.strftime("%Y-%m"),
                "session_tag": str(record.get("session_tag", "unknown") or "unknown"),
                "strategy_name": decision.signal.strategy_name,
                "state_label": decision.state.state_label.value,
                "side": decision.signal.side.value,
                "volatility_level": (
                    decision.volatility.primary_alert.warning_level.value
                    if decision.volatility is not None
                    else "unavailable"
                ),
            }

            if order_plan["side"] == "buy":
                orders = self.buy_bracket(
                    size=size,
                    exectype=bt.Order.Market,
                    tradeid=tradeid,
                    stopprice=order_plan["stop_loss"],
                    limitprice=order_plan["take_profit"],
                )
            else:
                orders = self.sell_bracket(
                    size=size,
                    exectype=bt.Order.Market,
                    tradeid=tradeid,
                    stopprice=order_plan["stop_loss"],
                    limitprice=order_plan["take_profit"],
                )

            self.pending_orders = [order for order in orders if order is not None]
            self.orders_submitted += len(self.pending_orders)

        def notify_order(self, order: Any) -> None:
            if order.status == order.Completed:
                self.orders_completed += 1
            elif order.status == order.Cancelled:
                self.orders_cancelled += 1
            elif order.status == order.Margin:
                self.orders_margin += 1
            elif order.status == order.Rejected:
                self.orders_rejected += 1

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
                    "volatility_level": "unavailable",
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
