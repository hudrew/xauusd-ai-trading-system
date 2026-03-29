param(
    [switch]$WithResearch,
    [switch]$RunHostCheck,
    [string]$EnvTemplate = ".env.mt5.example",
    [string]$EnvTarget = ".env.mt5.local"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $rootDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$envTemplatePath = Join-Path $rootDir $EnvTemplate
$envTargetPath = Join-Path $rootDir $EnvTarget

function Resolve-BootstrapPython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }

    throw "Python launcher not found. Install Python 3.10+ first."
}

if (-not (Test-Path $venvPython)) {
    $bootstrapPython = Resolve-BootstrapPython
    if ($bootstrapPython.Length -gt 1) {
        & $bootstrapPython[0] $bootstrapPython[1] -m venv $venvDir
    }
    else {
        & $bootstrapPython[0] -m venv $venvDir
    }
}

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment bootstrap failed: $venvPython"
}

& $venvPython -m pip install --upgrade pip

$editableSpec = if ($WithResearch) { ".[research,mt5]" } else { ".[mt5]" }
Push-Location $rootDir
try {
    & $venvPython -m pip install -e $editableSpec
}
finally {
    Pop-Location
}

if ((Test-Path $envTemplatePath) -and (-not (Test-Path $envTargetPath))) {
    Copy-Item -Path $envTemplatePath -Destination $envTargetPath
}

Write-Host "Bootstrap completed." -ForegroundColor Green
Write-Host "Virtual environment: $venvPython"
Write-Host "Env file: $envTargetPath"
Write-Host "Next steps:"
Write-Host "1. Fill MT5 credentials in $EnvTarget"
Write-Host "2. Run: powershell -ExecutionPolicy Bypass -File .\scripts\mt5_host_check.ps1 $EnvTarget"
Write-Host "3. Run: powershell -ExecutionPolicy Bypass -File .\scripts\mt5_preflight.ps1 $EnvTarget"
Write-Host "4. Run: powershell -ExecutionPolicy Bypass -File .\scripts\mt5_deploy_gate.ps1 $EnvTarget"
Write-Host "5. Run: powershell -ExecutionPolicy Bypass -File .\scripts\mt5_live_once.ps1 $EnvTarget"
Write-Host "6. Optional for long-running host: powershell -ExecutionPolicy Bypass -File .\scripts\mt5_register_task.ps1 -Mode paper -EnvFile $EnvTarget"
Write-Host "7. Inspect task health: powershell -ExecutionPolicy Bypass -File .\scripts\mt5_task_status.ps1 -Mode paper -TailLog"

if ($RunHostCheck) {
    & (Join-Path $PSScriptRoot "mt5_host_check.ps1") $EnvTarget
}
