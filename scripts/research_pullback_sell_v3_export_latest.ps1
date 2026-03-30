param(
    [Parameter(Position = 0)]
    [string]$OutputPath,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
$resolvedOutputPath = if ($OutputPath) {
    Resolve-AbsoluteProjectPath -PathValue $OutputPath
}
else {
    Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_acceptance_latest.json"
}
$reportDir = Join-Path $Script:RootDir "reports\research_pullback_sell_v3"
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $Script:RootDir "src")
    & $Script:VenvPython -m xauusd_ai_system.cli report-export $resolvedOutputPath --report-dir $reportDir @CliArgs
}
finally {
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }
}
