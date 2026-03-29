"""XAUUSD AI quant trading system scaffold."""

from .bootstrap import (
    build_deployment_gate_runner,
    build_host_check_runner,
    build_live_runner,
    build_preflight_runner,
    build_runtime_service,
    load_default_config,
)
from .config.schema import SystemConfig, load_system_config
from .core.pipeline import TradingSystem

__all__ = [
    "SystemConfig",
    "TradingSystem",
    "build_deployment_gate_runner",
    "build_host_check_runner",
    "build_live_runner",
    "build_preflight_runner",
    "build_runtime_service",
    "load_system_config",
    "load_default_config",
]
