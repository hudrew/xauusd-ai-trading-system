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

    def test_export_history_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/mt5_export_history.sh"
        powershell_script = ROOT / "scripts/mt5_export_history.ps1"
        probe_shell_script = ROOT / "scripts/mt5_probe_history_capacity.sh"
        probe_powershell_script = ROOT / "scripts/mt5_probe_history_capacity.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        self.assertTrue(probe_shell_script.exists())
        self.assertTrue(probe_powershell_script.exists())
        self.assertIn("export-mt5-history", shell_script.read_text(encoding="utf-8"))
        self.assertIn('"export-mt5-history"', powershell_script.read_text(encoding="utf-8"))
        self.assertIn("probe-mt5-history", probe_shell_script.read_text(encoding="utf-8"))
        self.assertIn('"probe-mt5-history"', probe_powershell_script.read_text(encoding="utf-8"))

    def test_powershell_task_registration_scripts_exist(self) -> None:
        register_script = ROOT / "scripts/mt5_register_task.ps1"
        unregister_script = ROOT / "scripts/mt5_unregister_task.ps1"
        runner_script = ROOT / "scripts/mt5_task_runner.ps1"
        status_script = ROOT / "scripts/mt5_task_status.ps1"
        recover_script = ROOT / "scripts/mt5_task_recover.ps1"

        self.assertTrue(register_script.exists())
        self.assertTrue(unregister_script.exists())
        self.assertTrue(runner_script.exists())
        self.assertTrue(status_script.exists())
        self.assertTrue(recover_script.exists())
        register_content = register_script.read_text(encoding="utf-8")
        unregister_content = unregister_script.read_text(encoding="utf-8")
        runner_content = runner_script.read_text(encoding="utf-8")
        status_content = status_script.read_text(encoding="utf-8")
        recover_content = recover_script.read_text(encoding="utf-8")
        common_content = (ROOT / "scripts/_mt5_common.ps1").read_text(encoding="utf-8")

        self.assertIn("Register-ScheduledTask", register_content)
        self.assertIn("New-ScheduledTaskAction", register_content)
        self.assertIn("mt5_task_runner.ps1", register_content)
        self.assertIn("LogDir", register_content)
        self.assertIn("mt5_prod_loop.ps1", register_content)
        self.assertIn("mt5_paper_loop.ps1", register_content)
        self.assertIn("Unregister-ScheduledTask", unregister_content)
        self.assertIn("Get-DefaultMt5TaskLogDir", runner_content)
        self.assertIn("HeartbeatIntervalSeconds = 30", runner_content)
        self.assertIn("task_runner_heartbeat", runner_content)
        self.assertIn("WaitForExit($heartbeatIntervalMilliseconds)", runner_content)
        self.assertIn("Ensure-Mt5TerminalProcess", runner_content)
        self.assertIn("terminal_process_ready", runner_content)
        self.assertIn("function Ensure-Mt5TerminalProcess", common_content)
        self.assertIn("function Get-Mt5TerminalProcess", common_content)
        self.assertIn("Get-ScheduledTaskInfo", status_content)
        self.assertIn("Latest log tail", status_content)
        self.assertIn("mt5_register_task.ps1", recover_content)
        self.assertIn("mt5_task_status.ps1", recover_content)
        self.assertIn("Stop-ScheduledTask", recover_content)
        self.assertIn("StartAfterRegister = $true", recover_content)

    def test_pullback_sell_v3_prepare_script_exists(self) -> None:
        script = ROOT / "scripts/mt5_pullback_sell_v3_prepare.ps1"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("mt5_paper_pullback_sell_v3.yaml", content)
        self.assertIn('"report-import"', content)
        self.assertIn('"host-check", "--strict"', content)
        self.assertIn('"preflight", "--strict"', content)
        self.assertIn('"deploy-gate", "--strict"', content)
        self.assertIn('"live-once", "--require-deploy-gate", "--require-preflight"', content)

    def test_pullback_sell_v3_runtime_wrapper_scripts_exist(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v3_paper_loop.ps1",
            "scripts/mt5_pullback_sell_v3_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_task_recover.ps1",
            "scripts/mt5_pullback_sell_v3_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_unregister_task.ps1",
        )

        for relative_path in relative_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("configs\\mt5_paper_pullback_sell_v3.yaml", content, relative_path)

        self.assertIn(
            "mt5_paper_loop.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_paper_loop.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_register_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_task_status.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_task_status.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_task_recover.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_task_recover.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_unregister_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_unregister_task.ps1").read_text(encoding="utf-8"),
        )

    def test_pullback_sell_v3_wrappers_pin_paper_mode_via_env(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v3_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_task_recover.ps1",
            "scripts/mt5_pullback_sell_v3_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_dashboard.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_recover.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_register_tasks.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_unregister_tasks.ps1",
        )

        for relative_path in relative_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn('$env:XAUUSD_AI_ENV = "paper"', content, relative_path)
            self.assertIn("ConfigPath = \"configs\\mt5_paper_pullback_sell_v3.yaml\"", content, relative_path)
            self.assertNotIn('-Mode "paper"', content, relative_path)

    def test_runtime_scripts_support_explicit_config_override(self) -> None:
        shell_common = (ROOT / "scripts/_mt5_common.sh").read_text(encoding="utf-8")
        ps_common = (ROOT / "scripts/_mt5_common.ps1").read_text(encoding="utf-8")
        register_content = (ROOT / "scripts/mt5_register_task.ps1").read_text(encoding="utf-8")
        runner_content = (ROOT / "scripts/mt5_task_runner.ps1").read_text(encoding="utf-8")

        self.assertIn("XAUUSD_AI_CONFIG_PATH", shell_common)
        self.assertIn("Get-DefaultMt5TaskName -Mode $Mode -ConfigPath $resolvedConfigPath", register_content)
        self.assertIn("-ConfigPath", register_content)
        self.assertIn("-ConfigPath $resolvedConfigPath", runner_content)
        self.assertIn("$env:XAUUSD_AI_CONFIG_PATH", ps_common)
        self.assertIn("function Get-Mt5MonitoringSnapshot", ps_common)
        self.assertIn('"monitoring"', ps_common)
        self.assertIn('"snapshot"', ps_common)
        self.assertIn("ConvertFrom-Json", ps_common)

    def test_pullback_sell_v3_acceptance_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v3_acceptance.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v3_acceptance.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("mvp_pullback_sell_research_v3_branch_gate.yaml", shell_content)
        self.assertIn("reports/research_pullback_sell_v3", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("mvp_pullback_sell_research_v3_branch_gate.yaml", powershell_content)
        self.assertIn("research_pullback_sell_v3", powershell_content)
        self.assertIn('"acceptance"', powershell_content)

    def test_pullback_sell_v3_export_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v3_export_latest.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v3_export_latest.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-export", shell_content)
        self.assertIn("research_pullback_sell_v3_acceptance_latest.json", shell_content)
        self.assertIn("report-export", powershell_content)
        self.assertIn("research_pullback_sell_v3_acceptance_latest.json", powershell_content)

    def test_pullback_sell_v3_probe_refresh_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v3_refresh_probe.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v3_refresh_probe.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("reports/research_pullback_sell_v3_probe", shell_content)
        self.assertIn("research_pullback_sell_v3_probe_acceptance_latest.json", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("report-export", shell_content)
        self.assertIn("reports\\research_pullback_sell_v3_probe", powershell_content)
        self.assertIn("research_pullback_sell_v3_probe_acceptance_latest.json", powershell_content)
        self.assertIn('"acceptance"', powershell_content)
        self.assertIn("report-export", powershell_content)

    def test_monitoring_dashboard_scripts_avoid_host_variable_collision(self) -> None:
        base_script = ROOT / "scripts/mt5_monitoring_dashboard.ps1"
        wrapper_script = ROOT / "scripts/mt5_pullback_sell_v3_monitoring_dashboard.ps1"

        self.assertTrue(base_script.exists())
        self.assertTrue(wrapper_script.exists())

        base_content = base_script.read_text(encoding="utf-8")
        wrapper_content = wrapper_script.read_text(encoding="utf-8")

        self.assertIn('[Alias("Host")]', base_content)
        self.assertIn('[Alias("Host")]', wrapper_content)
        self.assertIn("$BindHost", base_content)
        self.assertIn("$BindHost", wrapper_content)
        self.assertIn('"monitoring"', base_content)
        self.assertIn("mt5_monitoring_dashboard.ps1", wrapper_content)
        self.assertIn("[int]$Port = 80", wrapper_content)

    def test_monitoring_autostart_scripts_exist(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v3_daily_check.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_archive.ps1",
            "scripts/mt5_pullback_sell_v3_daily_recover.ps1",
            "scripts/mt5_monitoring_export_loop.ps1",
            "scripts/mt5_monitoring_recover.ps1",
            "scripts/mt5_monitoring_register_tasks.ps1",
            "scripts/mt5_monitoring_task_runner.ps1",
            "scripts/mt5_monitoring_unregister_tasks.ps1",
            "scripts/mt5_monitoring_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_recover.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_register_tasks.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_unregister_tasks.ps1",
            "scripts/mt5_pullback_sell_v3_monitoring_task_status.ps1",
        )

        for relative_path in relative_paths:
            self.assertTrue((ROOT / relative_path).exists(), relative_path)

        register_content = (ROOT / "scripts/mt5_monitoring_register_tasks.ps1").read_text(encoding="utf-8")
        export_loop_content = (ROOT / "scripts/mt5_monitoring_export_loop.ps1").read_text(encoding="utf-8")
        runner_content = (ROOT / "scripts/mt5_monitoring_task_runner.ps1").read_text(encoding="utf-8")
        status_content = (ROOT / "scripts/mt5_monitoring_task_status.ps1").read_text(encoding="utf-8")
        recover_content = (ROOT / "scripts/mt5_monitoring_recover.ps1").read_text(encoding="utf-8")
        wrapper_register_content = (ROOT / "scripts/mt5_pullback_sell_v3_monitoring_register_tasks.ps1").read_text(encoding="utf-8")
        wrapper_recover_content = (ROOT / "scripts/mt5_pullback_sell_v3_monitoring_recover.ps1").read_text(encoding="utf-8")
        daily_check_content = (ROOT / "scripts/mt5_pullback_sell_v3_daily_check.ps1").read_text(encoding="utf-8")
        daily_check_archive_content = (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_archive.ps1").read_text(encoding="utf-8")
        daily_recover_content = (ROOT / "scripts/mt5_pullback_sell_v3_daily_recover.ps1").read_text(encoding="utf-8")
        task_recover_content = (ROOT / "scripts/mt5_pullback_sell_v3_task_recover.ps1").read_text(encoding="utf-8")

        self.assertIn("Register-ScheduledTask", register_content)
        self.assertIn("Get-DefaultMt5MonitoringTaskName", register_content)
        self.assertIn("Get-DefaultMt5MonitoringLogPath", register_content)
        self.assertIn("mt5_monitoring_task_runner.ps1", register_content)
        self.assertIn('"monitoring"', export_loop_content)
        self.assertIn('"export-html"', export_loop_content)
        self.assertIn("monitoring_runner_started", runner_content)
        self.assertIn("monitoring_runner_heartbeat", runner_content)
        self.assertIn("mt5_monitoring_dashboard.ps1", runner_content)
        self.assertIn("mt5_monitoring_export_loop.ps1", runner_content)
        self.assertIn("Start-Process", runner_content)
        self.assertIn("dashboard_path:", status_content)
        self.assertIn("Get-ScheduledTaskInfo", status_content)
        self.assertIn("ConvertTo-Json", status_content)
        self.assertIn("dashboard_exists", status_content)
        self.assertIn("monitoring_health", status_content)
        self.assertIn("Invoke-WebRequest", recover_content)
        self.assertIn("Stop-ScheduledTask", recover_content)
        self.assertIn("Get-NetTCPConnection", recover_content)
        self.assertIn("$registerArgs = @{", recover_content)
        self.assertIn("$statusArgs = @{", recover_content)
        self.assertIn('$env:XAUUSD_AI_ENV = $Mode', recover_content)
        self.assertIn("Get-Mt5MonitoringSnapshot", recover_content)
        self.assertIn("AttentionSyncThreshold", recover_content)
        self.assertIn("FailOnAttentionSync", recover_content)
        self.assertIn("FailOnRuntimeIssue", recover_content)
        self.assertIn("attention_sync_detected", recover_content)
        self.assertIn("runtime_issue_detected", recover_content)
        self.assertIn("configs\\mt5_paper_pullback_sell_v3.yaml", wrapper_register_content)
        self.assertIn("mt5_monitoring_recover.ps1", wrapper_recover_content)
        self.assertIn("[int]$Port = 80", wrapper_register_content)
        self.assertIn("[int]$Port = 80", wrapper_recover_content)
        self.assertIn("AttentionSyncThreshold", wrapper_recover_content)
        self.assertIn("FailOnAttentionSync", wrapper_recover_content)
        self.assertIn("FailOnRuntimeIssue", wrapper_recover_content)
        self.assertIn("AsJson", (ROOT / "scripts/mt5_pullback_sell_v3_monitoring_task_status.ps1").read_text(encoding="utf-8"))
        self.assertIn("mt5_pullback_sell_v3_task_status.ps1", daily_check_content)
        self.assertIn("mt5_pullback_sell_v3_monitoring_task_status.ps1", daily_check_content)
        self.assertIn("Invoke-WebRequest", daily_check_content)
        self.assertIn("Get-Mt5MonitoringSnapshot", daily_check_content)
        self.assertIn("ConvertTo-Json", daily_check_content)
        self.assertIn("AsJson", daily_check_content)
        self.assertIn("FailOnAttention", daily_check_content)
        self.assertIn("daily-check-summary", daily_check_content)
        self.assertIn("recent_reconcile_syncs", daily_check_content)
        self.assertIn("[int]$Port = 80", daily_check_content)
        self.assertIn('var\\xauusd_ai\\ops_checks\\paper', daily_check_archive_content)
        self.assertIn("Start-Transcript", daily_check_archive_content)
        self.assertIn("latest.json", daily_check_archive_content)
        self.assertIn("summary_health", daily_check_archive_content)
        self.assertIn("FailOnAttention", daily_check_archive_content)
        self.assertIn("mt5_pullback_sell_v3_daily_check.ps1", daily_check_archive_content)
        self.assertIn("[int]$Port = 80", daily_check_archive_content)
        self.assertIn("mt5_pullback_sell_v3_monitoring_recover.ps1", daily_recover_content)
        self.assertIn("mt5_pullback_sell_v3_daily_check.ps1", daily_recover_content)
        self.assertIn("[int]$Port = 80", daily_recover_content)
        self.assertIn("AttentionSyncThreshold", daily_recover_content)
        self.assertIn("FailOnAttentionSync", daily_recover_content)
        self.assertIn("FailOnRuntimeIssue", daily_recover_content)
        self.assertIn("RecoverPaperTaskOnRuntimeIssue", daily_recover_content)
        self.assertIn("mt5_pullback_sell_v3_task_recover.ps1", daily_recover_content)
        self.assertIn("Get-Mt5MonitoringSnapshot", daily_recover_content)
        self.assertIn("Load-EnvFile", daily_recover_content)
        self.assertIn("mt5_task_recover.ps1", task_recover_content)


if __name__ == "__main__":
    unittest.main()
