param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "mt5_paper_loop.ps1"
& $scriptPath -EnvFile $EnvFile -ConfigPath "configs\mt5_paper_pullback_sell_v3.yaml" @CliArgs

