param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$TaskName,
    [string]$OutputDir,
    [switch]$AsJson,
    [int]$ArchiveFreshnessWarningMinutes = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_daily_check_task_status.ps1"

$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v4.yaml"
        TaskName = $TaskName
        OutputDir = $OutputDir
        AsJson = $AsJson
        ArchiveFreshnessWarningMinutes = $ArchiveFreshnessWarningMinutes
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
