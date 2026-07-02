# SDACS 발표용 원클릭 데모 실행 스크립트
# 사용법: PowerShell에서 .\launch_demo.ps1 실행
# 작성일: 2026-05-08

$ErrorActionPreference = "Stop"

# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
$ProjectRoot = $PSScriptRoot

# Python 3 자동 탐지 — 하드코딩 경로 제거(환경마다 설치 위치/버전이 달라 실행 실패의 원인이었음).
#   1) py 런처로 Python 3 실제 경로 해석 → 2) PATH의 python/python3 → 3) 사용자별 기본 설치 경로 폴백
$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try { $Python = (& py -3 -c "import sys; print(sys.executable)" 2>$null).Trim() } catch { $Python = $null }
}
if (-not $Python -or -not (Test-Path $Python)) {
    foreach ($cand in @("python", "python3")) {
        $c = Get-Command $cand -ErrorAction SilentlyContinue
        if ($c) { $Python = $c.Source; break }
    }
}
if (-not $Python -or -not (Test-Path $Python)) {
    foreach ($v in @("Python313", "Python312", "Python311", "Python310")) {
        $p = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\$v\python.exe"
        if (Test-Path $p) { $Python = $p; break }
    }
}
$DashUrl = "http://127.0.0.1:8050"
$SimV2 = Join-Path $ProjectRoot "docs\swarm_3d_simulator_v2.html"
$HubPage = Join-Path $ProjectRoot "docs\go.html"

# ─────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────
function Write-Banner($Text) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}

function Test-Port($Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

# ─────────────────────────────────────────────────────────────
# 1. Python 환경 확인
# ─────────────────────────────────────────────────────────────
Write-Banner "1. Python 환경 확인"
if (-not $Python -or -not (Test-Path $Python)) {
    Write-Host "[ERROR] Python 3을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "python.org 설치 후 'Add to PATH' 체크, 또는 winget install Python.Python.3.11 실행 필요" -ForegroundColor Yellow
    exit 1
}
& $Python --version
Write-Host "[OK] Python 설치 확인" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────
# 2. 핵심 라이브러리 확인
# ─────────────────────────────────────────────────────────────
Write-Banner "2. 핵심 라이브러리 확인"
$importCheck = & $Python -c "import numpy, simpy, scipy, dash, plotly; print('OK')" 2>&1
if ($importCheck -eq "OK") {
    Write-Host "[OK] numpy, simpy, scipy, dash, plotly 모두 로드 가능" -ForegroundColor Green
} else {
    Write-Host "[ERROR] 라이브러리 누락: $importCheck" -ForegroundColor Red
    Write-Host "pip install -r requirements.txt 실행 필요" -ForegroundColor Yellow
    exit 1
}

# ─────────────────────────────────────────────────────────────
# 3. 기존 Dash 프로세스 정리
# ─────────────────────────────────────────────────────────────
Write-Banner "3. 기존 Dash 프로세스 정리"
if (Test-Port 8050) {
    Write-Host "포트 8050이 이미 사용 중입니다. 종료 시도..." -ForegroundColor Yellow
    $conn = Get-NetTCPConnection -LocalPort 8050 -State Listen
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Write-Host "[OK] 포트 8050 사용 가능" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────
# 4. Dash 3D 대시보드 시작 (백그라운드)
# ─────────────────────────────────────────────────────────────
Write-Banner "4. Dash 3D 대시보드 시작"
$dashProc = Start-Process -FilePath $Python `
    -ArgumentList "main.py", "visualize" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Minimized `
    -PassThru

Write-Host "PID: $($dashProc.Id) | 부팅 대기 (최대 15초)..." -ForegroundColor Gray
$timeout = 15
$elapsed = 0
while (-not (Test-Port 8050) -and $elapsed -lt $timeout) {
    Start-Sleep -Seconds 1
    $elapsed++
    Write-Host "." -NoNewline -ForegroundColor Gray
}
Write-Host ""

if (Test-Port 8050) {
    Write-Host "[OK] Dash 대시보드 LIVE on $DashUrl" -ForegroundColor Green
} else {
    Write-Host "[WARN] 부팅 시간 초과 — 백업 (HTML 시뮬레이터)로 진행" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────
# 5. 브라우저 열기
# ─────────────────────────────────────────────────────────────
Write-Banner "5. 브라우저 열기"
Write-Host "허브 페이지: $HubPage" -ForegroundColor Gray
Start-Process $HubPage
Start-Sleep -Milliseconds 500

Write-Host "3D 시뮬레이터 v2: $SimV2" -ForegroundColor Gray
Start-Process $SimV2
Start-Sleep -Milliseconds 500

if (Test-Port 8050) {
    Write-Host "Dash 대시보드: $DashUrl" -ForegroundColor Gray
    Start-Process $DashUrl
}

# ─────────────────────────────────────────────────────────────
# 6. 발표 시연 메모
# ─────────────────────────────────────────────────────────────
Write-Banner "6. 발표 시연 가이드"
Write-Host @"

[3D 시뮬레이터 v2 단축키]
  1 - Cinematic 카메라 (영화처럼 부드러움)
  2 - ATC 카메라 (관제 시점)
  3 - Data 카메라 (분석용)
  4 - Follow 카메라 (드론 추적)

[시연 추천 순서 5분]
  0:00 - free + Cinematic   "낮은 하늘의 가상 공역입니다"
  1:00 - crossing 시나리오   "교차로처럼 만나도..."
  2:00 - 2키 ATC 시점       "관제소 시점에서 보겠습니다"
  3:00 - wind 시나리오      "바람 조건에서도..."
  4:00 - 4키 Follow + 드론  "한 대만 따라가 보면..."
  5:00 - 3키 Data 시점      "결과 지표가 실시간으로..."

[Dash 대시보드 기능]
  - 시뮬 속도 슬라이더 (0.25x ~ 5x)
  - 바람 효과 ON/OFF 토글
  - APF 벡터 필드 표시 토글
  - 실시간 통계 패널 (충돌/근접/어드바이저리)

[발표 후 정리]
  Stop-Process -Id $($dashProc.Id) -Force
  또는 작업관리자에서 python.exe 종료
"@ -ForegroundColor White

Write-Banner "준비 완료 — 발표 시작하세요!"
Write-Host ""
