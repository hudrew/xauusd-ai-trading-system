param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$TaskName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

if ($EnvFile) {
    $resolvedEnvFile = Resolve-AbsoluteProjectPath -PathValue $EnvFile
    if (-not (Test-Path $resolvedEnvFile)) {
        throw "Env file not found: $resolvedEnvFile"
    }
    Load-EnvFile -EnvFile $resolvedEnvFile
}

$resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5DailyCheckTaskName -Mode $Mode -ConfigPath $resolvedConfigPath }

$task = Get-ScheduledTask -TaskName $resolvedTaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host ("task_missing: {0}" -f $resolvedTaskName)
    return
}

Unregister-ScheduledTask -TaskName $resolvedTaskName -Confirm:$false
Write-Host ("task_removed: {0}" -f $resolvedTaskName) -ForegroundColor Green
