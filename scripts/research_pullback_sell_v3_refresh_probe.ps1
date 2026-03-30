param(
    [Parameter(Position = 0)]
    [string]$CsvPath,
    [Parameter(Position = 1)]
    [string]$OutputPath,
    [Parameter(Position = 2, ValueFromRemainingArguments = $true)]
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
$resolvedOutputPath = if ($OutputPath) {
    Resolve-AbsoluteProjectPath -PathValue $OutputPath
}
else {
    Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_probe_acceptance_latest.json"
}
$configPath = Join-Path $Script:RootDir "configs\mvp_pullback_sell_research_v3_branch_gate.yaml"
$reportDir = Join-Path $Script:RootDir "reports\research_pullback_sell_v3_probe"

Invoke-Mt5Cli -ConfigPath $configPath -Arguments (@("acceptance", $resolvedCsvPath, "--report-dir", $reportDir) + $CliArgs)

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $Script:RootDir "src")
    & $Script:VenvPython -m xauusd_ai_system.cli report-export $resolvedOutputPath --report-dir $reportDir
}
finally {
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }
}
