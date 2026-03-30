param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$TaskName,
    [string]$OutputDir,
    [switch]$AsJson,
    [int]$ArchiveFreshnessWarningMinutes = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function Get-LastTaskResultDescription {
    param(
        [int64]$ResultCode
    )

    switch ($ResultCode) {
        0 { return "Success" }
        267008 { return "Task is ready to run" }
        267009 { return "Task is currently running" }
        267010 { return "Task is disabled" }
        267011 { return "Task has not run yet" }
        default { return "See Windows Task Scheduler last result code" }
    }
}

if ($EnvFile) {
    $resolvedEnvFile = Resolve-AbsoluteProjectPath -PathValue $EnvFile
    if (-not (Test-Path $resolvedEnvFile)) {
        throw "Env file not found: $resolvedEnvFile"
    }
    Load-EnvFile -EnvFile $resolvedEnvFile
}

$resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5DailyCheckTaskName -Mode $Mode -ConfigPath $resolvedConfigPath }
$resolvedOutputDir = Ensure-Directory -PathValue $(if ($OutputDir) { $OutputDir } else { Get-DefaultMt5OpsCheckDir -Mode $Mode -ConfigPath $resolvedConfigPath })
$latestJsonPath = Join-Path $resolvedOutputDir "latest.json"
$latestTextPath = Join-Path $resolvedOutputDir "latest.txt"

$task = Get-ScheduledTask -TaskName $resolvedTaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    if ($AsJson) {
        [ordered]@{
            mode = $Mode
            config_path = $resolvedConfigPath
            task_name = $resolvedTaskName
            health = "attention"
            status = "missing"
            output_dir = $resolvedOutputDir
            latest_json = $latestJsonPath
        } | ConvertTo-Json -Depth 6
        return
    }

    Write-Host ("task_name: {0}" -f $resolvedTaskName)
    Write-Host "status: missing"
    exit 1
}

$taskInfo = Get-ScheduledTaskInfo -TaskName $resolvedTaskName
$lastResult = [int64]$taskInfo.LastTaskResult
$latestSummary = $null
$latestJsonExists = Test-Path $latestJsonPath
$latestJsonUpdatedAt = $null
$latestJsonAgeSeconds = $null
if ($latestJsonExists) {
    $latestJsonItem = Get-Item -Path $latestJsonPath
    $latestJsonUpdatedAt = $latestJsonItem.LastWriteTime
    $latestJsonAgeSeconds = [Math]::Round(((Get-Date) - $latestJsonUpdatedAt).TotalSeconds, 0)
    $latestJsonText = Get-Content -Path $latestJsonPath -Raw
    $convertFromJsonCommand = Get-Command ConvertFrom-Json -ErrorAction Stop
    if ($convertFromJsonCommand.Parameters.ContainsKey("Depth")) {
        $latestSummary = $latestJsonText | ConvertFrom-Json -Depth 8
    }
    else {
        $latestSummary = $latestJsonText | ConvertFrom-Json
    }
}

$health = "ok"
$issues = @()
if (-not $task.Settings.Enabled) {
    $health = "attention"
    $issues += "TASK_DISABLED"
}
if ($lastResult -ne 0 -and $lastResult -ne 267008 -and $lastResult -ne 267009 -and $lastResult -ne 267011) {
    $health = "attention"
    $issues += "TASK_LAST_RESULT"
}
if (-not $latestJsonExists) {
    $health = "attention"
    $issues += "LATEST_JSON_MISSING"
}
elseif ($latestJsonAgeSeconds -gt ($ArchiveFreshnessWarningMinutes * 60)) {
    $health = "attention"
    $issues += "LATEST_JSON_STALE"
}
elseif ($null -ne $latestSummary -and [string]$latestSummary.health -ne "ok") {
    $health = "attention"
    $issues += "SUMMARY_ATTENTION"
}

$output = [ordered]@{
    mode = $Mode
    config_path = $resolvedConfigPath
    task_name = $resolvedTaskName
    health = $health
    issues = $issues
    state = [string]$task.State
    enabled = [bool]$task.Settings.Enabled
    last_run_time = $taskInfo.LastRunTime
    last_task_result = $lastResult
    last_task_result_hex = ("0x{0:X8}" -f $lastResult)
    last_task_result_description = Get-LastTaskResultDescription -ResultCode $lastResult
    next_run_time = $taskInfo.NextRunTime
    output_dir = $resolvedOutputDir
    latest_json = $latestJsonPath
    latest_json_exists = $latestJsonExists
    latest_json_updated_at = $latestJsonUpdatedAt
    latest_json_age_seconds = $latestJsonAgeSeconds
    latest_text = $latestTextPath
    summary_health = if ($null -ne $latestSummary) { $latestSummary.health } else { $null }
    summary_issue_count = if ($null -ne $latestSummary) { $latestSummary.issue_count } else { $null }
    summary_runtime_status = if ($null -ne $latestSummary) { $latestSummary.snapshot.runtime_status } else { $null }
    summary_latest_timestamp = if ($null -ne $latestSummary) { $latestSummary.snapshot.latest_timestamp } else { $null }
    summary_dashboard_age_seconds = if ($null -ne $latestSummary) { $latestSummary.monitoring.dashboard_age_seconds } else { $null }
}

if ($AsJson) {
    $output | ConvertTo-Json -Depth 6
    return
}

foreach ($entry in $output.GetEnumerator()) {
    Write-Host ("{0}: {1}" -f $entry.Key, $entry.Value)
}
