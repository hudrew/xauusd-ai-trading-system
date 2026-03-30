param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$DashboardPath,
    [Alias("Host")]
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8765,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [int]$SnapshotIntervalSeconds = 60,
    [string]$Title,
    [string]$ServeTaskName,
    [string]$RefreshTaskName,
    [string]$UserId = $env:USERNAME,
    [switch]$StartAfterRegister,
    [switch]$Force,
    [int]$RestartCount = 999,
    [int]$RestartIntervalMinutes = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function ConvertTo-ArgumentToken {
    param(
        [string]$Value
    )

    if ($null -eq $Value) {
        return '""'
    }

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    return '"' + $Value.Replace('"', '\"') + '"'
}

Ensure-Venv

$resolvedEnvFile = if ($EnvFile) {
    Resolve-AbsoluteProjectPath -PathValue $EnvFile
}
else {
    $Script:DefaultEnvFile
}

if (-not (Test-Path $resolvedEnvFile)) {
    throw "Env file not found: $resolvedEnvFile"
}

Load-EnvFile -EnvFile $resolvedEnvFile
$resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
$resolvedDashboardPath = if ($DashboardPath) {
    Resolve-AbsoluteProjectPath -PathValue $DashboardPath
}
else {
    Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringDashboardPath -Mode $Mode -ConfigPath $resolvedConfigPath)
}

$resolvedServeTaskName = if ($ServeTaskName) { $ServeTaskName } else { Get-DefaultMt5MonitoringTaskName -Mode $Mode -ConfigPath $resolvedConfigPath -Role "serve" }
$resolvedRefreshTaskName = if ($RefreshTaskName) { $RefreshTaskName } else { Get-DefaultMt5MonitoringTaskName -Mode $Mode -ConfigPath $resolvedConfigPath -Role "refresh" }
$resolvedUserId = if ([string]::IsNullOrWhiteSpace($UserId)) { $env:USERNAME } else { $UserId }
if ([string]::IsNullOrWhiteSpace($resolvedUserId)) {
    throw "UserId is required to register an interactive monitoring scheduled task."
}

$resolvedServeLogPath = Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringLogPath -Mode $Mode -ConfigPath $resolvedConfigPath -Role "serve")
$resolvedRefreshLogPath = Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringLogPath -Mode $Mode -ConfigPath $resolvedConfigPath -Role "refresh")

Ensure-Directory -PathValue (Split-Path -Parent $resolvedDashboardPath) | Out-Null
Ensure-Directory -PathValue (Split-Path -Parent $resolvedServeLogPath) | Out-Null
Ensure-Directory -PathValue (Split-Path -Parent $resolvedRefreshLogPath) | Out-Null

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$runnerScriptPath = Join-Path $PSScriptRoot "mt5_monitoring_task_runner.ps1"
if (-not (Test-Path $runnerScriptPath)) {
    throw "Monitoring runner script not found: $runnerScriptPath"
}

$serveArguments = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    $runnerScriptPath
    "-Mode"
    $Mode
    "-Role"
    "serve"
    "-EnvFile"
    $resolvedEnvFile
    "-ConfigPath"
    $resolvedConfigPath
    "-DashboardPath"
    $resolvedDashboardPath
    "-BindHost"
    $BindHost
    "-Port"
    "$Port"
    "-DecisionLimit"
    "$DecisionLimit"
    "-ExecutionLimit"
    "$ExecutionLimit"
    "-StaleAfterSeconds"
    "$StaleAfterSeconds"
    "-RefreshSeconds"
    "$RefreshSeconds"
    "-LogPath"
    $resolvedServeLogPath
)
if (-not [string]::IsNullOrWhiteSpace($Title)) {
    $serveArguments += @("-Title", $Title)
}

$refreshArguments = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    $runnerScriptPath
    "-Mode"
    $Mode
    "-Role"
    "refresh"
    "-EnvFile"
    $resolvedEnvFile
    "-ConfigPath"
    $resolvedConfigPath
    "-DashboardPath"
    $resolvedDashboardPath
    "-DecisionLimit"
    "$DecisionLimit"
    "-ExecutionLimit"
    "$ExecutionLimit"
    "-StaleAfterSeconds"
    "$StaleAfterSeconds"
    "-RefreshSeconds"
    "$RefreshSeconds"
    "-IntervalSeconds"
    "$([Math]::Max($SnapshotIntervalSeconds, 15))"
    "-LogPath"
    $resolvedRefreshLogPath
)
if (-not [string]::IsNullOrWhiteSpace($Title)) {
    $refreshArguments += @("-Title", $Title)
}

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $resolvedUserId
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount $RestartCount `
    -RestartInterval (New-TimeSpan -Minutes $RestartIntervalMinutes) `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal `
    -UserId $resolvedUserId `
    -LogonType Interactive `
    -RunLevel Highest

$serveAction = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument (($serveArguments | ForEach-Object { ConvertTo-ArgumentToken -Value ([string]$_) }) -join " ") `
    -WorkingDirectory $Script:RootDir
$refreshAction = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument (($refreshArguments | ForEach-Object { ConvertTo-ArgumentToken -Value ([string]$_) }) -join " ") `
    -WorkingDirectory $Script:RootDir

Register-ScheduledTask `
    -TaskName $resolvedServeTaskName `
    -Action $serveAction `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "XAUUSD AI monitoring serve task." `
    -Force:$Force | Out-Null

Register-ScheduledTask `
    -TaskName $resolvedRefreshTaskName `
    -Action $refreshAction `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "XAUUSD AI monitoring dashboard refresh task." `
    -Force:$Force | Out-Null

Write-Host "Monitoring scheduled tasks registered." -ForegroundColor Green
Write-Host "ServeTaskName: $resolvedServeTaskName"
Write-Host "RefreshTaskName: $resolvedRefreshTaskName"
Write-Host "EnvFile: $resolvedEnvFile"
Write-Host "ConfigPath: $resolvedConfigPath"
Write-Host "DashboardPath: $resolvedDashboardPath"
Write-Host "ServeLog: $resolvedServeLogPath"
Write-Host "RefreshLog: $resolvedRefreshLogPath"

if ($StartAfterRegister) {
    Start-ScheduledTask -TaskName $resolvedServeTaskName
    Start-ScheduledTask -TaskName $resolvedRefreshTaskName
    Write-Host "Monitoring scheduled tasks started." -ForegroundColor Green
}
