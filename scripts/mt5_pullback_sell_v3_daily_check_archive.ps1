param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [int]$Port = 80,
    [int]$TailLines = 10,
    [int]$FreshnessWarningSeconds = 120,
    [int]$AttentionSyncThreshold = 1,
    [switch]$FailOnAttention,
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
$archiveTextPath = Join-Path $resolvedOutputDir ("daily_check_{0}.txt" -f $timestamp)
$latestTextPath = Join-Path $resolvedOutputDir "latest.txt"
$archiveJsonPath = Join-Path $resolvedOutputDir ("daily_check_{0}.json" -f $timestamp)
$latestJsonPath = Join-Path $resolvedOutputDir "latest.json"
$publicBaseUrl = "http://38.60.197.97/"
$jsonOutput = & $dailyCheckScriptPath `
    -EnvFile $EnvFile `
    -Port $Port `
    -FreshnessWarningSeconds $FreshnessWarningSeconds `
    -AttentionSyncThreshold $AttentionSyncThreshold `
    -AsJson
$jsonText = (@($jsonOutput) -join [Environment]::NewLine).Trim()
if ([string]::IsNullOrWhiteSpace($jsonText)) {
    throw "daily_check JSON output is empty"
}

$convertFromJsonCommand = Get-Command ConvertFrom-Json -ErrorAction Stop
if ($convertFromJsonCommand.Parameters.ContainsKey("Depth")) {
    $summary = $jsonText | ConvertFrom-Json -Depth 8
}
else {
    $summary = $jsonText | ConvertFrom-Json
}

Set-Content -Path $archiveJsonPath -Value $jsonText -Encoding UTF8

Start-Transcript -Path $archiveTextPath -Force | Out-Null
try {
    Write-Host "[archive-meta]" -ForegroundColor Cyan
    Write-Host ("checked_at: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
    Write-Host ("archive_text_path: {0}" -f $archiveTextPath)
    Write-Host ("archive_json_path: {0}" -f $archiveJsonPath)
    Write-Host ("latest_text_path: {0}" -f $latestTextPath)
    Write-Host ("latest_json_path: {0}" -f $latestJsonPath)
    Write-Host ("summary_health: {0}" -f $summary.health)
    Write-Host ("summary_issue_count: {0}" -f $summary.issue_count)
    Write-Host ("public_dashboard: {0}" -f $publicBaseUrl)
    Write-Host ("public_health: {0}health" -f $publicBaseUrl)
    Write-Host ""

    & $dailyCheckScriptPath `
        -EnvFile $EnvFile `
        -Port $Port `
        -TailLines $TailLines `
        -FreshnessWarningSeconds $FreshnessWarningSeconds `
        -AttentionSyncThreshold $AttentionSyncThreshold
}
finally {
    Stop-Transcript | Out-Null
}

Copy-Item -Path $archiveTextPath -Destination $latestTextPath -Force
Copy-Item -Path $archiveJsonPath -Destination $latestJsonPath -Force

Write-Host ("archive_text_saved: {0}" -f $archiveTextPath) -ForegroundColor Green
Write-Host ("archive_json_saved: {0}" -f $archiveJsonPath) -ForegroundColor Green
Write-Host ("latest_text_saved: {0}" -f $latestTextPath) -ForegroundColor Green
Write-Host ("latest_json_saved: {0}" -f $latestJsonPath) -ForegroundColor Green

if ($FailOnAttention -and [string]$summary.health -ne "ok") {
    throw ("Daily check archive captured attention state ({0} issues)" -f $summary.issue_count)
}
