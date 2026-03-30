param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [int]$Port = 80,
    [int]$TailLines = 10,
    [int]$FreshnessWarningSeconds = 120,
    [int]$AttentionSyncThreshold = 1,
    [switch]$AsJson,
    [switch]$FailOnAttention
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

function Convert-JsonTextToObject {
    param(
        [Parameter(Mandatory = $true)]
        [string]$JsonText
    )

    $convertFromJsonCommand = Get-Command ConvertFrom-Json -ErrorAction Stop
    if ($convertFromJsonCommand.Parameters.ContainsKey("Depth")) {
        return ($JsonText | ConvertFrom-Json -Depth 8)
    }

    return ($JsonText | ConvertFrom-Json)
}

function Convert-SerializedDateValue {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [datetime]) {
        return [datetime]$Value
    }

    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    $normalizedText = $text.Replace('\/', '/')
    $dateMatch = [regex]::Match($normalizedText, '^/Date\((?<milliseconds>-?\d+)\)/$')
    if ($dateMatch.Success) {
        return ([DateTimeOffset]::FromUnixTimeMilliseconds([int64]$dateMatch.Groups["milliseconds"].Value)).LocalDateTime
    }

    try {
        return [datetime]::Parse($normalizedText, [System.Globalization.CultureInfo]::InvariantCulture)
    }
    catch {
        return $null
    }
}

function Invoke-JsonStatusScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [hashtable]$ScriptArgs
    )

    $scriptOutput = & $ScriptPath @ScriptArgs
    $jsonText = (@($scriptOutput) -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($jsonText)) {
        throw ("Script returned empty JSON output: {0}" -f $ScriptPath)
    }

    return (Convert-JsonTextToObject -JsonText $jsonText)
}

function New-DailyCheckIssue {
    param(
        [string]$Source,
        [string]$Code,
        [string]$Message
    )

    return [ordered]@{
        source = $Source
        code = $Code
        message = $Message
    }
}

function Get-HealthCheckSnapshot {
    param(
        [int]$Port
    )

    $healthUrl = "http://127.0.0.1:{0}/health" -f $Port
    $snapshot = [ordered]@{
        url = $healthUrl
        ok = $false
        status_code = $null
        body = $null
        error = $null
    }

    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
        $snapshot.ok = ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 300)
        $snapshot.status_code = [int]$response.StatusCode
        $snapshot.body = [string]$response.Content
    }
    catch {
        $snapshot.error = $_.Exception.Message
    }

    return $snapshot
}

function Get-DailyCheckSummary {
    param(
        [Parameter(Mandatory = $true)]
        [object]$PaperTaskStatus,
        [Parameter(Mandatory = $true)]
        [object]$MonitoringTaskStatus,
        [Parameter(Mandatory = $true)]
        [object]$HealthCheck,
        [Parameter(Mandatory = $true)]
        [object]$Snapshot,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [Parameter(Mandatory = $true)]
        [int]$FreshnessWarningSeconds,
        [Parameter(Mandatory = $true)]
        [int]$AttentionSyncThreshold
    )

    $issues = @()
    $paperLastRunTime = Convert-SerializedDateValue -Value $PaperTaskStatus.last_run_time
    $paperLatestLogUpdatedAt = Convert-SerializedDateValue -Value $PaperTaskStatus.latest_log_updated_at
    $dashboardUpdatedAt = Convert-SerializedDateValue -Value $MonitoringTaskStatus.dashboard_updated_at
    $serveLastRunTime = Convert-SerializedDateValue -Value $MonitoringTaskStatus.serve.last_run_time
    $serveLogUpdatedAt = Convert-SerializedDateValue -Value $MonitoringTaskStatus.serve.log_updated_at
    $refreshLastRunTime = Convert-SerializedDateValue -Value $MonitoringTaskStatus.refresh.last_run_time
    $refreshLogUpdatedAt = Convert-SerializedDateValue -Value $MonitoringTaskStatus.refresh.log_updated_at

    if ([string]$PaperTaskStatus.health -ne "ok") {
        $issues += (New-DailyCheckIssue `
            -Source "paper_task" `
            -Code "PAPER_TASK_ATTENTION" `
            -Message ("Paper task health is {0} (state={1})" -f $PaperTaskStatus.health, $PaperTaskStatus.state))
    }

    if ([string]$MonitoringTaskStatus.health -ne "ok") {
        $monitoringIssues = @($MonitoringTaskStatus.issues)
        if ($monitoringIssues.Count -gt 0) {
            foreach ($monitoringIssue in $monitoringIssues) {
                $issues += (New-DailyCheckIssue `
                    -Source ("monitoring_{0}" -f [string]$monitoringIssue.source) `
                    -Code ([string]$monitoringIssue.code) `
                    -Message ([string]$monitoringIssue.message))
            }
        }
        else {
            $issues += (New-DailyCheckIssue `
                -Source "monitoring" `
                -Code "MONITORING_ATTENTION" `
                -Message ("Monitoring task health is {0}" -f $MonitoringTaskStatus.health))
        }
    }

    if (-not [bool]$HealthCheck.ok) {
        $issues += (New-DailyCheckIssue `
            -Source "monitoring_health" `
            -Code "HEALTH_ENDPOINT_UNAVAILABLE" `
            -Message ("Monitoring health endpoint failed: {0}" -f $HealthCheck.error))
    }

    $dashboardAgeSeconds = $null
    if ([bool]$MonitoringTaskStatus.dashboard_exists -and $null -ne $dashboardUpdatedAt) {
        $dashboardAgeSeconds = [Math]::Round(((Get-Date) - $dashboardUpdatedAt).TotalSeconds, 0)
        if ($dashboardAgeSeconds -gt $FreshnessWarningSeconds) {
            $issues += (New-DailyCheckIssue `
                -Source "dashboard" `
                -Code "DASHBOARD_STALE" `
                -Message ("Dashboard file age {0}s exceeds threshold {1}s" -f $dashboardAgeSeconds, $FreshnessWarningSeconds))
        }
    }

    if ([string]$Snapshot.runtime.status -ne "healthy") {
        $issues += (New-DailyCheckIssue `
            -Source "snapshot" `
            -Code "RUNTIME_NOT_HEALTHY" `
            -Message ("Monitoring snapshot runtime status is {0}" -f $Snapshot.runtime.status))
    }

    $normalizedAttentionSyncThreshold = [Math]::Max($AttentionSyncThreshold, 1)
    if ([bool]$Snapshot.execution_sync.latest_is_attention) {
        $issues += (New-DailyCheckIssue `
            -Source "execution_sync" `
            -Code "LATEST_SYNC_ATTENTION" `
            -Message "Latest execution sync is marked as attention")
    }
    elseif ([int]$Snapshot.execution_sync.recent_attention_count -ge $normalizedAttentionSyncThreshold) {
        $issues += (New-DailyCheckIssue `
            -Source "execution_sync" `
            -Code "RECENT_SYNC_ATTENTION_THRESHOLD" `
            -Message ("Recent attention sync count {0} reached threshold {1}" -f $Snapshot.execution_sync.recent_attention_count, $normalizedAttentionSyncThreshold))
    }

    return [ordered]@{
        checked_at = (Get-Date).ToString("o")
        port = $Port
        freshness_warning_seconds = $FreshnessWarningSeconds
        attention_sync_threshold = $normalizedAttentionSyncThreshold
        health = $(if ($issues.Count -gt 0) { "attention" } else { "ok" })
        issue_count = $issues.Count
        issues = $issues
        paper_task = [ordered]@{
            task_name = $PaperTaskStatus.task_name
            health = $PaperTaskStatus.health
            state = $PaperTaskStatus.state
            enabled = $PaperTaskStatus.enabled
            last_run_time = $(if ($null -ne $paperLastRunTime) { $paperLastRunTime.ToString("o") } else { $null })
            last_task_result = $PaperTaskStatus.last_task_result
            last_task_result_hex = $PaperTaskStatus.last_task_result_hex
            last_task_result_description = $PaperTaskStatus.last_task_result_description
            latest_log = $PaperTaskStatus.latest_log
            latest_log_updated_at = $(if ($null -ne $paperLatestLogUpdatedAt) { $paperLatestLogUpdatedAt.ToString("o") } else { $null })
            latest_log_age_seconds = $PaperTaskStatus.latest_log_age_seconds
            latest_log_has_failure_pattern = $PaperTaskStatus.latest_log_has_failure_pattern
        }
        monitoring = [ordered]@{
            health = $MonitoringTaskStatus.health
            dashboard_path = $MonitoringTaskStatus.dashboard_path
            dashboard_exists = $MonitoringTaskStatus.dashboard_exists
            dashboard_updated_at = $(if ($null -ne $dashboardUpdatedAt) { $dashboardUpdatedAt.ToString("o") } else { $null })
            dashboard_age_seconds = $dashboardAgeSeconds
            dashboard_size_bytes = $MonitoringTaskStatus.dashboard_size_bytes
            health_url = $HealthCheck.url
            health_ok = $HealthCheck.ok
            health_status_code = $HealthCheck.status_code
            health_body = $HealthCheck.body
            health_error = $HealthCheck.error
            serve = [ordered]@{
                label = $MonitoringTaskStatus.serve.label
                task_name = $MonitoringTaskStatus.serve.task_name
                status = $MonitoringTaskStatus.serve.status
                health = $MonitoringTaskStatus.serve.health
                state = $MonitoringTaskStatus.serve.state
                enabled = $MonitoringTaskStatus.serve.enabled
                last_run_time = $(if ($null -ne $serveLastRunTime) { $serveLastRunTime.ToString("o") } else { $null })
                last_task_result = $MonitoringTaskStatus.serve.last_task_result
                last_task_result_hex = $MonitoringTaskStatus.serve.last_task_result_hex
                last_task_result_description = $MonitoringTaskStatus.serve.last_task_result_description
                log_path = $MonitoringTaskStatus.serve.log_path
                log_exists = $MonitoringTaskStatus.serve.log_exists
                log_updated_at = $(if ($null -ne $serveLogUpdatedAt) { $serveLogUpdatedAt.ToString("o") } else { $null })
                log_size_bytes = $MonitoringTaskStatus.serve.log_size_bytes
            }
            refresh = [ordered]@{
                label = $MonitoringTaskStatus.refresh.label
                task_name = $MonitoringTaskStatus.refresh.task_name
                status = $MonitoringTaskStatus.refresh.status
                health = $MonitoringTaskStatus.refresh.health
                state = $MonitoringTaskStatus.refresh.state
                enabled = $MonitoringTaskStatus.refresh.enabled
                last_run_time = $(if ($null -ne $refreshLastRunTime) { $refreshLastRunTime.ToString("o") } else { $null })
                last_task_result = $MonitoringTaskStatus.refresh.last_task_result
                last_task_result_hex = $MonitoringTaskStatus.refresh.last_task_result_hex
                last_task_result_description = $MonitoringTaskStatus.refresh.last_task_result_description
                log_path = $MonitoringTaskStatus.refresh.log_path
                log_exists = $MonitoringTaskStatus.refresh.log_exists
                log_updated_at = $(if ($null -ne $refreshLogUpdatedAt) { $refreshLogUpdatedAt.ToString("o") } else { $null })
                log_size_bytes = $MonitoringTaskStatus.refresh.log_size_bytes
            }
        }
        snapshot = [ordered]@{
            runtime_status = $Snapshot.runtime.status
            latest_timestamp = $Snapshot.runtime.latest_timestamp
            staleness_seconds = $Snapshot.runtime.staleness_seconds
            latest_sync_status = $Snapshot.execution_sync.latest_status
            latest_sync_origin = $Snapshot.execution_sync.latest_origin
            latest_sync_attention = $Snapshot.execution_sync.latest_is_attention
            recent_submission_syncs = $Snapshot.execution_sync.recent_submission_count
            recent_reconcile_syncs = $Snapshot.execution_sync.recent_reconcile_count
            recent_close_events = $Snapshot.execution_sync.recent_close_event_count
            recent_tp_close_events = $Snapshot.execution_sync.recent_tp_close_count
            recent_sl_close_events = $Snapshot.execution_sync.recent_sl_close_count
            recent_manual_close_events = $Snapshot.execution_sync.recent_manual_close_count
            recent_expert_close_events = $Snapshot.execution_sync.recent_expert_close_count
            recent_attention_syncs = $Snapshot.execution_sync.recent_attention_count
            top_close_status = Get-FirstMixName -Rows $Snapshot.pressure.execution_sync_close_statuses
            top_deal_reason = Get-FirstMixName -Rows $Snapshot.pressure.execution_sync_deal_reasons
            latest_equity = $Snapshot.paper.latest_equity
            latest_daily_pnl_pct = $Snapshot.paper.latest_daily_pnl_pct
            max_drawdown_pct = $Snapshot.paper.max_drawdown_pct
            latest_open_positions = $Snapshot.paper.latest_open_positions
            average_spread = $Snapshot.paper.average_spread
            max_spread = $Snapshot.paper.max_spread
        }
    }
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

    $paperTaskStatus = Invoke-JsonStatusScript `
        -ScriptPath $paperStatusScriptPath `
        -ScriptArgs @{
            EnvFile = $EnvFile
            AsJson = $true
            FreshnessWarningSeconds = $FreshnessWarningSeconds
        }
    $monitoringTaskStatus = Invoke-JsonStatusScript `
        -ScriptPath $monitoringStatusScriptPath `
        -ScriptArgs @{
            EnvFile = $EnvFile
            AsJson = $true
        }
    $healthCheck = Get-HealthCheckSnapshot -Port $Port
    $resolvedConfigPath = Resolve-Mt5Config -Mode "paper" -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml"
    $snapshot = Get-Mt5MonitoringSnapshot `
        -ConfigPath $resolvedConfigPath `
        -DecisionLimit 40 `
        -ExecutionLimit 40 `
        -StaleAfterSeconds $FreshnessWarningSeconds
    $summary = Get-DailyCheckSummary `
        -PaperTaskStatus $paperTaskStatus `
        -MonitoringTaskStatus $monitoringTaskStatus `
        -HealthCheck $healthCheck `
        -Snapshot $snapshot `
        -Port $Port `
        -FreshnessWarningSeconds $FreshnessWarningSeconds `
        -AttentionSyncThreshold $AttentionSyncThreshold

    if ($AsJson) {
        $summary | ConvertTo-Json -Depth 8
        if ($FailOnAttention -and [string]$summary.health -ne "ok") {
            exit 1
        }
        return
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
    Write-Host ("health_url: {0}" -f $summary.monitoring.health_url)
    if ([bool]$summary.monitoring.health_ok) {
        Write-Host ("health_status_code: {0}" -f $summary.monitoring.health_status_code)
        Write-Host ("health_body: {0}" -f $summary.monitoring.health_body)
    }
    else {
        Write-Host ("health_error: {0}" -f $summary.monitoring.health_error) -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "[monitoring-snapshot]" -ForegroundColor Cyan
    Write-Host ("runtime_status: {0}" -f $summary.snapshot.runtime_status)
    Write-Host ("latest_timestamp: {0}" -f $summary.snapshot.latest_timestamp)
    Write-Host ("staleness_seconds: {0}" -f $summary.snapshot.staleness_seconds)
    Write-Host ("latest_sync_status: {0}" -f $summary.snapshot.latest_sync_status)
    Write-Host ("latest_sync_origin: {0}" -f $summary.snapshot.latest_sync_origin)
    Write-Host ("latest_sync_attention: {0}" -f $summary.snapshot.latest_sync_attention)
    Write-Host ("recent_submission_syncs: {0}" -f $summary.snapshot.recent_submission_syncs)
    Write-Host ("recent_reconcile_syncs: {0}" -f $summary.snapshot.recent_reconcile_syncs)
    Write-Host ("recent_close_events: {0}" -f $summary.snapshot.recent_close_events)
    Write-Host ("recent_tp_close_events: {0}" -f $summary.snapshot.recent_tp_close_events)
    Write-Host ("recent_sl_close_events: {0}" -f $summary.snapshot.recent_sl_close_events)
    Write-Host ("recent_manual_close_events: {0}" -f $summary.snapshot.recent_manual_close_events)
    Write-Host ("recent_expert_close_events: {0}" -f $summary.snapshot.recent_expert_close_events)
    Write-Host ("recent_attention_syncs: {0}" -f $summary.snapshot.recent_attention_syncs)
    Write-Host ("top_close_status: {0}" -f $summary.snapshot.top_close_status)
    Write-Host ("top_deal_reason: {0}" -f $summary.snapshot.top_deal_reason)
    Write-Host ("latest_equity: {0}" -f $summary.snapshot.latest_equity)
    Write-Host ("latest_daily_pnl_pct: {0}" -f $summary.snapshot.latest_daily_pnl_pct)
    Write-Host ("max_drawdown_pct: {0}" -f $summary.snapshot.max_drawdown_pct)
    Write-Host ("latest_open_positions: {0}" -f $summary.snapshot.latest_open_positions)
    Write-Host ("average_spread: {0}" -f $summary.snapshot.average_spread)
    Write-Host ("max_spread: {0}" -f $summary.snapshot.max_spread)

    Write-Host ""
    Write-Host "[daily-check-summary]" -ForegroundColor Cyan
    Write-Host ("health: {0}" -f $summary.health)
    Write-Host ("issue_count: {0}" -f $summary.issue_count)
    Write-Host ("paper_task_health: {0}" -f $summary.paper_task.health)
    Write-Host ("monitoring_health: {0}" -f $summary.monitoring.health)
    Write-Host ("dashboard_age_seconds: {0}" -f $summary.monitoring.dashboard_age_seconds)
    if ($summary.issue_count -gt 0) {
        Write-Host ""
        foreach ($issue in @($summary.issues)) {
            Write-Host ("issue: source={0} code={1} message={2}" -f $issue.source, $issue.code, $issue.message) -ForegroundColor Yellow
        }
    }

    if ($FailOnAttention -and [string]$summary.health -ne "ok") {
        throw ("Daily check detected attention state ({0} issues)" -f $summary.issue_count)
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
