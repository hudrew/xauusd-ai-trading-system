Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Script:RootDir = Split-Path -Parent $PSScriptRoot
$Script:VenvPython = Join-Path $Script:RootDir ".venv\Scripts\python.exe"
$Script:DefaultEnvFile = Join-Path $Script:RootDir ".env.mt5.local"

function Resolve-AbsoluteProjectPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $Script:RootDir $PathValue))
}

function Resolve-Mt5TerminalPath {
    param(
        [string]$TerminalPath = $env:XAUUSD_AI_MT5_PATH
    )

    if ([string]::IsNullOrWhiteSpace($TerminalPath)) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($TerminalPath)) {
        return [System.IO.Path]::GetFullPath($TerminalPath)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $Script:RootDir $TerminalPath))
}

function Get-Mt5TerminalProcess {
    param(
        [string]$TerminalPath = $env:XAUUSD_AI_MT5_PATH
    )

    $resolvedTerminalPath = Resolve-Mt5TerminalPath -TerminalPath $TerminalPath
    if ([string]::IsNullOrWhiteSpace($resolvedTerminalPath)) {
        return $null
    }

    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and [string]::Equals(
                [System.IO.Path]::GetFullPath($_.ExecutablePath),
                $resolvedTerminalPath,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        } |
        Select-Object -First 1
}

function Ensure-Mt5TerminalProcess {
    param(
        [string]$TerminalPath = $env:XAUUSD_AI_MT5_PATH,
        [int]$ReadyWaitSeconds = 30,
        [int]$WarmupSeconds = 10
    )

    $resolvedTerminalPath = Resolve-Mt5TerminalPath -TerminalPath $TerminalPath
    if ([string]::IsNullOrWhiteSpace($resolvedTerminalPath)) {
        return $null
    }

    if (-not (Test-Path $resolvedTerminalPath)) {
        return $null
    }

    $existingProcess = Get-Mt5TerminalProcess -TerminalPath $resolvedTerminalPath
    if ($null -ne $existingProcess) {
        return [PSCustomObject]@{
            Started = $false
            ProcessId = $existingProcess.ProcessId
            TerminalPath = $resolvedTerminalPath
        }
    }

    Start-Process `
        -FilePath $resolvedTerminalPath `
        -WorkingDirectory (Split-Path -Parent $resolvedTerminalPath) | Out-Null

    $deadline = (Get-Date).AddSeconds($ReadyWaitSeconds)
    do {
        Start-Sleep -Seconds 1
        $startedProcess = Get-Mt5TerminalProcess -TerminalPath $resolvedTerminalPath
    } while ($null -eq $startedProcess -and (Get-Date) -lt $deadline)

    if ($null -eq $startedProcess) {
        throw "MT5 terminal process did not become ready within $ReadyWaitSeconds seconds: $resolvedTerminalPath"
    }

    if ($WarmupSeconds -gt 0) {
        Start-Sleep -Seconds $WarmupSeconds
    }

    return [PSCustomObject]@{
        Started = $true
        ProcessId = $startedProcess.ProcessId
        TerminalPath = $resolvedTerminalPath
    }
}

function Ensure-Venv {
    if (-not (Test-Path $Script:VenvPython)) {
        throw "Missing virtual environment python: $Script:VenvPython`nCreate it first with: py -3.10 -m venv .venv"
    }
}

function Load-EnvFile {
    param(
        [string]$EnvFile = $Script:DefaultEnvFile
    )

    if (-not (Test-Path $EnvFile)) {
        return
    }

    foreach ($line in Get-Content -Path $EnvFile) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }

        $parts = $trimmed -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

function Get-DefaultMt5ConfigPath {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" })
    )

    if ($Mode -eq "prod") {
        return (Join-Path $Script:RootDir "configs\mt5_prod.yaml")
    }

    return (Join-Path $Script:RootDir "configs\mt5_paper.yaml")
}

function Resolve-Mt5Config {
    param(
        [string]$ConfigPath,
        [ValidateSet("paper", "prod")]
        [string]$Mode = $(if ($env:XAUUSD_AI_ENV -eq "prod") { "prod" } else { "paper" })
    )

    $candidatePath = if ($ConfigPath) {
        $ConfigPath
    }
    elseif ($env:XAUUSD_AI_CONFIG_PATH) {
        $env:XAUUSD_AI_CONFIG_PATH
    }
    else {
        Get-DefaultMt5ConfigPath -Mode $Mode
    }

    $resolvedPath = Resolve-AbsoluteProjectPath -PathValue $candidatePath
    if (-not (Test-Path $resolvedPath)) {
        throw "MT5 config not found: $resolvedPath"
    }

    return $resolvedPath
}

function Get-Mt5ConfigSlug {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode,
        [string]$ConfigPath
    )

    $resolvedConfigPath = Resolve-Mt5Config -Mode $Mode -ConfigPath $ConfigPath
    $defaultConfigPath = Resolve-AbsoluteProjectPath -PathValue (Get-DefaultMt5ConfigPath -Mode $Mode)
    if ([string]::Equals($resolvedConfigPath, $defaultConfigPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $null
    }

    $slug = [System.IO.Path]::GetFileNameWithoutExtension($resolvedConfigPath).ToLowerInvariant()
    $slug = [regex]::Replace($slug, "[^a-z0-9]+", "-").Trim("-")
    if ([string]::IsNullOrWhiteSpace($slug)) {
        return "custom"
    }

    return $slug
}

function Get-DefaultMt5TaskName {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode,
        [string]$ConfigPath
    )

    $configSlug = Get-Mt5ConfigSlug -Mode $Mode -ConfigPath $ConfigPath
    if ($configSlug) {
        return "xauusd-ai-$Mode-$configSlug-loop"
    }

    return "xauusd-ai-$Mode-loop"
}

function Get-DefaultMt5TaskLogDir {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode,
        [string]$ConfigPath
    )

    $configSlug = Get-Mt5ConfigSlug -Mode $Mode -ConfigPath $ConfigPath
    if ($configSlug) {
        return (Join-Path $Script:RootDir "var\xauusd_ai\task_logs\$Mode\$configSlug")
    }

    return (Join-Path $Script:RootDir "var\xauusd_ai\task_logs\$Mode")
}

function Get-DefaultMt5MonitoringDashboardPath {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode,
        [string]$ConfigPath
    )

    $configSlug = Get-Mt5ConfigSlug -Mode $Mode -ConfigPath $ConfigPath
    $dashboardName = if ($configSlug) { "$configSlug.html" } else { "$Mode.html" }
    return (Join-Path $Script:RootDir "var\xauusd_ai\dashboards\$dashboardName")
}

function Get-DefaultMt5MonitoringTaskName {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode,
        [string]$ConfigPath,
        [ValidateSet("serve", "refresh")]
        [string]$Role
    )

    $configSlug = Get-Mt5ConfigSlug -Mode $Mode -ConfigPath $ConfigPath
    if ($configSlug) {
        return "xauusd-ai-$Mode-$configSlug-monitor-$Role"
    }

    return "xauusd-ai-$Mode-monitor-$Role"
}

function Get-DefaultMt5MonitoringLogPath {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode,
        [string]$ConfigPath,
        [ValidateSet("serve", "refresh")]
        [string]$Role
    )

    $configSlug = Get-Mt5ConfigSlug -Mode $Mode -ConfigPath $ConfigPath
    $baseDir = if ($configSlug) {
        Join-Path $Script:RootDir "var\xauusd_ai\monitoring_logs\$Mode\$configSlug"
    }
    else {
        Join-Path $Script:RootDir "var\xauusd_ai\monitoring_logs\$Mode"
    }

    return (Join-Path $baseDir "$Role.log")
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    $resolvedPath = Resolve-AbsoluteProjectPath -PathValue $PathValue
    if (-not (Test-Path $resolvedPath)) {
        New-Item -Path $resolvedPath -ItemType Directory -Force | Out-Null
    }

    return $resolvedPath
}

function Get-LatestChildItem {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue,
        [string]$Filter = "*"
    )

    if (-not (Test-Path $PathValue)) {
        return $null
    }

    return Get-ChildItem -Path $PathValue -Filter $Filter -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Invoke-Mt5Cli {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    $previousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = (Join-Path $Script:RootDir "src")
        & $Script:VenvPython -m xauusd_ai_system.cli --config $ConfigPath @Arguments
    }
    finally {
        if ($null -eq $previousPythonPath) {
            Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        }
        else {
            $env:PYTHONPATH = $previousPythonPath
        }
    }
}

function Get-Mt5MonitoringSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath,
        [int]$DecisionLimit = 40,
        [int]$ExecutionLimit = 40,
        [int]$StaleAfterSeconds = 120
    )

    Ensure-Venv
    $snapshotJson = Invoke-Mt5Cli `
        -ConfigPath $ConfigPath `
        "monitoring" `
        "snapshot" `
        "--decision-limit" `
        "$DecisionLimit" `
        "--execution-limit" `
        "$ExecutionLimit" `
        "--stale-after-seconds" `
        "$StaleAfterSeconds"

    $convertFromJsonCommand = Get-Command ConvertFrom-Json -ErrorAction Stop
    if ($convertFromJsonCommand.Parameters.ContainsKey("Depth")) {
        return ($snapshotJson | ConvertFrom-Json -Depth 8)
    }

    return ($snapshotJson | ConvertFrom-Json)
}
