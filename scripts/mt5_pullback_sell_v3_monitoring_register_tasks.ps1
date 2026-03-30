param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$DashboardPath,
    [Alias("Host")]
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8765,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [int]$SnapshotIntervalSeconds = 60,
    [string]$Title,
    [string]$ServeTaskName,
    [string]$RefreshTaskName,
    [string]$UserId = $env:USERNAME,
    [switch]$StartAfterRegister,
    [switch]$Force,
    [int]$RestartCount = 999,
    [int]$RestartIntervalMinutes = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_monitoring_register_tasks.ps1"
& $scriptPath `
    -Mode "paper" `
    -EnvFile $EnvFile `
    -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" `
    -DashboardPath $DashboardPath `
    -BindHost $BindHost `
    -Port $Port `
    -DecisionLimit $DecisionLimit `
    -ExecutionLimit $ExecutionLimit `
    -StaleAfterSeconds $StaleAfterSeconds `
    -RefreshSeconds $RefreshSeconds `
    -SnapshotIntervalSeconds $SnapshotIntervalSeconds `
    -Title $Title `
    -ServeTaskName $ServeTaskName `
    -RefreshTaskName $RefreshTaskName `
    -UserId $UserId `
    -StartAfterRegister:$StartAfterRegister `
    -Force:$Force `
    -RestartCount $RestartCount `
    -RestartIntervalMinutes $RestartIntervalMinutes
