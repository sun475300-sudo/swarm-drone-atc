@echo off
setlocal EnableExtensions EnableDelayedExpansion
title ATC - MERGE ALL BRANCHES TO MAIN
cd /d "%~dp0"

echo ====================================================
echo  swarm-drone-atc - MERGE ALL BRANCHES TO MAIN
echo  Repo: %~dp0
echo ====================================================
echo.

if exist ".git\index.lock" del /F /Q ".git\index.lock"

REM --- 안전 점검: 커밋되지 않은 변경이 있으면 중단 (병합 사고 방지) ---
git diff --quiet
if errorlevel 1 goto :dirty
git diff --cached --quiet
if errorlevel 1 goto :dirty
goto :clean
:dirty
echo [ABORT] 커밋되지 않은 변경이 있습니다. 먼저 commit 하거나 stash 하세요.
echo.
git status --short
pause
exit /b 1
:clean

echo [1/5] git fetch --prune origin ...
git fetch --prune origin
if errorlevel 1 goto :err
echo.

echo [2/5] main 체크아웃 + origin/main 최신화 (fast-forward) ...
git checkout main
if errorlevel 1 goto :err
git merge --ff-only origin/main
echo.

echo [3/5] main 에 아직 병합되지 않은 원격 브랜치:
REM origin/HEAD 표시줄(->)과 origin/main 은 제외
git branch -r --no-merged main | findstr /V /C:"->" /C:"origin/main" > "%TEMP%\_atc_tomerge.txt"
set "COUNT=0"
for /f "tokens=*" %%B in (%TEMP%\_atc_tomerge.txt) do (
    echo   - %%B
    set /a COUNT+=1
)
if "!COUNT!"=="0" (
    echo   ^(없음 - 모든 브랜치가 이미 main 에 통합됨^)
    del /F /Q "%TEMP%\_atc_tomerge.txt" 2>nul
    goto :pushstage
)
echo.

echo [4/5] 병합 실행 (충돌 시 자동 중단) ...
for /f "tokens=*" %%B in (%TEMP%\_atc_tomerge.txt) do (
    echo   - merging %%B
    git merge --no-edit "%%B"
    if errorlevel 1 (
        echo.
        echo [CONFLICT] %%B 병합 중 충돌 발생. 자동 병합을 중단합니다.
        echo    충돌 해결 후:  git add . ^&^& git commit
        echo    되돌리려면:    git merge --abort
        del /F /Q "%TEMP%\_atc_tomerge.txt" 2>nul
        pause
        exit /b 1
    )
)
del /F /Q "%TEMP%\_atc_tomerge.txt" 2>nul
echo.

:pushstage
echo [5/5] origin 으로 push (원격 main 갱신) ...
set /p DOPUSH="   지금 push 하려면 Y 입력, 나중에 하려면 Enter: "
if /I "!DOPUSH!"=="Y" (
    git push origin main
    if errorlevel 1 goto :err
    echo   push 완료.
) else (
    echo   push 건너뜀. 나중에 실행:  git push origin main
)
echo.

echo ====================================================
echo  완료. 최종 상태:
echo ----------------------------------------------------
git log --oneline -6
echo.
git branch -a
echo ====================================================
pause
exit /b 0

:err
echo.
echo [ERROR] git 명령이 실패했습니다. 위 메시지를 확인하세요.
echo   .git 이 잠겼다면 다른 git 프로세스를 종료하고 다시 실행하세요.
pause
exit /b 1
