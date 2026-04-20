@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
echo.
echo ================================================
echo   SDACS site -^> GitHub Pages permanent deploy
echo ================================================
echo   Repo: sun475300-sudo/swarm-drone-atc
echo   Final URL:
echo     https://sun475300-sudo.github.io/swarm-drone-atc/
echo ================================================
echo.

REM 1) Remove stale index.lock if any
if exist ".git\index.lock" (
  echo [1/5] Removing stale .git\index.lock ...
  del /f /q ".git\index.lock"
) else (
  echo [1/5] No stale index.lock - OK
)

echo.
echo [2/5] Current git status:
echo ------------------------------------------------
git status --short
echo ------------------------------------------------

echo.
echo [3/5] Staging docs/ and workflows ...
git add docs/ .github/workflows/deploy-pages.yml .github/workflows/pages.yml
if errorlevel 1 (
  echo [ERROR] git add failed
  pause
  exit /b 1
)

echo.
echo [4/5] Creating commit ...
git commit -m "docs: merge SDACS official landing for GitHub Pages permanent deploy (simulator/scenarios/test-report, 2026-04-20)"
if errorlevel 1 (
  echo [INFO] Nothing to commit or already committed - continuing
)

echo.
echo [5/5] Pushing to origin/main ...
git push origin main
if errorlevel 1 (
  echo.
  echo ================================================
  echo [X] Push failed
  echo ------------------------------------------------
  echo Possible causes:
  echo   1. GitHub auth needed - open GitHub Desktop and sign in, then retry
  echo   2. Remote ahead - run: git pull --rebase origin main   then rerun
  echo   3. Network blocked
  echo ================================================
  pause
  exit /b 1
)

echo.
echo ================================================
echo [V] Push complete!
echo ------------------------------------------------
echo GitHub Actions build starts automatically (1-3 min).
echo.
echo Track build:
echo   https://github.com/sun475300-sudo/swarm-drone-atc/actions
echo.
echo Permanent URL (live after build succeeds):
echo   https://sun475300-sudo.github.io/swarm-drone-atc/
echo.
echo From now on the site stays online even when PC/terminal is off.
echo ================================================
echo.
pause
