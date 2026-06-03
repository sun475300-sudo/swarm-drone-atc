@echo off
REM SDACS 시뮬레이터 - Windows 원클릭 런처.
REM 탐색기에서 더블클릭하면 로컬 서버를 띄우고 브라우저를 자동으로 엽니다.
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   SDACS 3D 시뮬레이터를 시작합니다...
echo ============================================================

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\serve.py %*
  goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python scripts\serve.py %*
  goto :end
)
where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 scripts\serve.py %*
  goto :end
)

echo [오류] Python을 찾을 수 없습니다.
echo        https://www.python.org/downloads/ 에서 설치 시 "Add Python to PATH"를 체크하세요.
pause
:end
