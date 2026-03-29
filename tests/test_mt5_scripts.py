from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Mt5ScriptDefaultsTests(unittest.TestCase):
    def test_shell_runtime_scripts_require_gate_and_preflight(self) -> None:
        for relative_path in (
            "scripts/mt5_live_once.sh",
            "scripts/mt5_paper_loop.sh",
            "scripts/mt5_prod_loop.sh",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("--require-deploy-gate", content, relative_path)
            self.assertIn("--require-preflight", content, relative_path)

    def test_powershell_runtime_scripts_require_gate_and_preflight(self) -> None:
        for relative_path in (
            "scripts/mt5_live_once.ps1",
            "scripts/mt5_paper_loop.ps1",
            "scripts/mt5_prod_loop.ps1",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("--require-deploy-gate", content, relative_path)
            self.assertIn("--require-preflight", content, relative_path)

    def test_shell_and_powershell_gate_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/mt5_deploy_gate.sh"
        powershell_script = ROOT / "scripts/mt5_deploy_gate.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        self.assertIn("deploy-gate --strict", shell_script.read_text(encoding="utf-8"))
        self.assertIn('"deploy-gate", "--strict"', powershell_script.read_text(encoding="utf-8"))

    def test_powershell_task_registration_scripts_exist(self) -> None:
        register_script = ROOT / "scripts/mt5_register_task.ps1"
        unregister_script = ROOT / "scripts/mt5_unregister_task.ps1"
        runner_script = ROOT / "scripts/mt5_task_runner.ps1"
        status_script = ROOT / "scripts/mt5_task_status.ps1"

        self.assertTrue(register_script.exists())
        self.assertTrue(unregister_script.exists())
        self.assertTrue(runner_script.exists())
        self.assertTrue(status_script.exists())
        register_content = register_script.read_text(encoding="utf-8")
        unregister_content = unregister_script.read_text(encoding="utf-8")
        runner_content = runner_script.read_text(encoding="utf-8")
        status_content = status_script.read_text(encoding="utf-8")

        self.assertIn("Register-ScheduledTask", register_content)
        self.assertIn("New-ScheduledTaskAction", register_content)
        self.assertIn("mt5_task_runner.ps1", register_content)
        self.assertIn("LogDir", register_content)
        self.assertIn("mt5_prod_loop.ps1", register_content)
        self.assertIn("mt5_paper_loop.ps1", register_content)
        self.assertIn("Unregister-ScheduledTask", unregister_content)
        self.assertIn("Get-DefaultMt5TaskLogDir", runner_content)
        self.assertIn("Get-ScheduledTaskInfo", status_content)
        self.assertIn("Latest log tail", status_content)


if __name__ == "__main__":
    unittest.main()
