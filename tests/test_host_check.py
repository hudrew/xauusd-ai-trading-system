from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.config.schema import SystemConfig
from xauusd_ai_system.preflight.mt5_host_runner import MT5HostCheckRunner


class MT5HostCheckRunnerTests(unittest.TestCase):
    def test_host_ready_on_windows_x64_with_module_and_credentials(self) -> None:
        config = SystemConfig()
        env = {
            "XAUUSD_AI_MT5_LOGIN": "123456",
            "XAUUSD_AI_MT5_PASSWORD": "secret",
            "XAUUSD_AI_MT5_SERVER": "Broker-Server",
            "XAUUSD_AI_MT5_PATH": "C:/Program Files/MetaTrader 5/terminal64.exe",
        }
        runner = MT5HostCheckRunner(
            config,
            env=env,
            system_name="Windows",
            machine="AMD64",
            python_version=(3, 10, 11),
            module_available=lambda name: True,
            path_exists=lambda path: True,
        )

        report = runner.run()

        self.assertTrue(report.ready)
        self.assertEqual(report.platform, "mt5-host")
        self.assertTrue(all(item.passed for item in report.checks))

    def test_host_not_ready_on_macos_arm_without_module(self) -> None:
        config = SystemConfig()
        runner = MT5HostCheckRunner(
            config,
            env={},
            system_name="Darwin",
            machine="arm64",
            python_version=(3, 10, 0),
            module_available=lambda name: False,
            path_exists=lambda path: False,
        )

        report = runner.run()

        self.assertFalse(report.ready)
        failed_names = {item.name for item in report.checks if not item.passed}
        self.assertIn("official_host_platform", failed_names)
        self.assertIn("host_architecture", failed_names)
        self.assertIn("metatrader5_module", failed_names)
        self.assertIn("mt5_terminal_path", failed_names)
        self.assertIn("mt5_credentials", failed_names)

    def test_python_version_below_minimum_fails(self) -> None:
        config = SystemConfig()
        runner = MT5HostCheckRunner(
            config,
            env={
                "XAUUSD_AI_MT5_LOGIN": "123456",
                "XAUUSD_AI_MT5_PASSWORD": "secret",
                "XAUUSD_AI_MT5_SERVER": "Broker-Server",
                "XAUUSD_AI_MT5_PATH": "C:/terminal64.exe",
            },
            system_name="Windows",
            machine="AMD64",
            python_version=(3, 9, 18),
            module_available=lambda name: True,
            path_exists=lambda path: True,
        )

        report = runner.run()

        self.assertFalse(report.ready)
        version_check = next(item for item in report.checks if item.name == "python_version")
        self.assertFalse(version_check.passed)


if __name__ == "__main__":
    unittest.main()
