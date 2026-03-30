param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [switch]$StartAfterRegister,
    [switch]$Force,
    [string]$TaskName,
    [string]$UserId = $env:USERNAME,
    [int]$RestartCount = 999,
    [int]$RestartIntervalMinutes = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_register_task.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v3.yaml"
        TaskName = $TaskName
        UserId = $UserId
        StartAfterRegister = $StartAfterRegister
        Force = $Force
        RestartCount = $RestartCount
        RestartIntervalMinutes = $RestartIntervalMinutes
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
