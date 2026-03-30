from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
import os
from pathlib import Path
from typing import Any, TypeVar


@dataclass
class StateThresholds:
    breakout_distance_min: float = 0.18
    trend_ema_spread_min: float = 0.35
    ema_slope_min: float = 0.08
    volatility_ratio_min: float = 1.15
    breakout_false_break_max: int = 2
    trend_timeframe_alignment_min: int = 2
    pullback_depth_min: float = 0.10
    pullback_depth_max: float = 0.55
    range_ema_spread_max: float = 0.12
    range_ema_slope_max: float = 0.04
    range_volatility_max: float = 1.05
    range_false_break_min: int = 2
    range_boundary_touch_min: int = 2
    range_timeframe_bias_max: int = 1
    spread_ratio_max: float = 1.50
    volatility_floor: float = 0.70
    conflict_score_max: float = 0.45


@dataclass
class RiskConfig:
    max_single_trade_risk_pct: float = 0.005
    max_daily_loss_pct: float = 0.02
    max_consecutive_losses: int = 3
    max_open_positions: int = 1
    max_spread_ratio: float = 1.40
    protective_drawdown_pct: float = 0.08
    contract_size: float = 100.0
    partial_alignment_scale: float = 0.70


@dataclass
class BreakoutStrategyConfig:
    entry_mode: str = "retest"
    stop_loss_atr_multiplier: float = 1.30
    take_profit_rr: float = 2.00
    partial_take_profit_rr: float = 1.00
    max_hold_bars: int = 20
    require_retest_confirmation: bool = True


@dataclass
class MeanReversionStrategyConfig:
    lower_range_position: float = 0.15
    upper_range_position: float = 0.85
    stop_loss_atr_multiplier: float = 1.10
    take_profit_rr: float = 1.50
    midline_target_weight: float = 1.00
    require_m1_reversal_confirmation: bool = False
    max_breakout_distance_atr: float = 0.0
    max_price_distance_to_ema20_atr: float = 0.0
    max_hold_bars: int = 12


@dataclass
class PullbackStrategyConfig:
    stop_loss_atr_multiplier: float = 1.15
    take_profit_rr: float = 1.80
    max_reference_distance_atr: float = 1.25
    max_directional_extension_atr: float = 0.0
    min_directional_distance_to_ema20_atr: float = 0.0
    min_pullback_depth: float = 0.0
    min_atr_m1: float = 0.0
    min_atr_m5: float = 0.0
    min_volatility_ratio: float = 0.0
    allowed_sides: tuple[str, ...] = ()
    min_entry_hour: int | None = None
    max_entry_hour: int | None = None
    edge_position_threshold: float = 0.80
    required_state_reasons: tuple[str, ...] = ()
    require_m1_reversal_confirmation: bool = True
    max_hold_bars: int = 16


@dataclass
class VolatilityMonitorConfig:
    horizons_minutes: tuple[int, int, int] = (5, 15, 30)
    atr_expansion_trigger: float = 1.20
    spread_ratio_trigger: float = 1.20
    tick_speed_trigger: float = 1.15
    breakout_pressure_trigger: float = 0.20
    news_proximity_minutes: int = 15
    warning_score_min: float = 0.60
    critical_score_min: float = 0.82
    warning_position_scale: float = 0.60
    info_position_scale: float = 0.85
    block_on_critical: bool = True


@dataclass
class RoutingConfig:
    enabled_strategies: tuple[str, ...] = ()
    disabled_strategies: tuple[str, ...] = ()
    allowed_sessions: tuple[str, ...] = ()
    blocked_sessions: tuple[str, ...] = ()


@dataclass
class BacktestConfig:
    initial_cash: float = 10_000.0
    commission: float = 0.00035
    slippage_perc: float = 0.00008
    slippage_fixed: float = 0.0
    fill_delay_bars: int = 1
    stop_loss_slippage_perc: float = 0.00015
    take_profit_slippage_perc: float = 0.00005
    timed_exit_slippage_perc: float = 0.00012
    reset_consecutive_losses_on_session_change: bool = True


@dataclass
class AcceptanceConfig:
    min_total_net_pnl: float = 0.0
    min_total_profit_factor: float = 1.15
    max_total_drawdown_pct: float = 0.08
    min_out_of_sample_net_pnl: float = 0.0
    min_out_of_sample_profit_factor: float = 1.00
    max_out_of_sample_drawdown_pct: float = 0.08
    min_walk_forward_windows: int = 3
    min_walk_forward_positive_window_rate: float = 0.55
    max_close_month_profit_concentration: float = 0.65
    max_session_profit_concentration: float = 0.75


@dataclass
class ReportArchiveConfig:
    enabled: bool = True
    base_dir: str = "reports/research"
    write_latest: bool = True


@dataclass
class DeploymentGateConfig:
    require_acceptance_report: bool = True
    max_acceptance_report_age_hours: float = 168.0
    require_host_check_on_live: bool = True
    require_preflight_on_live: bool = True


@dataclass
class DatabaseConfig:
    url: str = "sqlite:///var/xauusd_ai/system.db"
    auto_create: bool = True


@dataclass
class NotificationConfig:
    enabled: bool = False
    channel: str = "stdout"
    webhook_url: str | None = None
    min_warning_level: str = "warning"
    timeout_seconds: float = 5.0


@dataclass
class RuntimeConfig:
    environment: str = "dev"
    service_name: str = "xauusd-ai-system"
    log_level: str = "INFO"
    heartbeat_interval_seconds: int = 30
    poll_interval_seconds: int = 5
    starting_equity: float = 10_000.0
    dry_run: bool = True


@dataclass
class CTraderExecutionConfig:
    enabled: bool = False
    account_id: int | None = None
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    symbol: str = "XAUUSD"


@dataclass
class MT5ExecutionConfig:
    enabled: bool = False
    login: int | None = None
    password: str | None = None
    server: str | None = None
    path: str | None = None
    symbol: str = "XAUUSD"
    deviation: int = 30
    magic: int = 20260329


@dataclass
class ExecutionConfig:
    platform: str = "none"
    symbol: str = "XAUUSD"
    order_comment_prefix: str = "xauusd-ai"
    ctrader: CTraderExecutionConfig = field(default_factory=CTraderExecutionConfig)
    mt5: MT5ExecutionConfig = field(default_factory=MT5ExecutionConfig)


@dataclass
class CTraderMarketDataConfig:
    enabled: bool = False
    account_id: int | None = None
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    environment: str = "demo"
    symbol_name: str = "XAUUSD"
    symbol_id: int | None = None
    subscribe_to_spot_timestamp: bool = True


@dataclass
class MT5MarketDataConfig:
    enabled: bool = False
    login: int | None = None
    password: str | None = None
    server: str | None = None
    path: str | None = None
    symbol: str = "XAUUSD"
    timeframe: str = "M1"
    history_bars: int = 500


@dataclass
class MarketDataConfig:
    platform: str = "none"
    symbol: str = "XAUUSD"
    ctrader: CTraderMarketDataConfig = field(default_factory=CTraderMarketDataConfig)
    mt5: MT5MarketDataConfig = field(default_factory=MT5MarketDataConfig)


@dataclass
class SystemConfig:
    state_thresholds: StateThresholds = field(default_factory=StateThresholds)
    risk: RiskConfig = field(default_factory=RiskConfig)
    breakout: BreakoutStrategyConfig = field(default_factory=BreakoutStrategyConfig)
    pullback: PullbackStrategyConfig = field(default_factory=PullbackStrategyConfig)
    mean_reversion: MeanReversionStrategyConfig = field(
        default_factory=MeanReversionStrategyConfig
    )
    volatility_monitor: VolatilityMonitorConfig = field(
        default_factory=VolatilityMonitorConfig
    )
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    acceptance: AcceptanceConfig = field(default_factory=AcceptanceConfig)
    report_archive: ReportArchiveConfig = field(default_factory=ReportArchiveConfig)
    deployment_gate: DeploymentGateConfig = field(default_factory=DeploymentGateConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)


DataclassT = TypeVar("DataclassT")


def _merge_dataclass(instance: DataclassT, values: dict[str, Any]) -> DataclassT:
    valid_fields = {item.name for item in fields(instance)}

    for key, value in values.items():
        if key not in valid_fields:
            continue

        current = getattr(instance, key)
        if is_dataclass(current) and isinstance(value, dict):
            setattr(instance, key, _merge_dataclass(current, value))
        else:
            setattr(instance, key, value)

    return instance


def load_system_config(path: str | Path | None = None) -> SystemConfig:
    config = SystemConfig()
    if path is None:
        return _apply_environment_overrides(config)

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load config files. Install dependencies first."
        ) from exc

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a top-level mapping.")
    return _apply_environment_overrides(_merge_dataclass(config, raw))


def _parse_csv_env(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    items = [item.strip().lower() for item in value.split(",")]
    return tuple(item for item in items if item)


def _apply_environment_overrides(config: SystemConfig) -> SystemConfig:
    database_url = os.getenv("XAUUSD_AI_DATABASE_URL")
    if database_url:
        config.database.url = database_url

    webhook_url = os.getenv("XAUUSD_AI_WEBHOOK_URL")
    if webhook_url:
        config.notification.webhook_url = webhook_url
        config.notification.enabled = True
        config.notification.channel = "webhook"

    environment = os.getenv("XAUUSD_AI_ENV")
    if environment:
        config.runtime.environment = environment

    log_level = os.getenv("XAUUSD_AI_LOG_LEVEL")
    if log_level:
        config.runtime.log_level = log_level

    poll_interval = os.getenv("XAUUSD_AI_POLL_INTERVAL_SECONDS")
    if poll_interval:
        config.runtime.poll_interval_seconds = int(poll_interval)

    starting_equity = os.getenv("XAUUSD_AI_STARTING_EQUITY")
    if starting_equity:
        config.runtime.starting_equity = float(starting_equity)

    dry_run = os.getenv("XAUUSD_AI_DRY_RUN")
    if dry_run is not None:
        config.runtime.dry_run = dry_run.lower() in {"1", "true", "yes", "on"}

    execution_platform = os.getenv("XAUUSD_AI_EXECUTION_PLATFORM")
    if execution_platform:
        config.execution.platform = execution_platform

    market_data_platform = os.getenv("XAUUSD_AI_MARKET_DATA_PLATFORM")
    if market_data_platform:
        config.market_data.platform = market_data_platform

    ctrader_client_id = os.getenv("XAUUSD_AI_CTRADER_CLIENT_ID")
    if ctrader_client_id:
        config.execution.ctrader.client_id = ctrader_client_id
        config.execution.ctrader.enabled = True
        config.market_data.ctrader.client_id = ctrader_client_id
        config.market_data.ctrader.enabled = True

    ctrader_client_secret = os.getenv("XAUUSD_AI_CTRADER_CLIENT_SECRET")
    if ctrader_client_secret:
        config.execution.ctrader.client_secret = ctrader_client_secret
        config.execution.ctrader.enabled = True
        config.market_data.ctrader.client_secret = ctrader_client_secret
        config.market_data.ctrader.enabled = True

    ctrader_account_id = os.getenv("XAUUSD_AI_CTRADER_ACCOUNT_ID")
    if ctrader_account_id:
        config.execution.ctrader.account_id = int(ctrader_account_id)
        config.execution.ctrader.enabled = True
        config.market_data.ctrader.account_id = int(ctrader_account_id)
        config.market_data.ctrader.enabled = True

    ctrader_access_token = os.getenv("XAUUSD_AI_CTRADER_ACCESS_TOKEN")
    if ctrader_access_token:
        config.execution.ctrader.access_token = ctrader_access_token
        config.execution.ctrader.enabled = True
        config.market_data.ctrader.access_token = ctrader_access_token
        config.market_data.ctrader.enabled = True

    ctrader_environment = os.getenv("XAUUSD_AI_CTRADER_ENV")
    if ctrader_environment:
        config.market_data.ctrader.environment = ctrader_environment
        config.market_data.ctrader.enabled = True

    ctrader_symbol = os.getenv("XAUUSD_AI_CTRADER_SYMBOL")
    if ctrader_symbol:
        config.execution.ctrader.symbol = ctrader_symbol
        config.market_data.ctrader.symbol_name = ctrader_symbol
        config.execution.symbol = ctrader_symbol
        config.market_data.symbol = ctrader_symbol

    mt5_login = os.getenv("XAUUSD_AI_MT5_LOGIN")
    if mt5_login:
        config.execution.mt5.login = int(mt5_login)
        config.execution.mt5.enabled = True
        config.market_data.mt5.login = int(mt5_login)
        config.market_data.mt5.enabled = True

    mt5_password = os.getenv("XAUUSD_AI_MT5_PASSWORD")
    if mt5_password:
        config.execution.mt5.password = mt5_password
        config.execution.mt5.enabled = True
        config.market_data.mt5.password = mt5_password
        config.market_data.mt5.enabled = True

    mt5_server = os.getenv("XAUUSD_AI_MT5_SERVER")
    if mt5_server:
        config.execution.mt5.server = mt5_server
        config.execution.mt5.enabled = True
        config.market_data.mt5.server = mt5_server
        config.market_data.mt5.enabled = True

    mt5_path = os.getenv("XAUUSD_AI_MT5_PATH")
    if mt5_path:
        config.execution.mt5.path = mt5_path
        config.execution.mt5.enabled = True
        config.market_data.mt5.path = mt5_path
        config.market_data.mt5.enabled = True

    mt5_symbol = os.getenv("XAUUSD_AI_MT5_SYMBOL")
    if mt5_symbol:
        config.execution.mt5.symbol = mt5_symbol
        config.market_data.mt5.symbol = mt5_symbol
        config.execution.symbol = mt5_symbol
        config.market_data.symbol = mt5_symbol

    mt5_timeframe = os.getenv("XAUUSD_AI_MT5_TIMEFRAME")
    if mt5_timeframe:
        config.market_data.mt5.timeframe = mt5_timeframe
        config.market_data.mt5.enabled = True

    ctrader_symbol_id = os.getenv("XAUUSD_AI_CTRADER_SYMBOL_ID")
    if ctrader_symbol_id:
        config.market_data.ctrader.symbol_id = int(ctrader_symbol_id)
        config.market_data.ctrader.enabled = True

    mt5_history_bars = os.getenv("XAUUSD_AI_MT5_HISTORY_BARS")
    if mt5_history_bars:
        config.market_data.mt5.history_bars = int(mt5_history_bars)
        config.market_data.mt5.enabled = True

    mt5_deviation = os.getenv("XAUUSD_AI_MT5_DEVIATION")
    if mt5_deviation:
        config.execution.mt5.deviation = int(mt5_deviation)

    mt5_magic = os.getenv("XAUUSD_AI_MT5_MAGIC")
    if mt5_magic:
        config.execution.mt5.magic = int(mt5_magic)

    risk_max_spread_ratio = os.getenv("XAUUSD_AI_RISK_MAX_SPREAD_RATIO")
    if risk_max_spread_ratio:
        config.risk.max_spread_ratio = float(risk_max_spread_ratio)

    risk_contract_size = os.getenv("XAUUSD_AI_RISK_CONTRACT_SIZE")
    if risk_contract_size:
        config.risk.contract_size = float(risk_contract_size)

    state_spread_ratio_max = os.getenv("XAUUSD_AI_STATE_SPREAD_RATIO_MAX")
    if state_spread_ratio_max:
        config.state_thresholds.spread_ratio_max = float(state_spread_ratio_max)

    volatility_spread_ratio_trigger = os.getenv(
        "XAUUSD_AI_VOLATILITY_SPREAD_RATIO_TRIGGER"
    )
    if volatility_spread_ratio_trigger:
        config.volatility_monitor.spread_ratio_trigger = float(
            volatility_spread_ratio_trigger
        )

    enabled_strategies = _parse_csv_env(os.getenv("XAUUSD_AI_ENABLED_STRATEGIES"))
    if enabled_strategies:
        config.routing.enabled_strategies = enabled_strategies

    disabled_strategies = _parse_csv_env(os.getenv("XAUUSD_AI_DISABLED_STRATEGIES"))
    if disabled_strategies:
        config.routing.disabled_strategies = disabled_strategies

    allowed_sessions = _parse_csv_env(os.getenv("XAUUSD_AI_ALLOWED_SESSIONS"))
    if allowed_sessions:
        config.routing.allowed_sessions = allowed_sessions

    blocked_sessions = _parse_csv_env(os.getenv("XAUUSD_AI_BLOCKED_SESSIONS"))
    if blocked_sessions:
        config.routing.blocked_sessions = blocked_sessions

    if config.market_data.platform == "none" and config.execution.platform != "none":
        config.market_data.platform = config.execution.platform

    return config
