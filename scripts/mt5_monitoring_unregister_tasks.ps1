param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$ServeTaskName,
    [string]$RefreshTaskName
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
$resolvedServeTaskName = if ($ServeTaskName) { $ServeTaskName } else { Get-DefaultMt5MonitoringTaskName -Mode $Mode -ConfigPath $resolvedConfigPath -Role "serve" }
$resolvedRefreshTaskName = if ($RefreshTaskName) { $RefreshTaskName } else { Get-DefaultMt5MonitoringTaskName -Mode $Mode -ConfigPath $resolvedConfigPath -Role "refresh" }

foreach ($taskName in @($resolvedServeTaskName, $resolvedRefreshTaskName)) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Host "Scheduled task not found: $taskName"
        continue
    }

    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Scheduled task removed." -ForegroundColor Green
    Write-Host "TaskName: $taskName"
}
