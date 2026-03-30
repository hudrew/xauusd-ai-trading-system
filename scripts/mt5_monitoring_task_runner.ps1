param(
    [ValidateSet("paper", "prod")]
    [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" }),
    [ValidateSet("serve", "refresh")]
    [string]$Role,
    [string]$EnvFile,
    [string]$ConfigPath,
    [string]$DashboardPath,
    [Alias("Host")]
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8765,
    [int]$DecisionLimit = 120,
    [int]$ExecutionLimit = 40,
    [int]$StaleAfterSeconds = 120,
    [int]$RefreshSeconds = 15,
    [int]$IntervalSeconds = 60,
    [string]$Title,
    [string]$LogPath,
    [ValidateRange(1, 3600)]
    [int]$HeartbeatIntervalSeconds = 30,
    [ValidateRange(1, 300)]
    [int]$RestartDelaySeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_mt5_common.ps1")

function Write-MonitoringRunnerLogLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    Add-Content -Path $Path -Value ("[{0}] {1}" -f $timestamp, $Message)
}

function Append-LogFileContents {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    if (-not (Test-Path $SourcePath)) {
        return
    }

    $sourceItem = Get-Item -Path $SourcePath -ErrorAction SilentlyContinue
    if ($null -eq $sourceItem -or $sourceItem.Length -le 0) {
        return
    }

    Get-Content -Path $SourcePath | Add-Content -Path $DestinationPath
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
$resolvedLogPath = if ($LogPath) {
    Resolve-AbsoluteProjectPath -PathValue $LogPath
}
else {
    Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5MonitoringLogPath -Mode $Mode -ConfigPath $resolvedConfigPath -Role $Role)
}

$targetScriptName = if ($Role -eq "serve") { "mt5_monitoring_dashboard.ps1" } else { "mt5_monitoring_export_loop.ps1" }
$targetScriptPath = Join-Path $PSScriptRoot $targetScriptName
if (-not (Test-Path $targetScriptPath)) {
    throw "Monitoring target script not found: $targetScriptPath"
}

Ensure-Directory -PathValue (Split-Path -Parent $resolvedDashboardPath) | Out-Null
Ensure-Directory -PathValue (Split-Path -Parent $resolvedLogPath) | Out-Null

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$heartbeatIntervalMilliseconds = $HeartbeatIntervalSeconds * 1000

Write-MonitoringRunnerLogLine -Path $resolvedLogPath -Message (
    "monitoring_runner_started role={0} mode={1} env_file={2} config_path={3} dashboard_path={4} bind_host={5} port={6}" -f
    $Role,
    $Mode,
    $resolvedEnvFile,
    $resolvedConfigPath,
    $resolvedDashboardPath,
    $BindHost,
    $Port
)

Push-Location $Script:RootDir
try {
    while ($true) {
        $stdoutPath = [System.IO.Path]::GetTempFileName()
        $stderrPath = [System.IO.Path]::GetTempFileName()
        try {
            $processArguments = @(
                "-NoProfile"
                "-ExecutionPolicy"
                "Bypass"
                "-File"
                $targetScriptPath
                "-Mode"
                $Mode
                "-EnvFile"
                $resolvedEnvFile
                "-ConfigPath"
                $resolvedConfigPath
                "-OutputPath"
                $resolvedDashboardPath
            )

            if ($Role -eq "serve") {
                $processArguments += @(
                    "-Serve"
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
                )
            }
            else {
                $processArguments += @(
                    "-IntervalSeconds"
                    "$([Math]::Max($IntervalSeconds, 15))"
                    "-DecisionLimit"
                    "$DecisionLimit"
                    "-ExecutionLimit"
                    "$ExecutionLimit"
                    "-StaleAfterSeconds"
                    "$StaleAfterSeconds"
                    "-RefreshSeconds"
                    "$RefreshSeconds"
                )
            }

            if (-not [string]::IsNullOrWhiteSpace($Title)) {
                $processArguments += @(
                    "-Title"
                    $Title
                )
            }

            $process = Start-Process `
                -FilePath $powershellExe `
                -ArgumentList $processArguments `
                -WorkingDirectory $Script:RootDir `
                -PassThru `
                -WindowStyle Hidden `
                -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath

            $processStartedAt = Get-Date
            Write-MonitoringRunnerLogLine -Path $resolvedLogPath -Message ("monitoring_child_started role={0} pid={1} script={2}" -f $Role, $process.Id, $targetScriptPath)

            while (-not $process.WaitForExit($heartbeatIntervalMilliseconds)) {
                $elapsedSeconds = [Math]::Round(((Get-Date) - $processStartedAt).TotalSeconds, 0)
                Write-MonitoringRunnerLogLine -Path $resolvedLogPath -Message ("monitoring_runner_heartbeat role={0} pid={1} elapsed_seconds={2}" -f $Role, $process.Id, $elapsedSeconds)
            }

            $process.WaitForExit()

            Append-LogFileContents -SourcePath $stdoutPath -DestinationPath $resolvedLogPath
            Append-LogFileContents -SourcePath $stderrPath -DestinationPath $resolvedLogPath

            Write-MonitoringRunnerLogLine -Path $resolvedLogPath -Message ("monitoring_child_exited role={0} pid={1} exit_code={2}" -f $Role, $process.Id, $process.ExitCode)
        }
        finally {
            Remove-Item -Path $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
        }

        Start-Sleep -Seconds $RestartDelaySeconds
    }
}
finally {
    Pop-Location
}
