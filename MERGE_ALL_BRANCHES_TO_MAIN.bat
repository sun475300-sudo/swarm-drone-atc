@echo off
setlocal EnableExtensions EnableDelayedExpansion
title ATC - MERGE ALL BRANCHES TO MAIN

echo ====================================================
echo  swarm-drone-atc - MERGE ALL BRANCHES TO MAIN
echo ====================================================
echo Repo: %~dp0
echo.

cd /d "%~dp0"
if exist ".git\index.lock" del /F /Q ".git\index.lock"

echo [1/4] git fetch --prune origin...
git fetch --prune origin
echo.

echo [2/4] Branches MERGED into main (will be deleted):
set MERGED_LIST=claude/atc-broad-except-20260502-150627 claude/atc-formation-flight-20260427-024340 claude/atc-hypothesis-tests-20260502-223805 claude/atc-imgur-localize-20260427-081624 claude/atc-p703-benchmarks-20260503-050107 claude/atc-p705-metrics-20260502-150603 claude/atc-test-count-20260503-041747 claude/cool-mendeleev-90751f claude/jolly-hypatia-a8d2d7
for %%B in (%MERGED_LIST%) do (
    git rev-parse --verify --quiet "%%B" >nul 2>&1
    if not errorlevel 1 (
        echo   - deleting %%B
        git branch -d "%%B" 2>nul
    )
)
echo.

echo [3/4] Branches NOT merged into main (kept):
echo   - claude/atc-ruff-audit-20260503-050142
echo   - claude/laughing-pasteur-d5f0fb
echo.

echo [4/4] Final local branch list:
git branch
echo.

echo ----------------------------------------------------
echo  See reports\branch_merge_plan.md for details.
echo ----------------------------------------------------
pause
exit /b 0
