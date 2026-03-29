param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$TaskName,
    [string]$UserId = $env:USERNAME,
    [switch]$StartAfterRegister,
    [switch]$Force,
    [int]$RestartCount = 999,
    [int]$RestartIntervalMinutes = 1
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

if (-not (Test-Path $resolvedEnvFile)) {
    throw "Env file not found: $resolvedEnvFile"
}

Load-EnvFile -EnvFile $resolvedEnvFile

$taskRunnerPath = Join-Path $PSScriptRoot "mt5_task_runner.ps1"
$resolvedLogDir = Ensure-Directory -PathValue (Get-DefaultMt5TaskLogDir -Mode $Mode)
$loopScriptName = if ($Mode -eq "prod") { "mt5_prod_loop.ps1" } else { "mt5_paper_loop.ps1" }
$loopScriptPath = Join-Path $PSScriptRoot $loopScriptName
if (-not (Test-Path $taskRunnerPath)) {
    throw "Task runner script not found: $taskRunnerPath"
}
if (-not (Test-Path $loopScriptPath)) {
    throw "Loop script not found: $loopScriptPath"
}

$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5TaskName -Mode $Mode }
$resolvedUserId = if ([string]::IsNullOrWhiteSpace($UserId)) { $env:USERNAME } else { $UserId }
if ([string]::IsNullOrWhiteSpace($resolvedUserId)) {
    throw "UserId is required to register an interactive scheduled task."
}

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$argumentString = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    ('"{0}"' -f $taskRunnerPath)
    "-Mode"
    $Mode
    "-EnvFile"
    ('"{0}"' -f $resolvedEnvFile)
    "-LogDir"
    ('"{0}"' -f $resolvedLogDir)
) -join " "

$action = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument $argumentString `
    -WorkingDirectory $Script:RootDir

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
    -LogonType InteractiveToken `
    -RunLevel Highest

$description = "XAUUSD AI $Mode loop with deploy-gate, preflight and task logging."

Register-ScheduledTask `
    -TaskName $resolvedTaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description $description `
    -Force:$Force | Out-Null

Write-Host "Scheduled task registered." -ForegroundColor Green
Write-Host "TaskName: $resolvedTaskName"
Write-Host "Mode: $Mode"
Write-Host "UserId: $resolvedUserId"
Write-Host "EnvFile: $resolvedEnvFile"
Write-Host "TaskRunner: $taskRunnerPath"
Write-Host "LoopScript: $loopScriptPath"
Write-Host "LogDir: $resolvedLogDir"

if ($StartAfterRegister) {
    Start-ScheduledTask -TaskName $resolvedTaskName
    Write-Host "Scheduled task started." -ForegroundColor Green
}
