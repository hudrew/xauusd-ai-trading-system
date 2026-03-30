param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [Alias("Host")]
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8765,
    [string]$DashboardPath,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [int]$SnapshotIntervalSeconds = 60,
    [string]$Title,
    [string]$ServeTaskName,
    [string]$RefreshTaskName,
    [int]$AttentionSyncThreshold = 1,
    [switch]$FailOnAttentionSync,
    [switch]$FailOnRuntimeIssue,
    [switch]$SkipTaskRestart,
    [switch]$SkipProcessCleanup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function Stop-ScheduledTaskIfExists {
    param(
        [string]$TaskName
    )

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Host ("task_missing: {0}" -f $TaskName)
        return
    }

    try {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Write-Host ("task_stopped: {0}" -f $TaskName)
    }
    catch {
        Write-Host ("task_stop_warning: {0} -> {1}" -f $TaskName, $_.Exception.Message)
    }
}

function Stop-PortListeners {
    param(
        [int]$Port
    )

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($null -eq $connections) {
        Write-Host ("port_clear: {0}" -f $Port)
        return
    }

    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host ("port_process_stopped: {0}" -f $processId)
        }
        catch {
            Write-Host ("port_process_stop_warning: {0} -> {1}" -f $processId, $_.Exception.Message)
        }
    }
}

function Get-FirstMixName {
    param(
        [object[]]$Rows
    )

    if ($null -eq $Rows -or $Rows.Count -eq 0) {
        return $null
    }

    return [string]$Rows[0].name
}

Ensure-Venv

$resolvedEnvFile = if ($EnvFile) {
    Resolve-AbsoluteProjectPath -PathValue $EnvFile
}
else {
    $Script:DefaultEnvFile
}

if (Test-Path $resolvedEnvFile) {
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

Stop-ScheduledTaskIfExists -TaskName $resolvedServeTaskName
Stop-ScheduledTaskIfExists -TaskName $resolvedRefreshTaskName
Start-Sleep -Seconds 2

if (-not $SkipProcessCleanup) {
    $stoppedProcesses = @(Stop-Mt5MonitoringProcesses -Mode $Mode -ConfigPath $resolvedConfigPath)
    foreach ($process in $stoppedProcesses) {
        Write-Host ("monitoring_process_stopped: pid={0} parent={1} name={2}" -f $process.ProcessId, $process.ParentProcessId, $process.Name)
    }

    if ($stoppedProcesses.Count -gt 0) {
        Start-Sleep -Seconds 2
    }
}

Stop-PortListeners -Port $Port
Start-Sleep -Seconds 2

if (-not $SkipTaskRestart) {
    $registerScriptPath = Join-Path $PSScriptRoot "mt5_monitoring_register_tasks.ps1"
    $registerArgs = @{
        EnvFile = $resolvedEnvFile
        ConfigPath = $resolvedConfigPath
        DashboardPath = $resolvedDashboardPath
        BindHost = $BindHost
        Port = $Port
        DecisionLimit = $DecisionLimit
        ExecutionLimit = $ExecutionLimit
        StaleAfterSeconds = $StaleAfterSeconds
        RefreshSeconds = $RefreshSeconds
        SnapshotIntervalSeconds = $SnapshotIntervalSeconds
        ServeTaskName = $resolvedServeTaskName
        RefreshTaskName = $resolvedRefreshTaskName
        StartAfterRegister = $true
        Force = $true
    }
    if (-not [string]::IsNullOrWhiteSpace($Title)) {
        $registerArgs.Title = $Title
    }

    $previousEnvMode = $env:XAUUSD_AI_ENV
    try {
        $env:XAUUSD_AI_ENV = $Mode
        & $registerScriptPath @registerArgs
    }
    finally {
        if ($null -eq $previousEnvMode) {
            Remove-Item Env:XAUUSD_AI_ENV -ErrorAction SilentlyContinue
        }
        else {
            $env:XAUUSD_AI_ENV = $previousEnvMode
        }
    }
}

Start-Sleep -Seconds 5

$healthUrl = "http://127.0.0.1:{0}/health" -f $Port
try {
    $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
    Write-Host "monitoring_health_ok" -ForegroundColor Green
    Write-Host ("health_status_code: {0}" -f $response.StatusCode)
    Write-Host ("health_body: {0}" -f $response.Content)
}
catch {
    Write-Host "monitoring_health_failed" -ForegroundColor Yellow
    Write-Host ("health_error: {0}" -f $_.Exception.Message)
}

$statusScriptPath = Join-Path $PSScriptRoot "mt5_monitoring_task_status.ps1"
$statusArgs = @{
    EnvFile = $resolvedEnvFile
    ConfigPath = $resolvedConfigPath
    DashboardPath = $resolvedDashboardPath
    ServeTaskName = $resolvedServeTaskName
    RefreshTaskName = $resolvedRefreshTaskName
    TailLog = $true
    TailLines = 20
}

$previousEnvMode = $env:XAUUSD_AI_ENV
try {
    $env:XAUUSD_AI_ENV = $Mode
    & $statusScriptPath @statusArgs
}
finally {
    if ($null -eq $previousEnvMode) {
        Remove-Item Env:XAUUSD_AI_ENV -ErrorAction SilentlyContinue
    }
    else {
        $env:XAUUSD_AI_ENV = $previousEnvMode
    }
}

Write-Host ""
Write-Host "[monitoring-snapshot]" -ForegroundColor Cyan

$snapshot = Get-Mt5MonitoringSnapshot `
    -ConfigPath $resolvedConfigPath `
    -DecisionLimit $DecisionLimit `
    -ExecutionLimit $ExecutionLimit `
    -StaleAfterSeconds $StaleAfterSeconds

Write-Host ("runtime_status: {0}" -f $snapshot.runtime.status)
Write-Host ("latest_sync_status: {0}" -f $snapshot.execution_sync.latest_status)
Write-Host ("latest_sync_origin: {0}" -f $snapshot.execution_sync.latest_origin)
Write-Host ("latest_sync_attention: {0}" -f $snapshot.execution_sync.latest_is_attention)
Write-Host ("recent_attention_syncs: {0}" -f $snapshot.execution_sync.recent_attention_count)
Write-Host ("recent_close_events: {0}" -f $snapshot.execution_sync.recent_close_event_count)
Write-Host ("top_close_status: {0}" -f (Get-FirstMixName -Rows $snapshot.pressure.execution_sync_close_statuses))
Write-Host ("top_deal_reason: {0}" -f (Get-FirstMixName -Rows $snapshot.pressure.execution_sync_deal_reasons))

$hasRuntimeIssue = $snapshot.runtime.status -ne "healthy"
$hasAttentionSync = (
    [bool]$snapshot.execution_sync.latest_is_attention -or
    [int]$snapshot.execution_sync.recent_attention_count -ge [Math]::Max($AttentionSyncThreshold, 1)
)

if ($hasRuntimeIssue) {
    Write-Host "runtime_issue_detected" -ForegroundColor Yellow
}

if ($hasAttentionSync) {
    Write-Host "attention_sync_detected" -ForegroundColor Yellow
}

if ($FailOnRuntimeIssue -and $hasRuntimeIssue) {
    throw ("Monitoring runtime is not healthy: {0}" -f $snapshot.runtime.status)
}

if ($FailOnAttentionSync -and $hasAttentionSync) {
    throw (
        "Execution sync attention threshold reached: latest_is_attention={0}, recent_attention_syncs={1}, threshold={2}" -f
        $snapshot.execution_sync.latest_is_attention,
        $snapshot.execution_sync.recent_attention_count,
        [Math]::Max($AttentionSyncThreshold, 1)
    )
}
