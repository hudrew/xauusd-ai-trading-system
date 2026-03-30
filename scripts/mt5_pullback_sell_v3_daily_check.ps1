param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [int]$Port = 80,
    [int]$TailLines = 10,
    [int]$FreshnessWarningSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

$paperStatusScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_task_status.ps1"
$monitoringStatusScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v3_monitoring_task_status.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

function Get-FirstMixName {
    param(
        [object[]]$Rows
    )

    if ($null -eq $Rows -or $Rows.Count -eq 0) {
        return $null
    }

    return [string]$Rows[0].name
}

try {
    $env:XAUUSD_AI_ENV = "paper"

    if ($EnvFile) {
        $resolvedEnvFile = Resolve-AbsoluteProjectPath -PathValue $EnvFile
        if (-not (Test-Path $resolvedEnvFile)) {
            throw "Env file not found: $resolvedEnvFile"
        }
        Load-EnvFile -EnvFile $resolvedEnvFile
    }

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

    Write-Host ""
    Write-Host "[monitoring-snapshot]" -ForegroundColor Cyan

    try {
        $resolvedConfigPath = Resolve-Mt5Config -Mode "paper" -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml"
        $snapshot = Get-Mt5MonitoringSnapshot `
            -ConfigPath $resolvedConfigPath `
            -DecisionLimit 40 `
            -ExecutionLimit 40 `
            -StaleAfterSeconds $FreshnessWarningSeconds

        Write-Host ("runtime_status: {0}" -f $snapshot.runtime.status)
        Write-Host ("latest_sync_status: {0}" -f $snapshot.execution_sync.latest_status)
        Write-Host ("latest_sync_origin: {0}" -f $snapshot.execution_sync.latest_origin)
        Write-Host ("latest_sync_attention: {0}" -f $snapshot.execution_sync.latest_is_attention)
        Write-Host ("recent_submission_syncs: {0}" -f $snapshot.execution_sync.recent_submission_count)
        Write-Host ("recent_reconcile_syncs: {0}" -f $snapshot.execution_sync.recent_reconcile_count)
        Write-Host ("recent_close_events: {0}" -f $snapshot.execution_sync.recent_close_event_count)
        Write-Host ("recent_tp_close_events: {0}" -f $snapshot.execution_sync.recent_tp_close_count)
        Write-Host ("recent_sl_close_events: {0}" -f $snapshot.execution_sync.recent_sl_close_count)
        Write-Host ("recent_manual_close_events: {0}" -f $snapshot.execution_sync.recent_manual_close_count)
        Write-Host ("recent_expert_close_events: {0}" -f $snapshot.execution_sync.recent_expert_close_count)
        Write-Host ("recent_attention_syncs: {0}" -f $snapshot.execution_sync.recent_attention_count)
        Write-Host ("top_close_status: {0}" -f (Get-FirstMixName -Rows $snapshot.pressure.execution_sync_close_statuses))
        Write-Host ("top_deal_reason: {0}" -f (Get-FirstMixName -Rows $snapshot.pressure.execution_sync_deal_reasons))
    }
    catch {
        Write-Host ("monitoring_snapshot_error: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}
catch {
    throw
}
finally {
    if ($null -eq $previousEnvMode) {
        Remove-Item Env:XAUUSD_AI_ENV -ErrorAction SilentlyContinue
    }
    else {
        $env:XAUUSD_AI_ENV = $previousEnvMode
    }
}
