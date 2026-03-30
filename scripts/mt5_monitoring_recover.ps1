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
    [switch]$SkipTaskRestart
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
Stop-PortListeners -Port $Port
Start-Sleep -Seconds 2

if (-not $SkipTaskRestart) {
    $registerArgs = @(
        "-Mode"
        $Mode
        "-EnvFile"
        $resolvedEnvFile
        "-ConfigPath"
        $resolvedConfigPath
        "-DashboardPath"
        $resolvedDashboardPath
        "-BindHost"
        $BindHost
        "-Port"
        "$Port"
        "-DecisionLimit"
        "$DecisionLimit"
        "-ExecutionLimit"
        "$ExecutionLimit"
        "-StaleAfterSeconds"
        "$StaleAfterSeconds"
        "-RefreshSeconds"
        "$RefreshSeconds"
        "-SnapshotIntervalSeconds"
        "$SnapshotIntervalSeconds"
        "-StartAfterRegister"
        "-Force"
    )
    if (-not [string]::IsNullOrWhiteSpace($Title)) {
        $registerArgs += @("-Title", $Title)
    }

    & (Join-Path $PSScriptRoot "mt5_monitoring_register_tasks.ps1") @registerArgs
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

& (Join-Path $PSScriptRoot "mt5_monitoring_task_status.ps1") `
    -Mode $Mode `
    -EnvFile $resolvedEnvFile `
    -ConfigPath $resolvedConfigPath `
    -DashboardPath $resolvedDashboardPath `
    -ServeTaskName $resolvedServeTaskName `
    -RefreshTaskName $resolvedRefreshTaskName `
    -TailLog `
    -TailLines 20
