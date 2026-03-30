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

function ConvertTo-SingleQuotedLiteral {
    param(
        [string]$Value
    )

    return "'{0}'" -f $Value.Replace("'", "''")
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
$serveScriptPath = Join-Path $PSScriptRoot "mt5_monitoring_dashboard.ps1"
$refreshScriptPath = Join-Path $PSScriptRoot "mt5_monitoring_export_loop.ps1"

if (-not (Test-Path $serveScriptPath)) {
    throw "Monitoring serve script not found: $serveScriptPath"
}
if (-not (Test-Path $refreshScriptPath)) {
    throw "Monitoring refresh script not found: $refreshScriptPath"
}

$quotedMode = ConvertTo-SingleQuotedLiteral -Value $Mode
$quotedEnvFile = ConvertTo-SingleQuotedLiteral -Value $resolvedEnvFile
$quotedConfigPath = ConvertTo-SingleQuotedLiteral -Value $resolvedConfigPath
$quotedDashboardPath = ConvertTo-SingleQuotedLiteral -Value $resolvedDashboardPath
$quotedBindHost = ConvertTo-SingleQuotedLiteral -Value $BindHost
$quotedServeLogPath = ConvertTo-SingleQuotedLiteral -Value $resolvedServeLogPath
$quotedRefreshLogPath = ConvertTo-SingleQuotedLiteral -Value $resolvedRefreshLogPath
$quotedServeScriptPath = ConvertTo-SingleQuotedLiteral -Value $serveScriptPath
$quotedRefreshScriptPath = ConvertTo-SingleQuotedLiteral -Value $refreshScriptPath

$titleArgs = ""
if (-not [string]::IsNullOrWhiteSpace($Title)) {
    $titleArgs = " -Title {0}" -f (ConvertTo-SingleQuotedLiteral -Value $Title)
}

$serveCommand = (
    "& {0} -Mode {1} -EnvFile {2} -ConfigPath {3} -OutputPath {4} -Serve -BindHost {5} -Port {6} -DecisionLimit {7} -ExecutionLimit {8} -StaleAfterSeconds {9} -RefreshSeconds {10}{11} *>> {12}" -f
    $quotedServeScriptPath,
    $quotedMode,
    $quotedEnvFile,
    $quotedConfigPath,
    $quotedDashboardPath,
    $quotedBindHost,
    $Port,
    $DecisionLimit,
    $ExecutionLimit,
    $StaleAfterSeconds,
    $RefreshSeconds,
    $titleArgs,
    $quotedServeLogPath
)

$refreshCommand = (
    "& {0} -Mode {1} -EnvFile {2} -ConfigPath {3} -OutputPath {4} -IntervalSeconds {5} -DecisionLimit {6} -ExecutionLimit {7} -StaleAfterSeconds {8} -RefreshSeconds {9}{10} *>> {11}" -f
    $quotedRefreshScriptPath,
    $quotedMode,
    $quotedEnvFile,
    $quotedConfigPath,
    $quotedDashboardPath,
    [Math]::Max($SnapshotIntervalSeconds, 15),
    $DecisionLimit,
    $ExecutionLimit,
    $StaleAfterSeconds,
    $RefreshSeconds,
    $titleArgs,
    $quotedRefreshLogPath
)

$serveArgumentString = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-Command"
    ('"{0}"' -f $serveCommand)
) -join " "

$refreshArgumentString = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-Command"
    ('"{0}"' -f $refreshCommand)
) -join " "

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
    -Argument $serveArgumentString `
    -WorkingDirectory $Script:RootDir
$refreshAction = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument $refreshArgumentString `
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
