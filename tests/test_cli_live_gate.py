from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xauusd_ai_system.cli import main


class StubDecision:
    def as_dict(self) -> dict[str, bool]:
        return {"ok": True}


class StubLiveRunner:
    def __init__(self) -> None:
        self.run_once_called = False
        self.run_loop_calls: list[int | None] = []
        self.shutdown_called = False

    def run_once(self):
        self.run_once_called = True
        return StubDecision()

    def run_loop(self, iterations=None):
        self.run_loop_calls.append(iterations)

    def shutdown(self):
        self.shutdown_called = True


class LiveCliGateTests(unittest.TestCase):
    def test_live_once_requires_deploy_gate_in_live_mode(self) -> None:
        config_text = textwrap.dedent(
            """
            runtime:
              dry_run: false
            market_data:
              platform: mt5
            execution:
              platform: mt5
            """
        )
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(config_text)
            config_path = handle.name

        runner = StubLiveRunner()
        buffer = StringIO()
        try:
            with patch("xauusd_ai_system.cli._run_deploy_gate", return_value=True) as gate_mock:
                with patch("xauusd_ai_system.bootstrap.build_live_runner", return_value=runner):
                    with patch.object(
                        sys,
                        "argv",
                        ["xauusd_ai_system.cli", "--config", config_path, "live-once"],
                    ):
                        with redirect_stdout(buffer):
                            main()
        finally:
            Path(config_path).unlink(missing_ok=True)

        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])
        gate_mock.assert_called_once()
        self.assertTrue(runner.run_once_called)
        self.assertTrue(runner.shutdown_called)

    def test_live_loop_blocks_when_deploy_gate_fails_in_live_mode(self) -> None:
        config_text = textwrap.dedent(
            """
            runtime:
              dry_run: false
            market_data:
              platform: mt5
            execution:
              platform: mt5
            """
        )
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(config_text)
            config_path = handle.name

        runner = StubLiveRunner()
        try:
            with patch("xauusd_ai_system.cli._run_deploy_gate", return_value=False) as gate_mock:
                with patch("xauusd_ai_system.bootstrap.build_live_runner", return_value=runner) as live_mock:
                    with patch.object(
                        sys,
                        "argv",
                        ["xauusd_ai_system.cli", "--config", config_path, "live-loop", "--iterations", "2"],
                    ):
                        with self.assertRaises(SystemExit) as ctx:
                            main()
        finally:
            Path(config_path).unlink(missing_ok=True)

        self.assertEqual(ctx.exception.code, 2)
        gate_mock.assert_called_once()
        live_mock.assert_not_called()
        self.assertEqual(runner.run_loop_calls, [])

    def test_live_once_keeps_preflight_only_path_in_dry_run(self) -> None:
        runner = StubLiveRunner()
        buffer = StringIO()
        with patch("xauusd_ai_system.cli._run_preflight", return_value=True) as preflight_mock:
            with patch("xauusd_ai_system.cli._run_deploy_gate", return_value=True) as gate_mock:
                with patch("xauusd_ai_system.bootstrap.build_live_runner", return_value=runner):
                    with patch.object(
                        sys,
                        "argv",
                        ["xauusd_ai_system.cli", "live-once", "--require-preflight"],
                    ):
                        with redirect_stdout(buffer):
                            main()

        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])
        preflight_mock.assert_called_once()
        gate_mock.assert_not_called()
        self.assertTrue(runner.run_once_called)

    def test_live_once_can_force_deploy_gate_in_dry_run(self) -> None:
        runner = StubLiveRunner()
        buffer = StringIO()
        with patch("xauusd_ai_system.cli._run_deploy_gate", return_value=True) as gate_mock:
            with patch("xauusd_ai_system.cli._run_preflight", return_value=True) as preflight_mock:
                with patch("xauusd_ai_system.bootstrap.build_live_runner", return_value=runner):
                    with patch.object(
                        sys,
                        "argv",
                        ["xauusd_ai_system.cli", "live-once", "--require-deploy-gate"],
                    ):
                        with redirect_stdout(buffer):
                            main()

        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])
        gate_mock.assert_called_once()
        preflight_mock.assert_not_called()
        self.assertTrue(runner.run_once_called)


if __name__ == "__main__":
    unittest.main()
