param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [string]$ConfigPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
Load-EnvFile -EnvFile $(if ($EnvFile) { $EnvFile } else { $Script:DefaultEnvFile })
$configPath = Resolve-Mt5Config -ConfigPath $ConfigPath
Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("preflight", "--strict")
