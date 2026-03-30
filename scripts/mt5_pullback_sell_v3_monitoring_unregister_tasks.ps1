param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$ServeTaskName,
    [string]$RefreshTaskName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_monitoring_unregister_tasks.ps1"
& $scriptPath `
    -Mode "paper" `
    -EnvFile $EnvFile `
    -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" `
    -ServeTaskName $ServeTaskName `
    -RefreshTaskName $RefreshTaskName
