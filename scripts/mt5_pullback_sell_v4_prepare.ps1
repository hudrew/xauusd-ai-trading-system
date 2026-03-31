param(
    [Parameter(Position = 0)]
    [string]$EnvFile,
    [Parameter(Position = 1)]
    [string]$ReportJsonPath,
    [switch]$SkipReportImport,
    [switch]$RunLiveOnce,
    [int]$LoopIterations = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
Load-EnvFile -EnvFile $(if ($EnvFile) { $EnvFile } else { $Script:DefaultEnvFile })

$configPath = Resolve-Mt5Config -Mode "paper" -ConfigPath "configs\mt5_paper_pullback_sell_v4.yaml"

if (-not $SkipReportImport) {
    if (-not $ReportJsonPath) {
        throw "ReportJsonPath is required unless -SkipReportImport is specified."
    }

    $resolvedReportJsonPath = Resolve-AbsoluteProjectPath -PathValue $ReportJsonPath
    if (-not (Test-Path $resolvedReportJsonPath)) {
        throw "Report JSON not found: $resolvedReportJsonPath"
    }

    Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("report-import", $resolvedReportJsonPath)
    Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("reports", "latest")
}

Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("host-check", "--strict")
Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("preflight", "--strict")
Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("deploy-gate", "--strict")

if ($RunLiveOnce) {
    Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("live-once", "--require-deploy-gate", "--require-preflight")
}

if ($LoopIterations -gt 0) {
    Invoke-Mt5Cli -ConfigPath $configPath -Arguments @("live-loop", "--iterations", [string]$LoopIterations, "--require-deploy-gate", "--require-preflight")
}
