from __future__ import annotations

from ..config.schema import SystemConfig
from .mt5_runner import MT5PreflightRunner


def build_preflight_runner(config: SystemConfig):
    execution_platform = config.execution.platform.lower()
    market_data_platform = config.market_data.platform.lower()
    platform = execution_platform if execution_platform != "none" else market_data_platform

    if platform == "mt5":
        return MT5PreflightRunner(config)
    if platform == "ctrader":
        raise RuntimeError(
            "cTrader preflight is not ready yet. Complete the async session manager first."
        )
    raise RuntimeError("No supported live platform configured for preflight.")
