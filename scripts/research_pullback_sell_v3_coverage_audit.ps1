param(
    [Parameter(Position = 0)]
    [string]$OutputPath,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$JsonPaths
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv
$resolvedOutputPath = if ($OutputPath) {
    Resolve-AbsoluteProjectPath -PathValue $OutputPath
}
else {
    Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_coverage_audit_latest.json"
}

$resolvedJsonPaths = @()
if ($JsonPaths.Count -gt 0) {
    foreach ($jsonPath in $JsonPaths) {
        $resolvedJsonPaths += Resolve-AbsoluteProjectPath -PathValue $jsonPath
    }
}
else {
    $resolvedJsonPaths = @(
        (Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_probe_acceptance_150000_local.json"),
        (Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_probe_acceptance_300000_local.json"),
        (Join-Path $Script:RootDir "tmp\research_pullback_sell_v3_probe_acceptance_500000_local.json")
    )
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $Script:RootDir "src")
    & $Script:VenvPython -m xauusd_ai_system.cli report-audit $resolvedJsonPaths --output $resolvedOutputPath
}
finally {
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }
}
