param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$TaskName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_unregister_task.ps1"
& $scriptPath `
    -Mode "paper" `
    -EnvFile $EnvFile `
    -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" `
    -TaskName $TaskName

