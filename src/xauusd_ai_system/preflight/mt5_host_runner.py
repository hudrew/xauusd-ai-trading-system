from __future__ import annotations

import importlib.util
from pathlib import Path
import platform
import sys
from typing import Callable, Mapping

from ..config.schema import SystemConfig
from .base import PreflightCheck, PreflightReport


class MT5HostCheckRunner:
    def __init__(
        self,
        config: SystemConfig,
        *,
        env: Mapping[str, str] | None = None,
        system_name: str | None = None,
        machine: str | None = None,
        python_version: tuple[int, int, int] | None = None,
        module_available: Callable[[str], bool] | None = None,
        path_exists: Callable[[str], bool] | None = None,
    ) -> None:
        self.config = config
        self.env = env
        self.system_name = system_name
        self.machine = machine
        self.python_version = python_version
        self.module_available = module_available
        self.path_exists = path_exists

    def run(self) -> PreflightReport:
        system_name = (self.system_name or platform.system()).strip()
        machine = (self.machine or platform.machine()).strip()
        python_version = self.python_version or sys.version_info[:3]
        env = self.env or {}

        checks: list[PreflightCheck] = []

        is_windows = system_name.lower() == "windows"
        checks.append(
            PreflightCheck(
                name="official_host_platform",
                passed=is_windows,
                detail=(
                    f"Host platform is {system_name}."
                    if is_windows
                    else (
                        f"Host platform is {system_name}. For MT5 execution, use a "
                        "Windows execution host to align with the official Python "
                        "integration path."
                    )
                ),
                metadata={"system": system_name},
            )
        )

        normalized_machine = machine.lower()
        is_x64 = normalized_machine in {"amd64", "x86_64"}
        checks.append(
            PreflightCheck(
                name="host_architecture",
                passed=is_x64,
                detail=(
                    f"Host architecture is {machine}."
                    if is_x64
                    else (
                        f"Host architecture is {machine}. Prefer an x64 execution host "
                        "for MT5 live deployment."
                    )
                ),
                metadata={"machine": machine},
            )
        )

        python_ok = python_version >= (3, 10, 0)
        checks.append(
            PreflightCheck(
                name="python_version",
                passed=python_ok,
                detail=(
                    f"Python version is {python_version[0]}.{python_version[1]}.{python_version[2]}."
                    if python_ok
                    else (
                        f"Python version is {python_version[0]}.{python_version[1]}.{python_version[2]}. "
                        "The project requires Python 3.10 or newer."
                    )
                ),
                metadata={"version": ".".join(str(item) for item in python_version)},
            )
        )

        mt5_available = self._module_available("MetaTrader5")
        checks.append(
            PreflightCheck(
                name="metatrader5_module",
                passed=mt5_available,
                detail=(
                    "MetaTrader5 module is importable."
                    if mt5_available
                    else "MetaTrader5 module is not importable in this Python environment."
                ),
            )
        )

        terminal_path = env.get("XAUUSD_AI_MT5_PATH") or self._config_terminal_path()
        terminal_path_ok = bool(terminal_path) and self._path_exists(str(terminal_path))
        checks.append(
            PreflightCheck(
                name="mt5_terminal_path",
                passed=terminal_path_ok,
                detail=(
                    f"MT5 terminal path is available: {terminal_path}."
                    if terminal_path_ok
                    else (
                        "MT5 terminal path is missing or does not exist. Set "
                        "`XAUUSD_AI_MT5_PATH` or configure `execution.mt5.path`."
                    )
                ),
                metadata={"path": terminal_path},
            )
        )

        credentials_present = all(
            [
                env.get("XAUUSD_AI_MT5_LOGIN") or self._config_login(),
                env.get("XAUUSD_AI_MT5_PASSWORD") or self._config_password(),
                env.get("XAUUSD_AI_MT5_SERVER") or self._config_server(),
            ]
        )
        checks.append(
            PreflightCheck(
                name="mt5_credentials",
                passed=credentials_present,
                detail=(
                    "MT5 login, password, and server are configured."
                    if credentials_present
                    else (
                        "MT5 credentials are incomplete. Provide login, password, and "
                        "server through env vars or config."
                    )
                ),
            )
        )

        ready = all(item.passed or item.severity == "info" for item in checks)
        return PreflightReport(platform="mt5-host", ready=ready, checks=checks)

    def _module_available(self, name: str) -> bool:
        if self.module_available is not None:
            return self.module_available(name)
        return importlib.util.find_spec(name) is not None

    def _path_exists(self, path: str) -> bool:
        if self.path_exists is not None:
            return self.path_exists(path)
        return Path(path).exists()

    def _config_terminal_path(self) -> str | None:
        return self._first_non_empty(
            self.config.execution.mt5.path,
            self.config.market_data.mt5.path,
        )

    def _config_login(self) -> int | None:
        return self._first_non_empty(
            self.config.execution.mt5.login,
            self.config.market_data.mt5.login,
        )

    def _config_password(self) -> str | None:
        return self._first_non_empty(
            self.config.execution.mt5.password,
            self.config.market_data.mt5.password,
        )

    def _config_server(self) -> str | None:
        return self._first_non_empty(
            self.config.execution.mt5.server,
            self.config.market_data.mt5.server,
        )

    @staticmethod
    def _first_non_empty(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None
