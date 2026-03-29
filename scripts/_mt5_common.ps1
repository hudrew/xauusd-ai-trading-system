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

function Resolve-Mt5Config {
    $envName = $env:XAUUSD_AI_ENV
    if ($envName -eq "prod") {
        return (Join-Path $Script:RootDir "configs\mt5_prod.yaml")
    }

    return (Join-Path $Script:RootDir "configs\mt5_paper.yaml")
}

function Get-DefaultMt5TaskName {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode
    )

    return "xauusd-ai-$Mode-loop"
}

function Get-DefaultMt5TaskLogDir {
    param(
        [ValidateSet("paper", "prod")]
        [string]$Mode
    )

    return (Join-Path $Script:RootDir "var\xauusd_ai\task_logs\$Mode")
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
