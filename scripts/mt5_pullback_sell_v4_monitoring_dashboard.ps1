param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$OutputPath,
    [Alias("Host")]
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 80,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [string]$Title,
    [switch]$Serve
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_monitoring_dashboard.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v4.yaml"
        OutputPath = $OutputPath
        BindHost = $BindHost
        Port = $Port
        DecisionLimit = $DecisionLimit
        ExecutionLimit = $ExecutionLimit
        StaleAfterSeconds = $StaleAfterSeconds
        RefreshSeconds = $RefreshSeconds
        Title = $Title
        Serve = $Serve
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
