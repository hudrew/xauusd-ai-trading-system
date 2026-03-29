param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$TaskName,
    [string]$LogDir,
    [switch]$AsJson,
    [switch]$TailLog,
    [int]$TailLines = 40
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function Get-ActionArgumentValue {
    param(
        [string]$Arguments,
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Arguments)) {
        return $null
    }

    $quotedPattern = '-{0}\s+"([^"]+)"' -f [regex]::Escape($Name)
    $quotedMatch = [regex]::Match($Arguments, $quotedPattern)
    if ($quotedMatch.Success) {
        return $quotedMatch.Groups[1].Value
    }

    $plainPattern = '-{0}\s+([^\s]+)' -f [regex]::Escape($Name)
    $plainMatch = [regex]::Match($Arguments, $plainPattern)
    if ($plainMatch.Success) {
        return $plainMatch.Groups[1].Value
    }

    return $null
}

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

$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5TaskName -Mode $Mode }
$task = Get-ScheduledTask -TaskName $resolvedTaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "Scheduled task not found: $resolvedTaskName" -ForegroundColor Yellow
    exit 1
}

$taskInfo = Get-ScheduledTaskInfo -TaskName $resolvedTaskName
$action = $task.Actions | Select-Object -First 1
$actionArguments = if ($null -ne $action) { $action.Arguments } else { $null }
$runnerScriptPath = Get-ActionArgumentValue -Arguments $actionArguments -Name "File"
$envFileFromAction = Get-ActionArgumentValue -Arguments $actionArguments -Name "EnvFile"
$logDirFromAction = Get-ActionArgumentValue -Arguments $actionArguments -Name "LogDir"
$resolvedLogDir = if ($LogDir) {
    Resolve-AbsoluteProjectPath -PathValue $LogDir
}
elseif ($logDirFromAction) {
    $logDirFromAction
}
else {
    Get-DefaultMt5TaskLogDir -Mode $Mode
}
$latestLog = Get-LatestChildItem -PathValue $resolvedLogDir -Filter "*.log"
$lastResult = [int64]$taskInfo.LastTaskResult
$health = "ok"
if (-not $task.Settings.Enabled) {
    $health = "attention"
}
elseif ($task.State -ne "Running" -and $lastResult -ne 0 -and $lastResult -ne 267011) {
    $health = "attention"
}

$status = [ordered]@{
    task_name = $resolvedTaskName
    mode = $Mode
    health = $health
    state = [string]$task.State
    enabled = [bool]$task.Settings.Enabled
    last_run_time = $taskInfo.LastRunTime
    last_task_result = $lastResult
    last_task_result_hex = ("0x{0:X8}" -f $lastResult)
    last_task_result_description = Get-LastTaskResultDescription -ResultCode $lastResult
    next_run_time = $taskInfo.NextRunTime
    number_of_missed_runs = $taskInfo.NumberOfMissedRuns
    user_id = $task.Principal.UserId
    description = $task.Description
    execute = if ($null -ne $action) { $action.Execute } else { $null }
    arguments = $actionArguments
    working_directory = if ($null -ne $action) { $action.WorkingDirectory } else { $null }
    runner_script = $runnerScriptPath
    env_file = $envFileFromAction
    log_dir = $resolvedLogDir
    latest_log = if ($null -ne $latestLog) { $latestLog.FullName } else { $null }
    latest_log_updated_at = if ($null -ne $latestLog) { $latestLog.LastWriteTime } else { $null }
}

if ($AsJson) {
    $status | ConvertTo-Json -Depth 4
}
else {
    foreach ($entry in $status.GetEnumerator()) {
        Write-Host ("{0}: {1}" -f $entry.Key, $entry.Value)
    }
}

if ($TailLog) {
    if ($null -eq $latestLog) {
        Write-Host "Latest log not found in $resolvedLogDir" -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host ("Latest log tail: {0}" -f $latestLog.FullName) -ForegroundColor Cyan
        Get-Content -Path $latestLog.FullName -Tail $TailLines
    }
}
