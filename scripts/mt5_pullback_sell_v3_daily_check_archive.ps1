param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [int]$Port = 80,
    [int]$TailLines = 10,
    [int]$FreshnessWarningSeconds = 120,
    [string]$OutputDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

$dailyCheckScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_daily_check.ps1"
$resolvedConfigPath = Resolve-Mt5Config -Mode "paper" -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml"
$configSlug = Get-Mt5ConfigSlug -Mode "paper" -ConfigPath $resolvedConfigPath
$defaultOutputDir = Join-Path $Script:RootDir "var\xauusd_ai\ops_checks\paper\$configSlug"
$resolvedOutputDir = Ensure-Directory -PathValue $(if ($OutputDir) { $OutputDir } else { $defaultOutputDir })

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archivePath = Join-Path $resolvedOutputDir ("daily_check_{0}.txt" -f $timestamp)
$latestPath = Join-Path $resolvedOutputDir "latest.txt"
$publicBaseUrl = "http://38.60.197.97/"

Start-Transcript -Path $archivePath -Force | Out-Null
try {
    Write-Host "[archive-meta]" -ForegroundColor Cyan
    Write-Host ("checked_at: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
    Write-Host ("archive_path: {0}" -f $archivePath)
    Write-Host ("public_dashboard: {0}" -f $publicBaseUrl)
    Write-Host ("public_health: {0}health" -f $publicBaseUrl)
    Write-Host ""

    & $dailyCheckScriptPath `
        -EnvFile $EnvFile `
        -Port $Port `
        -TailLines $TailLines `
        -FreshnessWarningSeconds $FreshnessWarningSeconds
}
finally {
    Stop-Transcript | Out-Null
}

Copy-Item -Path $archivePath -Destination $latestPath -Force

Write-Host ("archive_saved: {0}" -f $archivePath) -ForegroundColor Green
Write-Host ("latest_saved: {0}" -f $latestPath) -ForegroundColor Green
