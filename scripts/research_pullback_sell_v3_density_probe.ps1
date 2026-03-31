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
    Join-Path $Script:RootDir "tmp\xauusd_m1_history_150000_chunked_vps_full.csv"
}
$resolvedOutputPath = if ($OutputPath) {
    Resolve-AbsoluteProjectPath -PathValue $OutputPath
}
else {
    Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_density_probe_latest.json"
}
$configPath = Join-Path $Script:RootDir "configs\mvp_pullback_sell_research_v3_branch_gate.yaml"

Invoke-Mt5Cli -ConfigPath $configPath -Arguments (
    @(
        "pullback-density-probe",
        $resolvedCsvPath,
        "--config-path",
        $configPath,
        "--output",
        $resolvedOutputPath
    ) + $CliArgs
)
