param(
    [string]$EnvFile,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
Load-EnvFile -EnvFile $(if ($EnvFile) { $EnvFile } else { $Script:DefaultEnvFile })
$configPath = Join-Path $Script:RootDir "configs\mt5_prod.yaml"
Invoke-Mt5Cli -ConfigPath $configPath -Arguments (@("live-loop", "--require-deploy-gate", "--require-preflight") + $CliArgs)
