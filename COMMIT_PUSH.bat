@echo off
setlocal EnableExtensions
title SDACS - COMMIT and PUSH to main
cd /d "%~dp0"

echo ==========================================
echo   SDACS  -  COMMIT ^& PUSH  (branch: main)
echo   Repo: %~dp0
echo ==========================================
echo.

REM [1/4] stale lock 제거 (GitHub Desktop "lock file already exists" 해결)
if exist ".git\index.lock" (
    echo [1/4] .git\index.lock 제거 중...
    del /F /Q ".git\index.lock" 2>nul
    if exist ".git\index.lock" (
        echo    [!] 삭제 실패. GitHub Desktop 을 완전히 종료한 뒤 다시 실행하세요.
        pause
        exit /b 1
    )
    echo    제거 완료.
) else (
    echo [1/4] lock 없음 - 건너뜀.
)
if exist ".git\index.stash.5.lock" del /F /Q ".git\index.stash.5.lock" 2>nul
echo.

REM [2/4] 커밋 대상 확인
echo [2/4] 커밋될 변경 파일:
echo ------------------------------------------
git status --short
echo ------------------------------------------
echo.
set /p GO="   이대로 커밋+푸시하려면 Y 입력, 취소하려면 Enter: "
if /I not "%GO%"=="Y" (
    echo    취소했습니다. 변경사항은 그대로 유지됩니다.
    pause
    exit /b 0
)
echo.

REM [3/4] 스테이징 + 커밋
echo [3/4] git add -A  +  commit ...
git add -A
git commit -m "feat: desktop app file:// fix + deep tests + A* opt + README TOC" -m "- desktop/main.js: allow local ES module load (fixes blank 3D view in built app)" -m "- main.py: serve visualize-3d over local HTTP (file:// blocks ES modules)" -m "- launch_demo.ps1: auto-detect python interpreter" -m "- MERGE_ALL_BRANCHES_TO_MAIN.bat: safe merge-all script" -m "- README: collapsible TOC; package.json: electron-builder config"
if errorlevel 1 (
    echo    [!] 커밋 실패 또는 커밋할 변경 없음. 위 메시지를 확인하세요.
    pause
    exit /b 1
)
echo.

REM [4/4] push
echo [4/4] git push origin main ...
git push origin main
if errorlevel 1 (
    echo    [!] push 실패. GitHub 로그인/인증을 확인하세요.
    echo        (GitHub Desktop 에서 로그인되어 있으면 대개 자동 인증됩니다.)
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   완료! 최근 커밋:
git log --oneline -3
echo ==========================================
pause
exit /b 0
