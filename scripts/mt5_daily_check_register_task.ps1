param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$ArchiveScriptPath,
    [string]$TaskName,
    [string]$UserId = $env:USERNAME,
    [ValidateRange(1, 1440)]
    [int]$IntervalMinutes = 15,
    [ValidateRange(0, 1440)]
    [int]$StartDelayMinutes = 1,
    [int]$FreshnessWarningSeconds = 120,
    [int]$AttentionSyncThreshold = 1,
    [string]$OutputDir,
    [switch]$StartAfterRegister,
    [switch]$Force
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
$resolvedArchiveScriptPath = if ($ArchiveScriptPath) {
    Resolve-AbsoluteProjectPath -PathValue $ArchiveScriptPath
}
else {
    throw "ArchiveScriptPath is required."
}
if (-not (Test-Path $resolvedArchiveScriptPath)) {
    throw "Daily check archive script not found: $resolvedArchiveScriptPath"
}

$resolvedTaskName = if ($TaskName) { $TaskName } else { Get-DefaultMt5DailyCheckTaskName -Mode $Mode -ConfigPath $resolvedConfigPath }
$resolvedUserId = if ([string]::IsNullOrWhiteSpace($UserId)) { $env:USERNAME } else { $UserId }
if ([string]::IsNullOrWhiteSpace($resolvedUserId)) {
    throw "UserId is required to register the daily check task."
}
$resolvedOutputDir = Ensure-Directory -PathValue $(if ($OutputDir) { $OutputDir } else { Get-DefaultMt5OpsCheckDir -Mode $Mode -ConfigPath $resolvedConfigPath })

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$archiveArguments = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    $resolvedArchiveScriptPath
    $resolvedEnvFile
    "-FreshnessWarningSeconds"
    "$FreshnessWarningSeconds"
    "-AttentionSyncThreshold"
    "$AttentionSyncThreshold"
    "-OutputDir"
    $resolvedOutputDir
    "-FailOnAttention"
)

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At ((Get-Date).AddMinutes($StartDelayMinutes)) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal `
    -UserId $resolvedUserId `
    -LogonType Interactive `
    -RunLevel Highest
$action = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument (($archiveArguments | ForEach-Object { ConvertTo-ArgumentToken -Value ([string]$_) }) -join " ") `
    -WorkingDirectory $Script:RootDir

Register-ScheduledTask `
    -TaskName $resolvedTaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "XAUUSD AI $Mode daily check archive task." `
    -Force:$Force | Out-Null

Write-Host "Daily check scheduled task registered." -ForegroundColor Green
Write-Host ("TaskName: {0}" -f $resolvedTaskName)
Write-Host ("Mode: {0}" -f $Mode)
Write-Host ("EnvFile: {0}" -f $resolvedEnvFile)
Write-Host ("ConfigPath: {0}" -f $resolvedConfigPath)
Write-Host ("ArchiveScriptPath: {0}" -f $resolvedArchiveScriptPath)
Write-Host ("OutputDir: {0}" -f $resolvedOutputDir)
Write-Host ("IntervalMinutes: {0}" -f $IntervalMinutes)
Write-Host ("StartDelayMinutes: {0}" -f $StartDelayMinutes)
Write-Host ("FreshnessWarningSeconds: {0}" -f $FreshnessWarningSeconds)
Write-Host ("AttentionSyncThreshold: {0}" -f $AttentionSyncThreshold)

if ($StartAfterRegister) {
    Start-ScheduledTask -TaskName $resolvedTaskName
    Write-Host "Daily check scheduled task started." -ForegroundColor Green
}
