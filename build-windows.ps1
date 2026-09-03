$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Python virtual environment not found at $python"
}

& $python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install PyInstaller."
}

Push-Location $projectRoot
try {
    Remove-Item (Join-Path $projectRoot "dist\WowProfile.exe") -Force -ErrorAction SilentlyContinue
    & $python -m PyInstaller --clean --noconfirm WowProfile.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
} finally {
    Pop-Location
}

Write-Host "Built dist\WowProfile\WowProfile.exe"