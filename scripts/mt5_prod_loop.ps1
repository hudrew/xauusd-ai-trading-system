param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$ConfigPath,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
Load-EnvFile -EnvFile $(if ($EnvFile) { $EnvFile } else { $Script:DefaultEnvFile })
$configPath = Resolve-Mt5Config -Mode "prod" -ConfigPath $ConfigPath
Invoke-Mt5Cli -ConfigPath $configPath -Arguments (@("live-loop", "--require-deploy-gate", "--require-preflight") + $CliArgs)
