param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$DashboardPath,
    [string]$ServeTaskName,
    [string]$RefreshTaskName,
    [string]$ServeLogPath,
    [string]$RefreshLogPath,
    [switch]$TailLog,
    [int]$TailLines = 40
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function Get-LastTaskResultDescription {
    param(
        [int64]$ResultCode
    )

    switch ($ResultCode) {
        0 { return "Success" }
        267008 { return "Task is ready to run" }
        267009 { return "Task is currently running" }
        267010 { return "Task is disabled" }
        267011 { return "Task has not run yet" }
        default { return "See Windows Task Scheduler last result code" }
    }
}

function Show-MonitoringTaskStatus {
    param(
        [string]$Label,
        [string]$TaskName,
        [string]$LogPath
    )

    Write-Host ""
    Write-Host ("[{0}]" -f $Label) -ForegroundColor Cyan

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Host ("task_name: {0}" -f $TaskName)
        Write-Host "status: missing"
        return
    }

    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
    $lastResult = [int64]$taskInfo.LastTaskResult

    Write-Host ("task_name: {0}" -f $TaskName)
    Write-Host ("state: {0}" -f $task.State)
    Write-Host ("enabled: {0}" -f $task.Settings.Enabled)
    Write-Host ("last_run_time: {0}" -f $taskInfo.LastRunTime)
    Write-Host ("last_task_result: {0}" -f $lastResult)
    Write-Host ("last_task_result_hex: {0}" -f ("0x{0:X8}" -f $lastResult))
    Write-Host ("last_task_result_description: {0}" -f (Get-LastTaskResultDescription -ResultCode $lastResult))

    if ($LogPath -and (Test-Path $LogPath)) {
        $logItem = Get-Item -Path $LogPath
        Write-Host ("log_path: {0}" -f $LogPath)
        Write-Host ("log_updated_at: {0}" -f $logItem.LastWriteTime)
        Write-Host ("log_size_bytes: {0}" -f $logItem.Length)
        if ($TailLog) {
            Write-Host ""
            Write-Host ("Latest log tail: {0}" -f $LogPath) -ForegroundColor DarkGray
            Get-Content -Path $LogPath -Tail $TailLines
        }
    }
    else {
        Write-Host ("log_path: {0}" -f $LogPath)
        Write-Host "log_status: missing"
    }
}

if ($EnvFile) {
    $resolvedEnvFile = Resolve-AbsoluteProjectPath -PathValue $EnvFile
    if (-not (Test-Path $resolvedEnvFile)) {
        throw "Env file not found: $resolvedEnvFile"
    }
    Load-EnvFile -EnvFile $resolvedEnvFile
}

$resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
$resolvedDashboardPath = if ($DashboardPath) {
    Resolve-AbsoluteProjectPath -PathValue $DashboardPath
}
else {
    Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringDashboardPath -Mode $Mode -ConfigPath $resolvedConfigPath)
}
$resolvedServeTaskName = if ($ServeTaskName) { $ServeTaskName } else { Get-DefaultMt5MonitoringTaskName -Mode $Mode -ConfigPath $resolvedConfigPath -Role "serve" }
$resolvedRefreshTaskName = if ($RefreshTaskName) { $RefreshTaskName } else { Get-DefaultMt5MonitoringTaskName -Mode $Mode -ConfigPath $resolvedConfigPath -Role "refresh" }
$resolvedServeLogPath = if ($ServeLogPath) {
    Resolve-AbsoluteProjectPath -PathValue $ServeLogPath
}
else {
    Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringLogPath -Mode $Mode -ConfigPath $resolvedConfigPath -Role "serve")
}
$resolvedRefreshLogPath = if ($RefreshLogPath) {
    Resolve-AbsoluteProjectPath -PathValue $RefreshLogPath
}
else {
    Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringLogPath -Mode $Mode -ConfigPath $resolvedConfigPath -Role "refresh")
}

Write-Host ("dashboard_path: {0}" -f $resolvedDashboardPath)
if (Test-Path $resolvedDashboardPath) {
    $dashboardItem = Get-Item -Path $resolvedDashboardPath
    Write-Host ("dashboard_updated_at: {0}" -f $dashboardItem.LastWriteTime)
    Write-Host ("dashboard_size_bytes: {0}" -f $dashboardItem.Length)
}
else {
    Write-Host "dashboard_status: missing"
}

Show-MonitoringTaskStatus -Label "serve" -TaskName $resolvedServeTaskName -LogPath $resolvedServeLogPath
Show-MonitoringTaskStatus -Label "refresh" -TaskName $resolvedRefreshTaskName -LogPath $resolvedRefreshLogPath
