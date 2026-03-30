param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$TaskName,
    [string]$LogDir,
    [switch]$AsJson,
    [switch]$TailLog,
    [int]$TailLines = 40,
    [int]$FreshnessWarningSeconds = 120,
    [int]$WatchCount = 1,
    [int]$WatchIntervalSeconds = 15
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

function Test-RecentFailurePattern {
    param(
        [string]$LogPath,
        [int]$TailLines = 80
    )

    if ([string]::IsNullOrWhiteSpace($LogPath) -or -not (Test-Path $LogPath)) {
        return $false
    }

    $recentLines = Get-Content -Path $LogPath -Tail $TailLines -ErrorAction SilentlyContinue
    foreach ($line in $recentLines) {
        if ($line -match "live_cycle_failed|task_runner_failed") {
            return $true
        }
    }

    return $false
}

function Get-TaskStatusSnapshot {
    param(
        [string]$Mode,
        [string]$ResolvedTaskName,
        [string]$ResolvedConfigPath,
        [string]$ResolvedLogDir,
        [int]$TailLines,
        [int]$FreshnessWarningSeconds
    )

    $task = Get-ScheduledTask -TaskName $ResolvedTaskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        throw "Scheduled task not found: $ResolvedTaskName"
    }

    $taskInfo = Get-ScheduledTaskInfo -TaskName $ResolvedTaskName
    $action = $task.Actions | Select-Object -First 1
    $actionArguments = if ($null -ne $action) { $action.Arguments } else { $null }
    $runnerScriptPath = Get-ActionArgumentValue -Arguments $actionArguments -Name "File"
    $envFileFromAction = Get-ActionArgumentValue -Arguments $actionArguments -Name "EnvFile"
    $configPathFromAction = Get-ActionArgumentValue -Arguments $actionArguments -Name "ConfigPath"
    $logDirFromAction = Get-ActionArgumentValue -Arguments $actionArguments -Name "LogDir"

    $effectiveLogDir = if ($ResolvedLogDir) {
        $ResolvedLogDir
    }
    elseif ($logDirFromAction) {
        $logDirFromAction
    }
    else {
        Get-DefaultMt5TaskLogDir -Mode $Mode -ConfigPath $ResolvedConfigPath
    }

    $latestLog = Get-LatestChildItem -PathValue $effectiveLogDir -Filter "*.log"
    $latestLogAgeSeconds = if ($null -ne $latestLog) {
        [Math]::Round(((Get-Date) - $latestLog.LastWriteTime).TotalSeconds, 0)
    }
    else {
        $null
    }
    $latestLogHasFailurePattern = if ($null -ne $latestLog) {
        Test-RecentFailurePattern -LogPath $latestLog.FullName -TailLines ([Math]::Max($TailLines, 80))
    }
    else {
        $false
    }

    $lastResult = [int64]$taskInfo.LastTaskResult
    $health = "ok"
    if (-not $task.Settings.Enabled) {
        $health = "attention"
    }
    elseif ($latestLogHasFailurePattern) {
        $health = "attention"
    }
    elseif ($task.State -eq "Running" -and $null -ne $latestLogAgeSeconds -and $latestLogAgeSeconds -gt $FreshnessWarningSeconds) {
        $health = "attention"
    }
    elseif ($task.State -ne "Running" -and $lastResult -ne 0 -and $lastResult -ne 267008 -and $lastResult -ne 267011) {
        $health = "attention"
    }

    return [ordered]@{
        task_name = $ResolvedTaskName
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
        config_path = $(if ($configPathFromAction) { $configPathFromAction } else { $ResolvedConfigPath })
        log_dir = $effectiveLogDir
        latest_log = if ($null -ne $latestLog) { $latestLog.FullName } else { $null }
        latest_log_updated_at = if ($null -ne $latestLog) { $latestLog.LastWriteTime } else { $null }
        latest_log_age_seconds = $latestLogAgeSeconds
        latest_log_has_failure_pattern = $latestLogHasFailurePattern
        freshness_warning_seconds = $FreshnessWarningSeconds
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
$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5TaskName -Mode $Mode -ConfigPath $resolvedConfigPath }
$resolvedLogDir = if ($LogDir) {
    Resolve-AbsoluteProjectPath -PathValue $LogDir
}
else {
    $null
}

$sampleCount = [Math]::Max($WatchCount, 1)
for ($sampleIndex = 1; $sampleIndex -le $sampleCount; $sampleIndex++) {
    try {
        $status = Get-TaskStatusSnapshot `
            -Mode $Mode `
            -ResolvedTaskName $resolvedTaskName `
            -ResolvedConfigPath $resolvedConfigPath `
            -ResolvedLogDir $resolvedLogDir `
            -TailLines $TailLines `
            -FreshnessWarningSeconds $FreshnessWarningSeconds
    }
    catch {
        Write-Host $_.Exception.Message -ForegroundColor Yellow
        exit 1
    }

    if ($AsJson) {
        $output = [ordered]@{
            sample = $sampleIndex
            sample_count = $sampleCount
        }
        foreach ($entry in $status.GetEnumerator()) {
            $output[$entry.Key] = $entry.Value
        }
        $output | ConvertTo-Json -Depth 4
    }
    else {
        if ($sampleCount -gt 1) {
            Write-Host ("sample: {0}/{1}" -f $sampleIndex, $sampleCount) -ForegroundColor Cyan
        }
        foreach ($entry in $status.GetEnumerator()) {
            Write-Host ("{0}: {1}" -f $entry.Key, $entry.Value)
        }
    }

    if ($TailLog) {
        $latestLogPath = $status["latest_log"]
        if ([string]::IsNullOrWhiteSpace($latestLogPath)) {
            Write-Host ("Latest log not found in {0}" -f $status["log_dir"]) -ForegroundColor Yellow
        }
        else {
            Write-Host ""
            Write-Host ("Latest log tail: {0}" -f $latestLogPath) -ForegroundColor Cyan
            Get-Content -Path $latestLogPath -Tail $TailLines
        }
    }

    if ($sampleIndex -lt $sampleCount) {
        if (-not $AsJson) {
            Write-Host ""
            Write-Host ("Waiting {0}s before next sample..." -f $WatchIntervalSeconds) -ForegroundColor DarkGray
            Write-Host ""
        }
        Start-Sleep -Seconds $WatchIntervalSeconds
    }
}
