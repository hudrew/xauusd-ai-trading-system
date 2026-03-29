param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [string]$EnvFile,
    [string]$LogDir,
    [int]$KeepFiles = 20,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function Write-TaskRunnerLogLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    Add-Content -Path $LogPath -Value ("[{0}] {1}" -f $timestamp, $Message)
}

function Remove-ExpiredTaskLogs {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DirectoryPath,
        [int]$KeepFiles = 20
    )

    if ($KeepFiles -lt 1 -or -not (Test-Path $DirectoryPath)) {
        return
    }

    $filesToRemove = Get-ChildItem -Path $DirectoryPath -Filter "*.log" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $KeepFiles

    foreach ($file in $filesToRemove) {
        Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
    }
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

$resolvedLogDir = Ensure-Directory -PathValue $(if ($LogDir) { $LogDir } else { Get-DefaultMt5TaskLogDir -Mode $Mode })
$loopScriptName = if ($Mode -eq "prod") { "mt5_prod_loop.ps1" } else { "mt5_paper_loop.ps1" }
$loopScriptPath = Join-Path $PSScriptRoot $loopScriptName
if (-not (Test-Path $loopScriptPath)) {
    throw "Loop script not found: $loopScriptPath"
}

$logFileName = "run_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff")
$logPath = Join-Path $resolvedLogDir $logFileName
$exitCode = 0
$failureMessage = $null

Write-TaskRunnerLogLine -LogPath $logPath -Message ("task_runner_started mode={0} env_file={1} loop_script={2}" -f $Mode, $resolvedEnvFile, $loopScriptPath)

Push-Location $Script:RootDir
try {
    $global:LASTEXITCODE = 0
    & $loopScriptPath $resolvedEnvFile @CliArgs *>> $logPath
    if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
        $exitCode = $LASTEXITCODE
    }
}
catch {
    $exitCode = if ($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) { $LASTEXITCODE } else { 1 }
    $failureMessage = $_.Exception.Message
    Write-TaskRunnerLogLine -LogPath $logPath -Message ("task_runner_failed mode={0} error={1}" -f $Mode, $failureMessage)
}
finally {
    Pop-Location
    Write-TaskRunnerLogLine -LogPath $logPath -Message ("task_runner_finished mode={0} exit_code={1}" -f $Mode, $exitCode)
    Remove-ExpiredTaskLogs -DirectoryPath $resolvedLogDir -KeepFiles $KeepFiles
}

if ($failureMessage) {
    Write-Host "Task runner failed." -ForegroundColor Red
    Write-Host "Mode: $Mode"
    Write-Host "EnvFile: $resolvedEnvFile"
    Write-Host "LogFile: $logPath"
    Write-Host "Error: $failureMessage"
}

exit $exitCode
