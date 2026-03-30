param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$TaskName,
    [string]$UserId = $env:USERNAME,
    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 15,
    [ValidateRange(0, 1440)]
    [int]$StartDelayMinutes = 1,
    [int]$FreshnessWarningSeconds = 120,
    [int]$AttentionSyncThreshold = 1,
    [switch]$StartAfterRegister,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_daily_check_register_task.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v3.yaml"
        ArchiveScriptPath = "scripts\mt5_pullback_sell_v3_daily_check_archive.ps1"
        TaskName = $TaskName
        UserId = $UserId
        IntervalMinutes = $IntervalMinutes
        StartDelayMinutes = $StartDelayMinutes
        FreshnessWarningSeconds = $FreshnessWarningSeconds
        AttentionSyncThreshold = $AttentionSyncThreshold
        StartAfterRegister = $StartAfterRegister
        Force = $Force
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
