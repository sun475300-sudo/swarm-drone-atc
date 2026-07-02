@echo off
REM ============================================================
REM  SDACS 시뮬레이터 원클릭 실행기 (Windows)
REM  이 파일을 더블클릭하면 로컬 HTTP 서버가 뜨고
REM  브라우저에서 군집 드론 시뮬레이터가 자동으로 열립니다.
REM  (HTML 직접 더블클릭은 file:// CORS로 실패하므로 이 런처를 사용)
REM  이 창을 닫으면 서버가 종료됩니다.
REM ============================================================
chcp 65001 >nul
setlocal
title SDACS Simulator Launcher
cd /d "%~dp0"

REM Python 3 탐지 (py 런처 우선, 없으면 python)
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3 을 찾을 수 없습니다.
    echo         https://www.python.org 에서 설치 후 "Add to PATH" 를 체크하세요.
    echo.
    pause
    exit /b 1
)

echo SDACS 군집 드론 시뮬레이터를 시작합니다...
echo 브라우저가 자동으로 열립니다. 이 창을 닫으면 서버가 종료됩니다.
echo (해양 시뮬레이터는  %PY% scripts\serve.py --page maritime  로 실행)
echo.

%PY% scripts\serve.py --page swarm

endlocal
