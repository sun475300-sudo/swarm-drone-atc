@echo off
chcp 65001 > nul
title 🚁 Imperial Wings - 자동 포스팅 시스템

echo.
echo ================================================
echo   Imperial Wings 자동 포스팅 시스템 시작 중...
echo ================================================
echo.

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.10 이상을 설치해 주세요: https://python.org
    pause
    exit /b 1
)

:: 필수 패키지 설치 확인
echo [1/3] 필수 패키지 확인 중...
pip install playwright schedule pillow cryptography --quiet --disable-pip-version-check

:: Playwright 브라우저 설치 확인
echo [2/3] 브라우저 설치 확인 중...
playwright install chromium --quiet 2>nul

:: 앱 실행
echo [3/3] 앱 시작!
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [오류] 앱 실행 중 문제가 발생했습니다.
    pause
)
