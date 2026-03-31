param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$TaskName,
    [switch]$AsJson,
    [switch]$TailLog,
    [int]$TailLines = 40,
    [int]$FreshnessWarningSeconds = 120,
    [int]$WatchCount = 1,
    [int]$WatchIntervalSeconds = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_task_status.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v4.yaml"
        TaskName = $TaskName
        AsJson = $AsJson
        TailLog = $TailLog
        TailLines = $TailLines
        FreshnessWarningSeconds = $FreshnessWarningSeconds
        WatchCount = $WatchCount
        WatchIntervalSeconds = $WatchIntervalSeconds
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
