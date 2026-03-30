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
    [switch]$AsJson,
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
        [hashtable]$Status
    )

    Write-Host ""
    Write-Host ("[{0}]" -f $Status["label"]) -ForegroundColor Cyan

    Write-Host ("health: {0}" -f $Status["health"])
    Write-Host ("task_name: {0}" -f $Status["task_name"])
    Write-Host ("status: {0}" -f $Status["status"])

    if ($Status["status"] -eq "missing") {
        return
    }

    Write-Host ("state: {0}" -f $Status["state"])
    Write-Host ("enabled: {0}" -f $Status["enabled"])
    Write-Host ("last_run_time: {0}" -f $Status["last_run_time"])
    Write-Host ("last_task_result: {0}" -f $Status["last_task_result"])
    Write-Host ("last_task_result_hex: {0}" -f $Status["last_task_result_hex"])
    Write-Host ("last_task_result_description: {0}" -f $Status["last_task_result_description"])
    Write-Host ("log_path: {0}" -f $Status["log_path"])
    if ([bool]$Status["log_exists"]) {
        Write-Host ("log_updated_at: {0}" -f $Status["log_updated_at"])
        Write-Host ("log_size_bytes: {0}" -f $Status["log_size_bytes"])
        if ($TailLog -and -not $AsJson) {
            Write-Host ""
            Write-Host ("Latest log tail: {0}" -f $Status["log_path"]) -ForegroundColor DarkGray
            Get-Content -Path $Status["log_path"] -Tail $TailLines
        }
    }
    else {
        Write-Host "log_status: missing"
    }
}

function New-MonitoringIssue {
    param(
        [string]$Source,
        [string]$Code,
        [string]$Message
    )

    return [ordered]@{
        source = $Source
        code = $Code
        message = $Message
    }
}

function Get-MonitoringTaskSnapshot {
    param(
        [string]$Label,
        [string]$TaskName,
        [string]$LogPath
    )

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        return [ordered]@{
            label = $Label
            task_name = $TaskName
            status = "missing"
            health = "attention"
            state = $null
            enabled = $false
            last_run_time = $null
            last_task_result = $null
            last_task_result_hex = $null
            last_task_result_description = $null
            log_path = $LogPath
            log_exists = $false
            log_updated_at = $null
            log_size_bytes = $null
        }
    }

    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
    $lastResult = [int64]$taskInfo.LastTaskResult
    $logExists = [bool]($LogPath -and (Test-Path $LogPath))
    $logItem = if ($logExists) { Get-Item -Path $LogPath } else { $null }

    $health = "ok"
    if (-not $task.Settings.Enabled) {
        $health = "attention"
    }
    elseif ($task.State -ne "Running") {
        $health = "attention"
    }

    return [ordered]@{
        label = $Label
        task_name = $TaskName
        status = "present"
        health = $health
        state = [string]$task.State
        enabled = [bool]$task.Settings.Enabled
        last_run_time = $taskInfo.LastRunTime
        last_task_result = $lastResult
        last_task_result_hex = ("0x{0:X8}" -f $lastResult)
        last_task_result_description = Get-LastTaskResultDescription -ResultCode $lastResult
        log_path = $LogPath
        log_exists = $logExists
        log_updated_at = if ($null -ne $logItem) { $logItem.LastWriteTime } else { $null }
        log_size_bytes = if ($null -ne $logItem) { $logItem.Length } else { $null }
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

$dashboardExists = Test-Path $resolvedDashboardPath
$dashboardItem = if ($dashboardExists) { Get-Item -Path $resolvedDashboardPath } else { $null }
$serveStatus = Get-MonitoringTaskSnapshot -Label "serve" -TaskName $resolvedServeTaskName -LogPath $resolvedServeLogPath
$refreshStatus = Get-MonitoringTaskSnapshot -Label "refresh" -TaskName $resolvedRefreshTaskName -LogPath $resolvedRefreshLogPath

$issues = @()
if (-not $dashboardExists) {
    $issues += (New-MonitoringIssue -Source "dashboard" -Code "DASHBOARD_MISSING" -Message ("Dashboard file not found: {0}" -f $resolvedDashboardPath))
}
foreach ($taskStatus in @($serveStatus, $refreshStatus)) {
    if ($taskStatus["status"] -eq "missing") {
        $issues += (New-MonitoringIssue -Source ([string]$taskStatus["label"]) -Code "TASK_MISSING" -Message ("Monitoring task missing: {0}" -f $taskStatus["task_name"]))
        continue
    }

    if (-not [bool]$taskStatus["enabled"]) {
        $issues += (New-MonitoringIssue -Source ([string]$taskStatus["label"]) -Code "TASK_DISABLED" -Message ("Monitoring task disabled: {0}" -f $taskStatus["task_name"]))
    }

    if ([string]$taskStatus["state"] -ne "Running") {
        $issues += (New-MonitoringIssue -Source ([string]$taskStatus["label"]) -Code "TASK_NOT_RUNNING" -Message ("Monitoring task not running: {0} ({1})" -f $taskStatus["task_name"], $taskStatus["state"]))
    }
}

$health = if ($issues.Count -gt 0) { "attention" } else { "ok" }
$output = [ordered]@{
    mode = $Mode
    config_path = $resolvedConfigPath
    health = $health
    issues = $issues
    dashboard_path = $resolvedDashboardPath
    dashboard_exists = $dashboardExists
    dashboard_updated_at = if ($null -ne $dashboardItem) { $dashboardItem.LastWriteTime } else { $null }
    dashboard_size_bytes = if ($null -ne $dashboardItem) { $dashboardItem.Length } else { $null }
    serve = $serveStatus
    refresh = $refreshStatus
}

if ($AsJson) {
    $output | ConvertTo-Json -Depth 6
    return
}

Write-Host ("monitoring_health: {0}" -f $health)
Write-Host ("dashboard_path: {0}" -f $resolvedDashboardPath)
if ($dashboardExists) {
    Write-Host ("dashboard_updated_at: {0}" -f $dashboardItem.LastWriteTime)
    Write-Host ("dashboard_size_bytes: {0}" -f $dashboardItem.Length)
}
else {
    Write-Host "dashboard_status: missing"
}

Show-MonitoringTaskStatus -Status $serveStatus
Show-MonitoringTaskStatus -Status $refreshStatus
