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
        local_wine_shell_script = ROOT / "scripts/mt5_export_history_local_wine.sh"
        probe_shell_script = ROOT / "scripts/mt5_probe_history_capacity.sh"
        probe_powershell_script = ROOT / "scripts/mt5_probe_history_capacity.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        self.assertTrue(local_wine_shell_script.exists())
        self.assertTrue(probe_shell_script.exists())
        self.assertTrue(probe_powershell_script.exists())
        self.assertIn("run_mt5_history_export", shell_script.read_text(encoding="utf-8"))
        self.assertIn('"export-mt5-history"', powershell_script.read_text(encoding="utf-8"))
        local_wine_content = local_wine_shell_script.read_text(encoding="utf-8")
        self.assertIn("mt5_local_wine_exporter", local_wine_content)
        self.assertIn("--project-root", local_wine_content)
        self.assertIn("probe-mt5-history", probe_shell_script.read_text(encoding="utf-8"))
        self.assertIn('"probe-mt5-history"', probe_powershell_script.read_text(encoding="utf-8"))

    def test_local_wine_exporter_module_exists(self) -> None:
        exporter = ROOT / "src/xauusd_ai_system/data/mt5_local_wine_exporter.py"

        self.assertTrue(exporter.exists())
        content = exporter.read_text(encoding="utf-8")
        self.assertIn("metaeditor64.exe", content)
        self.assertIn("ScriptParameters={preset_name}", content)
        self.assertIn("EXPORT_OK", content)
        self.assertIn("normalize_mt5_export", content)

    def test_shell_long_sample_cycles_use_export_wrapper(self) -> None:
        for relative_path in (
            "scripts/research_pullback_sell_v4_long_sample_cycle.sh",
            "scripts/research_pullback_sell_v4_pullback_depth_0_28_long_sample_cycle.sh",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("run_mt5_history_export", content, relative_path)

    def test_research_tier_wrappers_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_research_tier.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_research_tier.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())

        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("--tier <fast|confirm|gate>", shell_content)
        self.assertIn("fast     -> 120000 bars", shell_content)
        self.assertIn("confirm  -> 500000 bars", shell_content)
        self.assertIn("gate     -> 800000 bars", shell_content)
        self.assertIn("pullback_depth_0_28_long_sample_cycle.sh", shell_content)

        self.assertIn('[ValidateSet("fast", "confirm", "gate")]', powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_28_long_sample_cycle.ps1", powershell_content)
        self.assertIn("$defaultBars = 120000", powershell_content)
        self.assertIn("$defaultBars = 500000", powershell_content)
        self.assertIn("$defaultBars = 800000", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_27_research_tier_wrappers_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_research_tier.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_research_tier.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())

        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("--tier <fast|confirm|gate>", shell_content)
        self.assertIn("fast     -> 120000 bars", shell_content)
        self.assertIn("confirm  -> 500000 bars", shell_content)
        self.assertIn("gate     -> 800000 bars", shell_content)
        self.assertIn("pullback_depth_0_27_long_sample_cycle.sh", shell_content)

        self.assertIn('[ValidateSet("fast", "confirm", "gate")]', powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_27_long_sample_cycle.ps1", powershell_content)
        self.assertIn("$defaultBars = 120000", powershell_content)
        self.assertIn("$defaultBars = 500000", powershell_content)
        self.assertIn("$defaultBars = 800000", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_26_research_tier_wrappers_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_research_tier.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_research_tier.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())

        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("--tier <fast|confirm|gate>", shell_content)
        self.assertIn("fast     -> 120000 bars", shell_content)
        self.assertIn("confirm  -> 500000 bars", shell_content)
        self.assertIn("gate     -> 800000 bars", shell_content)
        self.assertIn("pullback_depth_0_26_long_sample_cycle.sh", shell_content)

        self.assertIn('[ValidateSet("fast", "confirm", "gate")]', powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_26_long_sample_cycle.ps1", powershell_content)
        self.assertIn("$defaultBars = 120000", powershell_content)
        self.assertIn("$defaultBars = 500000", powershell_content)
        self.assertIn("$defaultBars = 800000", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_26_event_cycle_wrappers_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_event_cycle.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_event_cycle.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())

        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("--raw-event-path <path>", shell_content)
        self.assertIn("event-calendar-build", shell_content)
        self.assertIn("event-calendar-audit", shell_content)
        self.assertIn("XAUUSD_AI_EVENT_CALENDAR_PATH", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_26.yaml", shell_content)

        self.assertIn("[string]$RawEventPath", powershell_content)
        self.assertIn('"event-calendar-build"', powershell_content)
        self.assertIn('"event-calendar-audit"', powershell_content)
        self.assertIn("$env:XAUUSD_AI_EVENT_CALENDAR_PATH", powershell_content)
        self.assertIn("configs\\mvp_pullback_sell_research_v4_pullback_depth_0_26.yaml", powershell_content)

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
        self.assertIn("function Get-Mt5ExecutionAudit", common_content)
        self.assertIn("Get-ScheduledTaskInfo", status_content)
        self.assertIn("Latest log tail", status_content)
        self.assertIn("mt5_register_task.ps1", recover_content)
        self.assertIn("mt5_task_status.ps1", recover_content)
        self.assertIn("Stop-ScheduledTask", recover_content)
        self.assertIn("StartAfterRegister = $true", recover_content)

    def test_powershell_daily_check_task_scripts_exist(self) -> None:
        register_script = ROOT / "scripts/mt5_daily_check_register_task.ps1"
        status_script = ROOT / "scripts/mt5_daily_check_task_status.ps1"
        unregister_script = ROOT / "scripts/mt5_daily_check_unregister_task.ps1"
        common_content = (ROOT / "scripts/_mt5_common.ps1").read_text(encoding="utf-8")

        self.assertTrue(register_script.exists())
        self.assertTrue(status_script.exists())
        self.assertTrue(unregister_script.exists())

        register_content = register_script.read_text(encoding="utf-8")
        status_content = status_script.read_text(encoding="utf-8")
        unregister_content = unregister_script.read_text(encoding="utf-8")

        self.assertIn("Register-ScheduledTask", register_content)
        self.assertIn("ArchiveScriptPath", register_content)
        self.assertIn('[int]$Port = 80', register_content)
        self.assertIn('"-Port"', register_content)
        self.assertIn("Get-DefaultMt5DailyCheckTaskName", register_content)
        self.assertIn("Get-ScheduledTaskInfo", status_content)
        self.assertIn("Get-DefaultMt5OpsCheckDir", status_content)
        self.assertIn("Unregister-ScheduledTask", unregister_content)
        self.assertIn("function Get-DefaultMt5DailyCheckTaskName", common_content)
        self.assertIn("function Get-DefaultMt5OpsCheckDir", common_content)

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

    def test_pullback_sell_v4_prepare_script_exists(self) -> None:
        script = ROOT / "scripts/mt5_pullback_sell_v4_prepare.ps1"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("mt5_paper_pullback_sell_v4.yaml", content)
        self.assertIn('"report-import"', content)
        self.assertIn('"host-check", "--strict"', content)
        self.assertIn('"preflight", "--strict"', content)
        self.assertIn('"deploy-gate", "--strict"', content)
        self.assertIn('"live-once", "--require-deploy-gate", "--require-preflight"', content)

    def test_pullback_sell_v4_candidate_promotion_gate_script_exists(self) -> None:
        script = ROOT / "scripts/mt5_pullback_sell_v4_candidate_promotion_gate.ps1"

        self.assertTrue(script.exists())
        content = script.read_text(encoding="utf-8")
        self.assertIn("mt5_paper_pullback_sell_v4_pullback_depth_0_26.yaml", content)
        self.assertIn("mt5_paper_pullback_sell_v4.yaml", content)
        self.assertIn('"promotion-gate"', content)
        self.assertIn('"--baseline-report-dir"', content)
        self.assertIn('"--require-current-daily-check"', content)
        self.assertIn('"--require-candidate-daily-check"', content)
        self.assertIn('"--current-execution-audit-json"', content)
        self.assertIn('"--candidate-execution-audit-json"', content)
        self.assertIn('"--require-current-execution-audit"', content)
        self.assertIn('"--require-candidate-execution-audit"', content)
        self.assertIn("Get-DefaultMt5OpsCheckDir", content)
        self.assertIn("Get-DefaultMt5ExecutionAuditDir", content)
        self.assertIn("mt5_pullback_sell_v4_daily_check_archive.ps1", content)
        self.assertIn("mt5_execution_audit_archive.ps1", content)
        self.assertIn("[switch]$RequireCurrentExecutionAudit", content)
        self.assertIn("[switch]$RequireCandidateExecutionAudit", content)
        self.assertIn("[int]$CurrentMonitoringPort = 80", content)
        self.assertIn("[int]$CandidateMonitoringPort = 8765", content)
        self.assertIn("$currentExecutionAuditCanUseDailyCheck", content)
        self.assertIn("$candidateExecutionAuditCanUseDailyCheck", content)
        self.assertIn("($RequireCurrentExecutionAudit -and -not $currentExecutionAuditCanUseDailyCheck)", content)
        self.assertIn(
            "($RequireCandidateExecutionAudit -and -not $candidateExecutionAuditCanUseDailyCheck)",
            content,
        )
        self.assertIn("-Port $CurrentMonitoringPort", content)
        self.assertIn("-Port $CandidateMonitoringPort", content)
        self.assertIn("Invoke-Mt5Cli", content)

    def test_pullback_sell_v4_execution_audit_archive_scripts_exist(self) -> None:
        generic_script = ROOT / "scripts/mt5_execution_audit_archive.ps1"
        wrapper_script = ROOT / "scripts/mt5_pullback_sell_v4_execution_audit_archive.ps1"

        self.assertTrue(generic_script.exists())
        self.assertTrue(wrapper_script.exists())

        generic_content = generic_script.read_text(encoding="utf-8")
        wrapper_content = wrapper_script.read_text(encoding="utf-8")

        self.assertIn('"execution-audit"', generic_content)
        self.assertIn("Get-DefaultMt5ExecutionAuditDir", generic_content)
        self.assertIn("latest.json", generic_content)
        self.assertIn("execution_audit_", generic_content)
        self.assertIn("mt5_execution_audit_archive.ps1", wrapper_content)
        self.assertIn('configs\\mt5_paper_pullback_sell_v4.yaml', wrapper_content)

    def test_pullback_sell_v3_runtime_wrapper_scripts_exist(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v3_paper_loop.ps1",
            "scripts/mt5_pullback_sell_v3_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_task_recover.ps1",
            "scripts/mt5_pullback_sell_v3_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_unregister_task.ps1",
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
        self.assertIn(
            "mt5_pullback_sell_v3_daily_check_archive.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_daily_check_register_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_daily_check_task_status.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_task_status.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_daily_check_task_status.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_task_status.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_daily_check_unregister_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_unregister_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_daily_check_unregister_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_unregister_task.ps1").read_text(encoding="utf-8"),
        )

    def test_pullback_sell_v3_wrappers_pin_paper_mode_via_env(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v3_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_task_recover.ps1",
            "scripts/mt5_pullback_sell_v3_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_unregister_task.ps1",
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

    def test_pullback_sell_v4_runtime_wrapper_scripts_exist(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v4_paper_loop.ps1",
            "scripts/mt5_pullback_sell_v4_register_task.ps1",
            "scripts/mt5_pullback_sell_v4_task_recover.ps1",
            "scripts/mt5_pullback_sell_v4_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_archive.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_recover.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_dashboard.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_recover.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_register_tasks.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_unregister_tasks.ps1",
        )

        for relative_path in relative_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("configs\\mt5_paper_pullback_sell_v4.yaml", content, relative_path)

        self.assertIn(
            "mt5_paper_loop.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_paper_loop.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_register_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_task_status.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_task_status.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_task_recover.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_task_recover.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_unregister_task.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_unregister_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_task_status.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_monitoring_task_status.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Get-Mt5ExecutionAudit",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            'Write-Host "[execution-audit]"',
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "EXECUTION_AUDIT_UNAVAILABLE",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_daily_check.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check_archive.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_daily_check_archive.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            '[int]$Port = 80',
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Port = $Port",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            'http://38.60.197.97:{0}/" -f $Port',
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_check_archive.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_monitoring_recover.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_recover.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_daily_check.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_recover.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_pullback_sell_v4_task_recover.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_daily_recover.ps1").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "mt5_monitoring_recover.ps1",
            (ROOT / "scripts/mt5_pullback_sell_v4_monitoring_recover.ps1").read_text(encoding="utf-8"),
        )

    def test_pullback_sell_v4_wrappers_pin_paper_mode_via_env(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v4_register_task.ps1",
            "scripts/mt5_pullback_sell_v4_task_recover.ps1",
            "scripts/mt5_pullback_sell_v4_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_dashboard.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_recover.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_register_tasks.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_unregister_tasks.ps1",
        )

        for relative_path in relative_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn('$env:XAUUSD_AI_ENV = "paper"', content, relative_path)
            self.assertIn('[string]$ConfigPath', content, relative_path)
            self.assertIn("configs\\mt5_paper_pullback_sell_v4.yaml", content, relative_path)
            self.assertNotIn('-Mode "paper"', content, relative_path)

    def test_pullback_sell_v4_wrappers_support_explicit_config_override(self) -> None:
        relative_paths = (
            "scripts/mt5_pullback_sell_v4_prepare.ps1",
            "scripts/mt5_pullback_sell_v4_paper_loop.ps1",
            "scripts/mt5_pullback_sell_v4_register_task.ps1",
            "scripts/mt5_pullback_sell_v4_task_recover.ps1",
            "scripts/mt5_pullback_sell_v4_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_archive.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_register_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_daily_check_unregister_task.ps1",
            "scripts/mt5_pullback_sell_v4_daily_recover.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_dashboard.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_recover.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_register_tasks.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_task_status.ps1",
            "scripts/mt5_pullback_sell_v4_monitoring_unregister_tasks.ps1",
        )

        for relative_path in relative_paths:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn('[string]$ConfigPath', content, relative_path)
            self.assertIn("if ($ConfigPath) { $ConfigPath } else { \"configs\\mt5_paper_pullback_sell_v4.yaml\" }", content, relative_path)

    def test_pullback_sell_v4_pullback_depth_0_26_paper_config_exists(self) -> None:
        config = ROOT / "configs/mt5_paper_pullback_sell_v4_pullback_depth_0_26.yaml"

        self.assertTrue(config.exists())
        content = config.read_text(encoding="utf-8")

        self.assertIn("min_pullback_depth: 0.26", content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_26_paper", content)
        self.assertIn("paper_pullback_sell_v4_pullback_depth_0_26.db", content)
        self.assertIn("xauusd-ai-paper-pullback-sell-v4-pullback-depth-0-26", content)
        self.assertIn("xauusd-ai-v4d026", content)
        self.assertIn("magic: 2026040101", content)

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

    def test_pullback_sell_v3_coverage_audit_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v3_coverage_audit.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v3_coverage_audit.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-audit", shell_content)
        self.assertIn("research_pullback_sell_v3_coverage_audit_latest.json", shell_content)
        self.assertIn("research_pullback_sell_v3_probe_acceptance_500000_local.json", shell_content)
        self.assertIn("report-audit", powershell_content)
        self.assertIn("research_pullback_sell_v3_coverage_audit_latest.json", powershell_content)
        self.assertIn("research_pullback_sell_v3_probe_acceptance_500000_local.json", powershell_content)

    def test_pullback_sell_v4_coverage_audit_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_coverage_audit.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_coverage_audit.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-audit", shell_content)
        self.assertIn("research_pullback_sell_v4_coverage_audit_latest.json", shell_content)
        self.assertIn("research_pullback_sell_v3_entry_hour_18_acceptance_500000_local.json", shell_content)
        self.assertIn("research_pullback_sell_v4_acceptance_latest.json", shell_content)
        self.assertIn("report-audit", powershell_content)
        self.assertIn("research_pullback_sell_v4_coverage_audit_latest.json", powershell_content)
        self.assertIn("research_pullback_sell_v3_entry_hour_18_acceptance_500000_local.json", powershell_content)
        self.assertIn("research_pullback_sell_v4_acceptance_latest.json", powershell_content)

    def test_pullback_sell_v3_density_probe_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v3_density_probe.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v3_density_probe.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("pullback-density-probe", shell_content)
        self.assertIn("research_pullback_sell_v3_density_probe_latest.json", shell_content)
        self.assertIn("xauusd_m1_history_150000_chunked_vps_full.csv", shell_content)
        self.assertIn("pullback-density-probe", powershell_content)
        self.assertIn("research_pullback_sell_v3_density_probe_latest.json", powershell_content)
        self.assertIn("xauusd_m1_history_150000_chunked_vps_full.csv", powershell_content)

    def test_pullback_sell_v4_acceptance_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_acceptance.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_acceptance.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("mvp_pullback_sell_research_v4.yaml", shell_content)
        self.assertIn("reports/research_pullback_sell_v4", shell_content)
        self.assertIn("xauusd_m1_history_500000.csv", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4.yaml", powershell_content)
        self.assertIn("research_pullback_sell_v4", powershell_content)
        self.assertIn("xauusd_m1_history_500000.csv", powershell_content)
        self.assertIn('"acceptance"', powershell_content)

    def test_pullback_sell_v4_export_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_export_latest.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_export_latest.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-export", shell_content)
        self.assertIn("research_pullback_sell_v4_acceptance_latest.json", shell_content)
        self.assertIn("reports/research_pullback_sell_v4", shell_content)
        self.assertIn("report-export", powershell_content)
        self.assertIn("research_pullback_sell_v4_acceptance_latest.json", powershell_content)
        self.assertIn("research_pullback_sell_v4", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_28_acceptance_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_acceptance.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_acceptance.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_28.yaml", shell_content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_28", shell_content)
        self.assertIn("xauusd_m1_history_500000.csv", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_28.yaml", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_28", powershell_content)
        self.assertIn("xauusd_m1_history_500000.csv", powershell_content)
        self.assertIn('"acceptance"', powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_27_acceptance_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_acceptance.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_acceptance.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_27.yaml", shell_content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_27", shell_content)
        self.assertIn("xauusd_m1_history_500000.csv", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_27.yaml", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_27", powershell_content)
        self.assertIn("xauusd_m1_history_500000.csv", powershell_content)
        self.assertIn('"acceptance"', powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_26_acceptance_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_acceptance.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_acceptance.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_26.yaml", shell_content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_26", shell_content)
        self.assertIn("xauusd_m1_history_500000.csv", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_26.yaml", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_26", powershell_content)
        self.assertIn("xauusd_m1_history_500000.csv", powershell_content)
        self.assertIn('"acceptance"', powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_28_export_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_export_latest.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_export_latest.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-export", shell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_28_acceptance_latest.json", shell_content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_28", shell_content)
        self.assertIn("report-export", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_28_acceptance_latest.json", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_28", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_27_export_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_export_latest.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_export_latest.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-export", shell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_27_acceptance_latest.json", shell_content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_27", shell_content)
        self.assertIn("report-export", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_27_acceptance_latest.json", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_27", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_26_export_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_export_latest.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_export_latest.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("report-export", shell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_26_acceptance_latest.json", shell_content)
        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_26", shell_content)
        self.assertIn("report-export", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_26_acceptance_latest.json", powershell_content)
        self.assertIn("research_pullback_sell_v4_pullback_depth_0_26", powershell_content)

    def test_pullback_sell_v4_probe_refresh_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_refresh_probe.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_refresh_probe.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("reports/research_pullback_sell_v4_probe", shell_content)
        self.assertIn("research_pullback_sell_v4_probe_acceptance_latest.json", shell_content)
        self.assertIn("xauusd_m1_history_500000.csv", shell_content)
        self.assertIn("acceptance", shell_content)
        self.assertIn("report-export", shell_content)
        self.assertIn("reports\\research_pullback_sell_v4_probe", powershell_content)
        self.assertIn("research_pullback_sell_v4_probe_acceptance_latest.json", powershell_content)
        self.assertIn("xauusd_m1_history_500000.csv", powershell_content)
        self.assertIn('"acceptance"', powershell_content)
        self.assertIn("report-export", powershell_content)

    def test_pullback_sell_v4_density_probe_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_density_probe.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_density_probe.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("pullback-density-probe", shell_content)
        self.assertIn("research_pullback_sell_v4_density_probe_latest.json", shell_content)
        self.assertIn("xauusd_m1_history_500000.csv", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4.yaml", shell_content)
        self.assertIn("pullback-density-probe", powershell_content)
        self.assertIn("research_pullback_sell_v4_density_probe_latest.json", powershell_content)
        self.assertIn("xauusd_m1_history_500000.csv", powershell_content)
        self.assertIn("mvp_pullback_sell_research_v4.yaml", powershell_content)

    def test_pullback_sell_v4_density_probe_focus_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_density_probe_focus.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_density_probe_focus.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("research_pullback_sell_v4_density_probe_focus_latest.json", shell_content)
        self.assertIn("--variant \"${DEFAULT_VARIANTS[0]}\"", shell_content)
        self.assertIn("entry_hour_17", shell_content)
        self.assertIn("atr_m5_13", shell_content)
        self.assertIn("density_relaxed_v4_a", shell_content)

        self.assertIn("research_pullback_sell_v4_density_probe_focus_latest.json", powershell_content)
        self.assertIn('"base_v4"', powershell_content)
        self.assertIn('"entry_hour_17"', powershell_content)
        self.assertIn('"atr_m5_13"', powershell_content)
        self.assertIn('"density_relaxed_v4_a"', powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_28_density_probe_focus_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_density_probe_focus.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_density_probe_focus.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn(
            "research_pullback_sell_v4_pullback_depth_0_28_density_probe_focus_latest.json",
            shell_content,
        )
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_28.yaml", shell_content)
        self.assertIn("pullback_depth_0_28_base", shell_content)
        self.assertIn("pullback_depth_0_27_from_028", shell_content)
        self.assertIn("atr_m1_3_75_from_028", shell_content)
        self.assertIn('[[ "${arg}" == "--variant" ]]', shell_content)

        self.assertIn(
            "research_pullback_sell_v4_pullback_depth_0_28_density_probe_focus_latest.json",
            powershell_content,
        )
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_28.yaml", powershell_content)
        self.assertIn('"pullback_depth_0_28_base"', powershell_content)
        self.assertIn('"pullback_depth_0_27_from_028"', powershell_content)
        self.assertIn('"atr_m1_3_75_from_028"', powershell_content)
        self.assertIn('$CliArgs -contains "--variant"', powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_27_density_probe_focus_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_density_probe_focus.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_density_probe_focus.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn(
            "research_pullback_sell_v4_pullback_depth_0_27_density_probe_focus_latest.json",
            shell_content,
        )
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_27.yaml", shell_content)
        self.assertIn("pullback_depth_0_27_base", shell_content)
        self.assertIn("pullback_depth_0_26_from_027", shell_content)
        self.assertIn("atr_m1_3_75_from_027", shell_content)
        self.assertIn('[[ "${arg}" == "--variant" ]]', shell_content)

        self.assertIn(
            "research_pullback_sell_v4_pullback_depth_0_27_density_probe_focus_latest.json",
            powershell_content,
        )
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_27.yaml", powershell_content)
        self.assertIn('"pullback_depth_0_27_base"', powershell_content)
        self.assertIn('"pullback_depth_0_26_from_027"', powershell_content)
        self.assertIn('"atr_m1_3_75_from_027"', powershell_content)
        self.assertIn('$CliArgs -contains "--variant"', powershell_content)

    def test_pullback_sell_v4_long_sample_cycle_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_long_sample_cycle.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_long_sample_cycle.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("reports/research_pullback_sell_v4/long_sample_runs", shell_content)
        self.assertIn("run_mt5_history_export", shell_content)
        self.assertIn("sample-split", shell_content)
        self.assertIn("walk-forward", shell_content)
        self.assertIn("pullback-density-probe", shell_content)
        self.assertIn("summary.json", shell_content)

        self.assertIn("reports\\research_pullback_sell_v4\\long_sample_runs", powershell_content)
        self.assertIn("export-mt5-history", powershell_content)
        self.assertIn("sample-split", powershell_content)
        self.assertIn("walk-forward", powershell_content)
        self.assertIn("pullback-density-probe", powershell_content)
        self.assertIn("summary.json", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_28_long_sample_cycle_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_long_sample_cycle.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_28_long_sample_cycle.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_28/long_sample_runs", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_28.yaml", shell_content)
        self.assertIn("run_mt5_history_export", shell_content)
        self.assertIn("sample-split", shell_content)
        self.assertIn("walk-forward", shell_content)
        self.assertIn("pullback-density-probe", shell_content)
        self.assertIn("summary.json", shell_content)

        self.assertIn("reports\\research_pullback_sell_v4_pullback_depth_0_28\\long_sample_runs", powershell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_28.yaml", powershell_content)
        self.assertIn("export-mt5-history", powershell_content)
        self.assertIn("sample-split", powershell_content)
        self.assertIn("walk-forward", powershell_content)
        self.assertIn("pullback-density-probe", powershell_content)
        self.assertIn("summary.json", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_27_long_sample_cycle_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_long_sample_cycle.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_27_long_sample_cycle.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_27/long_sample_runs", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_27.yaml", shell_content)
        self.assertIn("run_mt5_history_export", shell_content)
        self.assertIn("sample-split", shell_content)
        self.assertIn("walk-forward", shell_content)
        self.assertIn("pullback-density-probe", shell_content)
        self.assertIn("summary.json", shell_content)

        self.assertIn("reports\\research_pullback_sell_v4_pullback_depth_0_27\\long_sample_runs", powershell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_27.yaml", powershell_content)
        self.assertIn("export-mt5-history", powershell_content)
        self.assertIn("sample-split", powershell_content)
        self.assertIn("walk-forward", powershell_content)
        self.assertIn("pullback-density-probe", powershell_content)
        self.assertIn("summary.json", powershell_content)

    def test_pullback_sell_v4_pullback_depth_0_26_long_sample_cycle_scripts_exist(self) -> None:
        shell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_long_sample_cycle.sh"
        powershell_script = ROOT / "scripts/research_pullback_sell_v4_pullback_depth_0_26_long_sample_cycle.ps1"

        self.assertTrue(shell_script.exists())
        self.assertTrue(powershell_script.exists())
        shell_content = shell_script.read_text(encoding="utf-8")
        powershell_content = powershell_script.read_text(encoding="utf-8")

        self.assertIn("reports/research_pullback_sell_v4_pullback_depth_0_26/long_sample_runs", shell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_26.yaml", shell_content)
        self.assertIn("run_mt5_history_export", shell_content)
        self.assertIn("sample-split", shell_content)
        self.assertIn("walk-forward", shell_content)
        self.assertIn("pullback-density-probe", shell_content)
        self.assertIn("summary.json", shell_content)

        self.assertIn("reports\\research_pullback_sell_v4_pullback_depth_0_26\\long_sample_runs", powershell_content)
        self.assertIn("mvp_pullback_sell_research_v4_pullback_depth_0_26.yaml", powershell_content)
        self.assertIn("export-mt5-history", powershell_content)
        self.assertIn("sample-split", powershell_content)
        self.assertIn("walk-forward", powershell_content)
        self.assertIn("pullback-density-probe", powershell_content)
        self.assertIn("summary.json", powershell_content)

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
            "scripts/mt5_pullback_sell_v3_daily_check_register_task.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_task_status.ps1",
            "scripts/mt5_pullback_sell_v3_daily_check_unregister_task.ps1",
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
        daily_check_register_content = (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_register_task.ps1").read_text(encoding="utf-8")
        daily_check_status_content = (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_task_status.ps1").read_text(encoding="utf-8")
        daily_check_unregister_content = (ROOT / "scripts/mt5_pullback_sell_v3_daily_check_unregister_task.ps1").read_text(encoding="utf-8")
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
        self.assertIn("mt5_daily_check_register_task.ps1", daily_check_register_content)
        self.assertIn("mt5_pullback_sell_v3_daily_check_archive.ps1", daily_check_register_content)
        self.assertIn("IntervalMinutes = 15", daily_check_register_content)
        self.assertIn("AttentionSyncThreshold", daily_check_register_content)
        self.assertIn("mt5_daily_check_task_status.ps1", daily_check_status_content)
        self.assertIn("ArchiveFreshnessWarningMinutes", daily_check_status_content)
        self.assertIn("mt5_daily_check_unregister_task.ps1", daily_check_unregister_content)
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
