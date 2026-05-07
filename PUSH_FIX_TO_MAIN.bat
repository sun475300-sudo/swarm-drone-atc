@echo off
setlocal EnableExtensions EnableDelayedExpansion
title ATC - PUSH FIX TO MAIN

echo ====================================================
echo  swarm-drone-atc - PUSH FIX TO MAIN (clean-tree)
echo ====================================================
echo Repo: %~dp0
echo.

cd /d "%~dp0"
if errorlevel 1 (
    echo [FAIL] Cannot cd to repo dir.
    pause
    exit /b 1
)

echo [1/5] Removing stale .git locks if any...
if exist ".git\index.lock" del /F /Q ".git\index.lock"
if exist ".git\HEAD.lock" del /F /Q ".git\HEAD.lock"
echo [OK]  Lock cleanup done.
echo.

echo [2/5] Current branch + status...
git rev-parse --abbrev-ref HEAD
git status -s
echo.

echo [3/5] Run smoke tests (apf + analytics + apf_engine_fallback)...
call python -m pytest tests/test_apf.py tests/test_analytics.py tests/test_apf_engine_fallback.py --tb=line -q --no-cov
if errorlevel 1 (
    echo.
    echo [FAIL] Smoke tests failed. Aborting push.
    pause
    exit /b 1
)
echo [OK]  Smoke tests passed.
echo.

echo [4/5] Stage untracked aux files (no production code changes pending)...
git add README_KO.txt MERGE_ALL_BRANCHES_TO_MAIN.bat PUSH_FIX_TO_MAIN.bat
if exist "reports" git add reports/
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "chore(repo): add KO summary + push helpers (clean working tree)" -m "" -m "- README_KO.txt: 한글 요약" -m "- MERGE_ALL_BRANCHES_TO_MAIN.bat / PUSH_FIX_TO_MAIN.bat: 자동화 스크립트" -m "- reports/: cowork 점검 보고"
    if errorlevel 1 (
        echo [FAIL] Commit failed.
        pause
        exit /b 1
    )
    echo [OK]  Committed.
) else (
    echo [SKIP] Nothing to commit.
)
echo.

echo [5/5] git pull --rebase origin main && push...
git pull --rebase origin main
if errorlevel 1 (
    echo.
    echo [FAIL] Rebase failed.
    pause
    exit /b 1
)
git push origin main
if errorlevel 1 (
    echo.
    echo [FAIL] Push failed. Check auth and retry.
    pause
    exit /b 1
)
echo.
echo ====================================================
echo  DONE - swarm-drone-atc main pushed to origin
echo ====================================================
pause
exit /b 0
