param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [Alias("Host")]
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 80,
    [int]$TailLines = 10,
    [int]$AttentionSyncThreshold = 1,
    [switch]$FailOnAttentionSync,
    [switch]$FailOnRuntimeIssue,
    [switch]$RecoverPaperTaskOnRuntimeIssue
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

$recoverScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v4_monitoring_recover.ps1"
$checkScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v4_daily_check.ps1"
$taskRecoverScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v4_task_recover.ps1"

if ($EnvFile) {
    $resolvedEnvFile = Resolve-AbsoluteProjectPath -PathValue $EnvFile
    if (-not (Test-Path $resolvedEnvFile)) {
        throw "Env file not found: $resolvedEnvFile"
    }
    Load-EnvFile -EnvFile $resolvedEnvFile
}

Write-Host "[monitoring-recover]" -ForegroundColor Cyan
& $recoverScriptPath `
    -EnvFile $EnvFile `
    -BindHost $BindHost `
    -Port $Port `
    -AttentionSyncThreshold $AttentionSyncThreshold `
    -FailOnAttentionSync:$FailOnAttentionSync `
    -FailOnRuntimeIssue:$FailOnRuntimeIssue

if ($RecoverPaperTaskOnRuntimeIssue) {
    $resolvedConfigPath = Resolve-Mt5Config -Mode "paper" -ConfigPath "configs\mt5_paper_pullback_sell_v4.yaml"
    $snapshot = Get-Mt5MonitoringSnapshot `
        -ConfigPath $resolvedConfigPath `
        -DecisionLimit 40 `
        -ExecutionLimit 40 `
        -StaleAfterSeconds 120
    if ($snapshot.runtime.status -ne "healthy") {
        Write-Host ""
        Write-Host "[paper-task-recover]" -ForegroundColor Cyan
        & $taskRecoverScriptPath `
            -EnvFile $EnvFile `
            -TailLog `
            -TailLines $TailLines `
            -FreshnessWarningSeconds 120
    }
}

Write-Host ""
Write-Host "[daily-check]" -ForegroundColor Cyan
& $checkScriptPath `
    -EnvFile $EnvFile `
    -Port $Port `
    -TailLines $TailLines
