param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [Alias("Host")]
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 80,
    [int]$TailLines = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$recoverScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_monitoring_recover.ps1"
$checkScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_daily_check.ps1"

Write-Host "[monitoring-recover]" -ForegroundColor Cyan
& $recoverScriptPath `
    -EnvFile $EnvFile `
    -BindHost $BindHost `
    -Port $Port

Write-Host ""
Write-Host "[daily-check]" -ForegroundColor Cyan
& $checkScriptPath `
    -EnvFile $EnvFile `
    -Port $Port `
    -TailLines $TailLines
