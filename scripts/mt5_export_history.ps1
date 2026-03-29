param(
    [string]$EnvFile,
    [string]$OutputPath,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
Load-EnvFile -EnvFile $(if ($EnvFile) { $EnvFile } else { $Script:DefaultEnvFile })
$configPath = Resolve-Mt5Config
$resolvedOutputPath = if ($OutputPath) { $OutputPath } else { (Join-Path $Script:RootDir "tmp\xauusd_mt5_history.csv") }
Invoke-Mt5Cli -ConfigPath $configPath -Arguments (@("export-mt5-history", $resolvedOutputPath) + $CliArgs)
