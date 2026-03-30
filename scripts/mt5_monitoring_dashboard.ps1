param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$OutputPath,
    [string]$Host = "127.0.0.1",
    [int]$Port = 8765,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [string]$Title,
    [switch]$Serve
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

Ensure-Venv

$resolvedEnvFile = if ($EnvFile) {
    Resolve-AbsoluteProjectPath -PathValue $EnvFile
}
else {
    $Script:DefaultEnvFile
}

if (Test-Path $resolvedEnvFile) {
    Load-EnvFile -EnvFile $resolvedEnvFile
}

$resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
$configSlug = Get-Mt5ConfigSlug -Mode $Mode -ConfigPath $resolvedConfigPath
$defaultDashboardName = if ($configSlug) { "$configSlug.html" } else { "$Mode.html" }
$defaultOutputPath = Join-Path $Script:RootDir "var\xauusd_ai\dashboards\$defaultDashboardName"
$resolvedOutputPath = if ($OutputPath) {
    Resolve-AbsoluteProjectPath -PathValue $OutputPath
}
else {
    $defaultOutputPath
}

$cliArgs = @(
    "monitoring"
)

if ($Serve) {
    $cliArgs += @(
        "serve"
        "--host"
        $Host
        "--port"
        "$Port"
        "--decision-limit"
        "$DecisionLimit"
        "--execution-limit"
        "$ExecutionLimit"
        "--stale-after-seconds"
        "$StaleAfterSeconds"
        "--refresh-seconds"
        "$RefreshSeconds"
    )
    if ($Title) {
        $cliArgs += @("--title", $Title)
    }
}
else {
    $dashboardDir = Split-Path -Parent $resolvedOutputPath
    if (-not [string]::IsNullOrWhiteSpace($dashboardDir)) {
        Ensure-Directory -PathValue $dashboardDir | Out-Null
    }
    $cliArgs += @(
        "export-html"
        $resolvedOutputPath
        "--decision-limit"
        "$DecisionLimit"
        "--execution-limit"
        "$ExecutionLimit"
        "--stale-after-seconds"
        "$StaleAfterSeconds"
        "--refresh-seconds"
        "$RefreshSeconds"
    )
    if ($Title) {
        $cliArgs += @("--title", $Title)
    }
}

Invoke-Mt5Cli -ConfigPath $resolvedConfigPath -Arguments $cliArgs
