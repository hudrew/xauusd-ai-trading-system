param(
    [Parameter(Position = 0)]
    [string]$CsvPath,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
$resolvedCsvPath = if ($CsvPath) {
    Resolve-AbsoluteProjectPath -PathValue $CsvPath
}
else {
    Join-Path $Script:RootDir "tmp\xauusd_m1_history_100000.csv"
}
$configPath = Join-Path $Script:RootDir "configs\mvp_pullback_sell_research_v3_branch_gate.yaml"
$reportDir = Join-Path $Script:RootDir "reports\research_pullback_sell_v3"

Invoke-Mt5Cli -ConfigPath $configPath -Arguments (@("acceptance", $resolvedCsvPath, "--report-dir", $reportDir) + $CliArgs)
