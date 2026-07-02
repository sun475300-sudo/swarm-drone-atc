# SDACS Desktop — 원커맨드 빌드 스크립트
# 사용법:
#   .\scripts\build_desktop.ps1                # 전체 빌드 (Python 백엔드 + Electron NSIS)
#   .\scripts\build_desktop.ps1 -SkipPython    # electron-builder 만 (Python 백엔드 그대로 사용)
#   .\scripts\build_desktop.ps1 -Clean         # 이전 빌드 산출물 삭제 후 클린 빌드
#
# 산출물:
#   dist-python/sdacs-backend/*                    (PyInstaller 백엔드, ~4.6GB)
#   dist-desktop/SDACS-Simulator-<VER>-Setup.exe   (NSIS 설치 관리자)
#
# 정책:
#   - 서명 없음 → Windows SmartScreen 경고 정상 (README 안내 참조)
#   - GitHub Releases draft 발행: package.json > build > publish 설정
#   - electron-updater 는 자동으로 latest.yml 을 발행 metadata 로 사용

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
    Write-Host " SDACS Desktop 빌드 — target=$Target" -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host ""

    # 1) Clean
    if ($Clean) {
        Write-Host "[1/4] 이전 빌드 산출물 삭제..." -ForegroundColor Yellow
        foreach ($d in 'dist-python', 'build-python', 'dist-desktop') {
            if (Test-Path $d) { Remove-Item -Recurse -Force $d; Write-Host "  removed $d" }
        }
        Write-Host ""
    }

    # 2) Python backend (PyInstaller)
    if (-not $SkipPython) {
        Write-Host "[2/4] Python 백엔드 번들링 (PyInstaller)..." -ForegroundColor Yellow
        # pyinstaller 설치 확인
        $piInstalled = python -m pip show pyinstaller 2>$null
        if (-not $piInstalled) {
            Write-Host "  PyInstaller 미설치 → 설치 중..." -ForegroundColor Yellow
            python -m pip install pyinstaller
        }
        python -m PyInstaller desktop/backend.spec --clean --noconfirm `
            --distpath dist-python --workpath build-python
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller 실패" }
        Write-Host "  ✓ dist-python/sdacs-backend/sdacs-backend.exe 생성됨" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "[2/4] Python 백엔드 스킵 (기존 dist-python 사용)" -ForegroundColor Gray
        if (-not (Test-Path 'dist-python/sdacs-backend/sdacs-backend.exe')) {
            throw "dist-python/sdacs-backend/sdacs-backend.exe 없음 — -SkipPython 을 빼고 다시 실행하세요."
        }
        Write-Host ""
    }

    # 3) npm 의존성 확인
    Write-Host "[3/4] npm 의존성 확인..." -ForegroundColor Yellow
    if (-not (Test-Path 'node_modules/electron-updater')) {
        Write-Host "  electron-updater 미설치 → npm install..." -ForegroundColor Yellow
        npm install --no-audit --no-fund --progress=false
    }
    Write-Host "  ✓ node_modules 준비 완료" -ForegroundColor Green
    Write-Host ""

    # 4) electron-builder
    Write-Host "[4/4] electron-builder ($Target)..." -ForegroundColor Yellow
    switch ($Target) {
        'win'   { npm run dist:win }
        'mac'   { npm run dist:mac }
        'linux' { npm run dist:linux }
        'dir'   { npm run pack }
    }
    if ($LASTEXITCODE -ne 0) { throw "electron-builder 실패" }
    Write-Host ""

    # 결과 요약
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host " 빌드 완료" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Get-ChildItem dist-desktop -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 6 Name, @{n='Size'; e={ "{0:N1} MB" -f ($_.Length / 1MB) }}, LastWriteTime |
        Format-Table -AutoSize

    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor Cyan
    Write-Host "  1. dist-desktop/*.exe 를 로컬에서 더블클릭 → 설치 → 실행 검증"
    Write-Host "  2. gh release create v<ver> dist-desktop/*.exe  (수동 릴리즈)"
    Write-Host "  3. electron-updater 는 GitHub Release 게시 후 자동 감지"
    Write-Host ""
}
finally {
    Pop-Location
}
