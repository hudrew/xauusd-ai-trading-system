param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$ConfigPath = "configs\mt5_paper_pullback_sell_v4_pullback_depth_0_26.yaml",
    [string]$BaselineConfigPath = "configs\mt5_paper_pullback_sell_v4.yaml",
    [string]$BaselineReportDir = "reports\research_pullback_sell_v4",
    [string]$CandidateReportDir,
    [int]$CurrentMonitoringPort = 80,
    [int]$CandidateMonitoringPort = 8765,
    [string]$CurrentDailyCheckJson,
    [string]$CandidateDailyCheckJson,
    [string]$CurrentExecutionAuditJson,
    [string]$CandidateExecutionAuditJson,
    [switch]$SkipCurrentDailyCheck,
    [switch]$SkipCandidateDailyCheck,
    [switch]$RequireCurrentExecutionAudit,
    [switch]$RequireCandidateExecutionAudit,
    [switch]$Strict
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
$dailyCheckArchiveScriptPath = Join-Path $PSScriptRoot "mt5_pullback_sell_v4_daily_check_archive.ps1"
$executionAuditArchiveScriptPath = Join-Path $PSScriptRoot "mt5_execution_audit_archive.ps1"

if ($EnvFile) {
    Load-EnvFile -EnvFile (Resolve-AbsoluteProjectPath -PathValue $EnvFile)
}

$resolvedCandidateConfigPath = Resolve-Mt5Config -Mode "paper" -ConfigPath $ConfigPath
$resolvedBaselineConfigPath = Resolve-Mt5Config -Mode "paper" -ConfigPath $BaselineConfigPath
$resolvedBaselineReportDir = Resolve-AbsoluteProjectPath -PathValue $BaselineReportDir
$resolvedCandidateReportDir = if ($CandidateReportDir) {
    Resolve-AbsoluteProjectPath -PathValue $CandidateReportDir
}
else {
    $null
}

$resolvedCurrentDailyCheckJson = if ($CurrentDailyCheckJson) {
    Resolve-AbsoluteProjectPath -PathValue $CurrentDailyCheckJson
}
else {
    Join-Path (Get-DefaultMt5OpsCheckDir -Mode "paper" -ConfigPath $resolvedBaselineConfigPath) "latest.json"
}

$resolvedCandidateDailyCheckJson = if ($CandidateDailyCheckJson) {
    Resolve-AbsoluteProjectPath -PathValue $CandidateDailyCheckJson
}
else {
    Join-Path (Get-DefaultMt5OpsCheckDir -Mode "paper" -ConfigPath $resolvedCandidateConfigPath) "latest.json"
}

$resolvedCurrentExecutionAuditJson = if ($CurrentExecutionAuditJson) {
    Resolve-AbsoluteProjectPath -PathValue $CurrentExecutionAuditJson
}
else {
    Join-Path (Get-DefaultMt5ExecutionAuditDir -Mode "paper" -ConfigPath $resolvedBaselineConfigPath) "latest.json"
}

$resolvedCandidateExecutionAuditJson = if ($CandidateExecutionAuditJson) {
    Resolve-AbsoluteProjectPath -PathValue $CandidateExecutionAuditJson
}
else {
    Join-Path (Get-DefaultMt5ExecutionAuditDir -Mode "paper" -ConfigPath $resolvedCandidateConfigPath) "latest.json"
}

$currentExecutionAuditCanUseDailyCheck = (
    $RequireCurrentExecutionAudit -and
    -not $SkipCurrentDailyCheck -and
    -not $CurrentExecutionAuditJson
)
$candidateExecutionAuditCanUseDailyCheck = (
    $RequireCandidateExecutionAudit -and
    -not $SkipCandidateDailyCheck -and
    -not $CandidateExecutionAuditJson
)

if (-not $SkipCurrentDailyCheck -and -not $CurrentDailyCheckJson) {
    & $dailyCheckArchiveScriptPath `
        -EnvFile $EnvFile `
        -ConfigPath $resolvedBaselineConfigPath `
        -Port $CurrentMonitoringPort | Out-Null
}

if (-not $SkipCandidateDailyCheck -and -not $CandidateDailyCheckJson) {
    & $dailyCheckArchiveScriptPath `
        -EnvFile $EnvFile `
        -ConfigPath $resolvedCandidateConfigPath `
        -Port $CandidateMonitoringPort | Out-Null
}

if (
    $RequireCurrentExecutionAudit -and
    -not $CurrentExecutionAuditJson -and
    -not $currentExecutionAuditCanUseDailyCheck
) {
    & $executionAuditArchiveScriptPath `
        -EnvFile $EnvFile `
        -Mode "paper" `
        -ConfigPath $resolvedBaselineConfigPath | Out-Null
}

if (
    $RequireCandidateExecutionAudit -and
    -not $CandidateExecutionAuditJson -and
    -not $candidateExecutionAuditCanUseDailyCheck
) {
    & $executionAuditArchiveScriptPath `
        -EnvFile $EnvFile `
        -Mode "paper" `
        -ConfigPath $resolvedCandidateConfigPath | Out-Null
}

$arguments = @("promotion-gate")
if ($resolvedCandidateReportDir) {
    $arguments += @("--candidate-report-dir", $resolvedCandidateReportDir)
}
$arguments += @("--baseline-report-dir", $resolvedBaselineReportDir)

if ($SkipCurrentDailyCheck) {
    $arguments += "--skip-current-daily-check"
}
else {
    $arguments += @(
        "--current-daily-check-json",
        $resolvedCurrentDailyCheckJson,
        "--require-current-daily-check"
    )
}

if ($SkipCandidateDailyCheck) {
    $arguments += "--skip-candidate-daily-check"
}
else {
    $arguments += @(
        "--candidate-daily-check-json",
        $resolvedCandidateDailyCheckJson,
        "--require-candidate-daily-check"
    )
}

if (
    $resolvedCurrentExecutionAuditJson -and (
        $CurrentExecutionAuditJson -or
        (Test-Path $resolvedCurrentExecutionAuditJson) -or
        ($RequireCurrentExecutionAudit -and -not $currentExecutionAuditCanUseDailyCheck)
    )
) {
    $arguments += @("--current-execution-audit-json", $resolvedCurrentExecutionAuditJson)
}
if ($RequireCurrentExecutionAudit) {
    $arguments += "--require-current-execution-audit"
}

if (
    $resolvedCandidateExecutionAuditJson -and (
        $CandidateExecutionAuditJson -or
        (Test-Path $resolvedCandidateExecutionAuditJson) -or
        ($RequireCandidateExecutionAudit -and -not $candidateExecutionAuditCanUseDailyCheck)
    )
) {
    $arguments += @("--candidate-execution-audit-json", $resolvedCandidateExecutionAuditJson)
}
if ($RequireCandidateExecutionAudit) {
    $arguments += "--require-candidate-execution-audit"
}

if ($Strict) {
    $arguments += "--strict"
}

Invoke-Mt5Cli -ConfigPath $resolvedCandidateConfigPath -Arguments $arguments
