@echo off
REM ----------------------------------------------------------
REM  GitHub Pages 영구 URL 배포 트리거
REM  실행 후 docs/.deploy-trigger 빈 파일을 추가하여 push -> deploy-pages.yml 워크플로 발동
REM ----------------------------------------------------------
chcp 65001 >nul 2>&1
title SDACS - Deploy to GitHub Pages

echo.
echo =====================================================
echo   SDACS GitHub Pages 배포 시작
echo =====================================================
echo.

cd /d E:\GitHub\swarm-drone-atc
if errorlevel 1 (
  echo [ERROR] E:\GitHub\swarm-drone-atc 폴더로 이동 실패
  goto end
)

echo [1/5] 현재 위치: %CD%
echo.

echo [2/5] 트리거 파일 작성중...
echo deployed at %DATE% %TIME% > "docs\.deploy-trigger"
if errorlevel 1 (
  echo [ERROR] 트리거 파일 작성 실패
  goto end
)

echo [3/5] git add / commit ...
git add "docs\.deploy-trigger"
git commit -m "chore: trigger GitHub Pages deploy"
if errorlevel 1 (
  echo [INFO] 변경사항이 없거나 commit 실패 - 빈 commit 으로 재시도
  git commit --allow-empty -m "chore: trigger GitHub Pages deploy (empty)"
)

echo.
echo [4/5] git push origin main ...
git push origin main
if errorlevel 1 (
  echo.
  echo [ERROR] push 실패 - 자격증명 또는 네트워크 문제일 수 있습니다
  echo  GitHub Desktop 또는 Git Bash 에서 수동 push 후 다시 시도해주세요
  goto end
)

echo.
echo [5/5] 완료. Actions 실행 상태:
echo   https://github.com/sun475300-sudo/swarm-drone-atc/actions
echo.
echo   배포 후 영구 URL:
echo   https://sun475300-sudo.github.io/swarm-drone-atc/
echo.
echo =====================================================
echo   Pages 빌드까지 1~3분 소요됩니다.
echo =====================================================

:end
echo.
echo 이 창은 10초 후 자동으로 닫힙니다 ...
timeout /t 10 /nobreak >nul
exit
