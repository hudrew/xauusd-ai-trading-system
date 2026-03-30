param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$TaskName,
    [switch]$AsJson,
    [switch]$TailLog,
    [int]$TailLines = 40
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_task_status.ps1"
& $scriptPath `
    -Mode "paper" `
    -EnvFile $EnvFile `
    -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" `
    -TaskName $TaskName `
    -AsJson:$AsJson `
    -TailLog:$TailLog `
    -TailLines $TailLines

