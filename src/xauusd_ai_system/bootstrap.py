from __future__ import annotations

from pathlib import Path

from .account_state.service import AccountStateService
from .alerts.notifier import AlertNotifier
from .config.schema import SystemConfig, load_system_config
from .core.pipeline import TradingSystem
from .execution.service import ExecutionService
from .logging_utils import configure_logging
from .market_data.service import MarketDataService
from .runtime.service import TradingRuntimeService
from .storage.sqlite_repository import SQLiteAuditRepository


def build_runtime_service(config: SystemConfig) -> TradingRuntimeService:
    configure_logging(config.runtime.log_level)
    system = TradingSystem(config)
    repository = SQLiteAuditRepository(
        config.database.url,
        auto_create=config.database.auto_create,
    )
    notifier = AlertNotifier()
    execution_service = ExecutionService(config.execution)
    return TradingRuntimeService(
        system,
        repository,
        notifier,
        config.notification,
        execution_service=execution_service,
        dry_run=config.runtime.dry_run,
    )


def build_live_runner(config: SystemConfig):
    from .runtime.live_runner import LiveTradingRunner

    runtime_service = build_runtime_service(config)
    market_data_service = MarketDataService(config.market_data)
    account_state_service = AccountStateService(config)
    return LiveTradingRunner(
        config,
        runtime_service=runtime_service,
        market_data_service=market_data_service,
        account_state_service=account_state_service,
    )


def build_preflight_runner(config: SystemConfig):
    from .preflight.factory import build_preflight_runner as _build_preflight_runner

    return _build_preflight_runner(config)


def build_host_check_runner(config: SystemConfig):
    from .preflight.mt5_host_runner import MT5HostCheckRunner

    return MT5HostCheckRunner(config)


def build_deployment_gate_runner(config: SystemConfig, **kwargs):
    from .deployment.gate import DeploymentGateRunner

    return DeploymentGateRunner(config, **kwargs)


def load_default_config() -> SystemConfig:
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "configs" / "mvp.yaml"
    try:
        return load_system_config(config_path)
    except RuntimeError:
        return load_system_config()
