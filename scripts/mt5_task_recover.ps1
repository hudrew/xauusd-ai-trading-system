param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$TaskName,
    [string]$UserId = $env:USERNAME,
    [int]$RestartCount = 999,
    [int]$RestartIntervalMinutes = 1,
    [switch]$SkipTaskRestart,
    [switch]$TailLog,
    [int]$TailLines = 20,
    [int]$FreshnessWarningSeconds = 120
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

Ensure-Venv

$resolvedEnvFile = if ($EnvFile) {
    Resolve-AbsoluteProjectPath -PathValue $EnvFile
}
else {
    $Script:DefaultEnvFile
}

if (-not (Test-Path $resolvedEnvFile)) {
    throw "Env file not found: $resolvedEnvFile"
}

Load-EnvFile -EnvFile $resolvedEnvFile
$resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5TaskName -Mode $Mode -ConfigPath $resolvedConfigPath }

Stop-ScheduledTaskIfExists -TaskName $resolvedTaskName
Start-Sleep -Seconds 2

if (-not $SkipTaskRestart) {
    $registerScriptPath = Join-Path $PSScriptRoot "mt5_register_task.ps1"
    $registerArgs = @{
        Mode = $Mode
        EnvFile = $resolvedEnvFile
        ConfigPath = $resolvedConfigPath
        TaskName = $resolvedTaskName
        UserId = $UserId
        StartAfterRegister = $true
        Force = $true
        RestartCount = $RestartCount
        RestartIntervalMinutes = $RestartIntervalMinutes
    }
    & $registerScriptPath @registerArgs
}

Start-Sleep -Seconds 5

$statusScriptPath = Join-Path $PSScriptRoot "mt5_task_status.ps1"
$statusArgs = @{
    Mode = $Mode
    EnvFile = $resolvedEnvFile
    ConfigPath = $resolvedConfigPath
    TaskName = $resolvedTaskName
    TailLog = $TailLog
    TailLines = $TailLines
    FreshnessWarningSeconds = $FreshnessWarningSeconds
}

& $statusScriptPath @statusArgs
