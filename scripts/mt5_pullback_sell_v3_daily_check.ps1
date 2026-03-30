param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [int]$Port = 80,
    [int]$TailLines = 10,
    [int]$FreshnessWarningSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$paperStatusScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_task_status.ps1"
$monitoringStatusScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_monitoring_task_status.ps1"

Write-Host "[paper-task]" -ForegroundColor Cyan
& $paperStatusScriptPath `
    -EnvFile $EnvFile `
    -TailLog `
    -TailLines $TailLines `
    -FreshnessWarningSeconds $FreshnessWarningSeconds

Write-Host ""
Write-Host "[monitoring-task]" -ForegroundColor Cyan
& $monitoringStatusScriptPath `
    -EnvFile $EnvFile `
    -TailLog `
    -TailLines $TailLines

Write-Host ""
Write-Host "[monitoring-health]" -ForegroundColor Cyan

$healthUrl = "http://127.0.0.1:{0}/health" -f $Port
try {
    $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
    Write-Host ("health_url: {0}" -f $healthUrl)
    Write-Host ("health_status_code: {0}" -f $response.StatusCode)
    Write-Host ("health_body: {0}" -f $response.Content)
}
catch {
    Write-Host ("health_url: {0}" -f $healthUrl)
    Write-Host ("health_error: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}
