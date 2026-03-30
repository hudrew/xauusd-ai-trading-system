param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$OutputPath,
    [int]$IntervalSeconds = 60,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [string]$Title
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
$resolvedOutputPath = if ($OutputPath) {
    Resolve-AbsoluteProjectPath -PathValue $OutputPath
}
else {
    Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringDashboardPath -Mode $Mode -ConfigPath $resolvedConfigPath)
}

$dashboardDir = Split-Path -Parent $resolvedOutputPath
if (-not [string]::IsNullOrWhiteSpace($dashboardDir)) {
    Ensure-Directory -PathValue $dashboardDir | Out-Null
}

$resolvedIntervalSeconds = [Math]::Max($IntervalSeconds, 15)
$resolvedTitle = if ([string]::IsNullOrWhiteSpace($Title)) { $null } else { $Title }

while ($true) {
    try {
        $invokeArgs = @(
            "monitoring"
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
        if ($resolvedTitle) {
            $invokeArgs += @("--title", $resolvedTitle)
        }

        Invoke-Mt5Cli -ConfigPath $resolvedConfigPath -Arguments $invokeArgs | Out-Null
        Write-Host ("[{0}] monitoring_snapshot_exported output={1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $resolvedOutputPath)
    }
    catch {
        Write-Host ("[{0}] monitoring_snapshot_export_failed error={1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $_.Exception.Message)
    }

    Start-Sleep -Seconds $resolvedIntervalSeconds
}
