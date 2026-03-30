param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$DashboardPath,
    [string]$ServeTaskName,
    [string]$RefreshTaskName,
    [string]$ServeLogPath,
    [string]$RefreshLogPath,
    [switch]$TailLog,
    [int]$TailLines = 40
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_monitoring_task_status.ps1"
& $scriptPath `
    -Mode "paper" `
    -EnvFile $EnvFile `
    -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" `
    -DashboardPath $DashboardPath `
    -ServeTaskName $ServeTaskName `
    -RefreshTaskName $RefreshTaskName `
    -ServeLogPath $ServeLogPath `
    -RefreshLogPath $RefreshLogPath `
    -TailLog:$TailLog `
    -TailLines $TailLines
