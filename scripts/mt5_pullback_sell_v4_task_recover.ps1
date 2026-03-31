param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
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

$scriptPath = Join-Path $PSScriptRoot "mt5_task_recover.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v4.yaml"
        TaskName = $TaskName
        UserId = $UserId
        RestartCount = $RestartCount
        RestartIntervalMinutes = $RestartIntervalMinutes
        SkipTaskRestart = $SkipTaskRestart
        TailLog = $TailLog
        TailLines = $TailLines
        FreshnessWarningSeconds = $FreshnessWarningSeconds
    }

    & $scriptPath @scriptArgs
}
finally {
    if ($null -eq $previousEnvMode) {
        Remove-Item Env:XAUUSD_AI_ENV -ErrorAction SilentlyContinue
    }
    else {
        $env:XAUUSD_AI_ENV = $previousEnvMode
    }
}
