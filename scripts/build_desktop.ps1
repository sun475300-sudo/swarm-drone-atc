# SDACS Desktop - one-command build script
# Usage:
#   .\scripts\build_desktop.ps1                  # Standalone Electron app (recommended)
#   .\scripts\build_desktop.ps1 -IncludePython   # Python Dash backend included
#   .\scripts\build_desktop.ps1 -Clean           # Clean previous artifacts first
#
# Outputs:
#   dist-python/sdacs-backend/*                         (optional PyInstaller backend)
#   dist-desktop/SDACS-Simulator-<VER>-x64.exe           (NSIS installer)
#   dist-desktop/SDACS-Simulator-<VER>-portable.exe      (portable app)
#
# Note:
#   - Unsigned build. Windows SmartScreen warning expected on first install.
#   - GitHub Releases draft publish via package.json > build > publish.
#   - electron-updater uses latest.yml auto-generated during publish.

[CmdletBinding()]
param(
    [switch]$IncludePython,
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

    if ($IncludePython) {
        Write-Host "[2/4] Bundling Python backend (PyInstaller)..." -ForegroundColor Yellow
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            throw "Python is not installed or is not on PATH. Install Python 3.11+ or omit -IncludePython."
        }
        & $python.Source --version | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "The python command is not executable. Install Python 3.11+ or omit -IncludePython."
        }
        $piInstalled = & $python.Source -m pip show pyinstaller 2>$null
        if (-not $piInstalled) {
            Write-Host "  PyInstaller not installed -> installing..." -ForegroundColor Yellow
            & $python.Source -m pip install pyinstaller
        }
        & $python.Source -m PyInstaller desktop/backend.spec --clean --noconfirm --distpath dist-python --workpath build-python
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
        Write-Host "  OK: dist-python/sdacs-backend/sdacs-backend.exe" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "[2/4] Standalone mode (JavaScript simulation engine)" -ForegroundColor Yellow
        if (Test-Path 'dist-python/sdacs-backend/sdacs-backend.exe') {
            Write-Host "  Existing Python backend found and will also be bundled." -ForegroundColor Green
        } else {
            Write-Host "  Python backend omitted. The full 3D simulator remains available offline." -ForegroundColor Gray
        }
        Write-Host ""
    }

    Write-Host "[3/4] Verifying npm dependencies..." -ForegroundColor Yellow
    $builder = Join-Path $repoRoot 'node_modules/.bin/electron-builder.cmd'
    if (-not (Test-Path $builder)) {
        $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
        if (-not $npm) {
            throw "npm is not available. Install Node.js LTS (including npm), then rerun this script."
        }
        Write-Host "  node_modules missing -> npm install..." -ForegroundColor Yellow
        & $npm.Source install --no-audit --no-fund --progress=false
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    }
    Write-Host "  OK: node_modules ready" -ForegroundColor Green
    Write-Host ""

    Write-Host "[4/4] Running electron-builder ($Target)..." -ForegroundColor Yellow
    switch ($Target) {
        'win'   { & $builder --config desktop/electron-builder.config.cjs --win nsis portable }
        'mac'   { & $builder --config desktop/electron-builder.config.cjs --mac dmg }
        'linux' { & $builder --config desktop/electron-builder.config.cjs --linux AppImage }
        'dir'   { & $builder --config desktop/electron-builder.config.cjs --dir }
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

    $executables = Get-ChildItem dist-desktop -Filter '*.exe' -File -ErrorAction SilentlyContinue
    if ($executables) {
        Write-Host "SHA-256:" -ForegroundColor Cyan
        $executables | Get-FileHash -Algorithm SHA256 | Select-Object Path, Hash | Format-Table -AutoSize
    }

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
