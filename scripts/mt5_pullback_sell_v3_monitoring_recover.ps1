param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [Alias("Host")]
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 80,
    [string]$DashboardPath,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [int]$SnapshotIntervalSeconds = 60,
    [string]$Title,
    [string]$ServeTaskName,
    [string]$RefreshTaskName,
    [int]$AttentionSyncThreshold = 1,
    [switch]$FailOnAttentionSync,
    [switch]$FailOnRuntimeIssue,
    [switch]$SkipTaskRestart,
    [switch]$SkipProcessCleanup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_monitoring_recover.ps1"
$previousEnvMode = $env:XAUUSD_AI_ENV

try {
    $env:XAUUSD_AI_ENV = "paper"

    $scriptArgs = @{
        EnvFile = $EnvFile
        ConfigPath = "configs\mt5_paper_pullback_sell_v3.yaml"
        BindHost = $BindHost
        Port = $Port
        DashboardPath = $DashboardPath
        DecisionLimit = $DecisionLimit
        ExecutionLimit = $ExecutionLimit
        StaleAfterSeconds = $StaleAfterSeconds
        RefreshSeconds = $RefreshSeconds
        SnapshotIntervalSeconds = $SnapshotIntervalSeconds
        Title = $Title
        ServeTaskName = $ServeTaskName
        RefreshTaskName = $RefreshTaskName
        AttentionSyncThreshold = $AttentionSyncThreshold
        FailOnAttentionSync = $FailOnAttentionSync
        FailOnRuntimeIssue = $FailOnRuntimeIssue
        SkipTaskRestart = $SkipTaskRestart
        SkipProcessCleanup = $SkipProcessCleanup
    }

    & $scriptPath @scriptArgs
}
finally {
    if ($null -eq $previousEnvMode) {
        Remove-Item Env:XAUUSD_AI_ENV -ErrorAction SilentlyContinue
    }
    else {
        $env:XAUUSD_AI_ENV = $previousEnvMode
    }
}
