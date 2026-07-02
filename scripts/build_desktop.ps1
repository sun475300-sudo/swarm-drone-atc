# SDACS Desktop - one-command build script
# Usage:
#   .\scripts\build_desktop.ps1                # Full build (Python backend + Electron NSIS)
#   .\scripts\build_desktop.ps1 -SkipPython    # electron-builder only (reuse existing backend)
#   .\scripts\build_desktop.ps1 -Clean         # Clean previous artifacts first
#
# Outputs:
#   dist-python/sdacs-backend/*                    (PyInstaller backend, ~4.6GB with torch)
#   dist-desktop/SDACS-Simulator-<VER>-Setup.exe   (NSIS installer)
#
# Note:
#   - Unsigned build. Windows SmartScreen warning expected on first install.
#   - GitHub Releases draft publish via package.json > build > publish.
#   - electron-updater uses latest.yml auto-generated during publish.

[CmdletBinding()]
param(
    [switch]$SkipPython,
    [switch]$Clean,
    [ValidateSet('win', 'mac', 'linux', 'dir')]
    [string]$Target = 'win'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host " SDACS Desktop build -- target=$Target" -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host ""

    if ($Clean) {
        Write-Host "[1/4] Removing previous build artifacts..." -ForegroundColor Yellow
        foreach ($d in 'dist-python', 'build-python', 'dist-desktop') {
            if (Test-Path $d) { Remove-Item -Recurse -Force $d; Write-Host "  removed $d" }
        }
        Write-Host ""
    }

    if (-not $SkipPython) {
        Write-Host "[2/4] Bundling Python backend (PyInstaller)..." -ForegroundColor Yellow
        $piInstalled = python -m pip show pyinstaller 2>$null
        if (-not $piInstalled) {
            Write-Host "  PyInstaller not installed -> installing..." -ForegroundColor Yellow
            python -m pip install pyinstaller
        }
        python -m PyInstaller desktop/backend.spec --clean --noconfirm --distpath dist-python --workpath build-python
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
        Write-Host "  OK: dist-python/sdacs-backend/sdacs-backend.exe" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "[2/4] Skipping Python backend (reusing dist-python)" -ForegroundColor Gray
        if (-not (Test-Path 'dist-python/sdacs-backend/sdacs-backend.exe')) {
            throw "dist-python/sdacs-backend/sdacs-backend.exe missing -- rerun without -SkipPython"
        }
        Write-Host ""
    }

    Write-Host "[3/4] Verifying npm dependencies..." -ForegroundColor Yellow
    if (-not (Test-Path 'node_modules/electron-updater')) {
        Write-Host "  electron-updater not installed -> npm install..." -ForegroundColor Yellow
        npm install --no-audit --no-fund --progress=false
    }
    Write-Host "  OK: node_modules ready" -ForegroundColor Green
    Write-Host ""

    Write-Host "[4/4] Running electron-builder ($Target)..." -ForegroundColor Yellow
    switch ($Target) {
        'win'   { npm run dist:win }
        'mac'   { npm run dist:mac }
        'linux' { npm run dist:linux }
        'dir'   { npm run pack }
    }
    if ($LASTEXITCODE -ne 0) { throw "electron-builder failed" }
    Write-Host ""

    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " Build complete" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Get-ChildItem dist-desktop -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 6 Name, @{n='Size'; e={ "{0:N1} MB" -f ($_.Length / 1MB) }}, LastWriteTime |
        Format-Table -AutoSize

    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Double-click dist-desktop/*.exe to install and verify"
    Write-Host "  2. gh release create v<ver> dist-desktop/*.exe  (manual release)"
    Write-Host "  3. electron-updater auto-detects new GitHub Releases"
    Write-Host ""
}
finally {
    Pop-Location
}
