param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$OutputPath,
    [string]$Host = "127.0.0.1",
    [int]$Port = 8765,
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
& $scriptPath `
    -Mode "paper" `
    -EnvFile $EnvFile `
    -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" `
    -OutputPath $OutputPath `
    -Host $Host `
    -Port $Port `
    -DecisionLimit $DecisionLimit `
    -ExecutionLimit $ExecutionLimit `
    -StaleAfterSeconds $StaleAfterSeconds `
    -RefreshSeconds $RefreshSeconds `
    -Title $Title `
    -Serve:$Serve
