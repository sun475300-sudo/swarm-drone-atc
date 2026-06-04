#!/usr/bin/env bash
# P719 — SDACS 보안 감사 스크립트
# bandit, pip-audit, safety를 순차 실행하고 결과를 reports/에 저장한다.
# 각 도구가 없으면 경고만 출력하고 계속 진행한다.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${REPO_ROOT}/reports"
REPORT_FILE="${REPORT_DIR}/security_audit_$(date +%Y%m%d).txt"
EXIT_CODE=0

mkdir -p "${REPORT_DIR}"

{
  echo "============================================================"
  echo "SDACS Security Audit — $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "============================================================"
  echo ""

  # ── 1. bandit — Python 정적 보안 분석 ──────────────────────────
  echo "[1/3] bandit — Python 정적 보안 분석"
  echo "------------------------------------------------------------"
  if command -v bandit &>/dev/null; then
    bandit -r "${REPO_ROOT}/src" \
      -x "${REPO_ROOT}/src/**/__pycache__" \
      -ll --format txt 2>&1 || EXIT_CODE=$?
  else
    echo "SKIP: bandit not installed (pip install bandit)"
  fi
  echo ""

  # ── 2. pip-audit — CVE 취약점 스캔 ────────────────────────────
  echo "[2/3] pip-audit — 의존성 CVE 스캔"
  echo "------------------------------------------------------------"
  if command -v pip-audit &>/dev/null; then
    pip-audit --requirement "${REPO_ROOT}/requirements.txt" 2>&1 || EXIT_CODE=$?
  else
    echo "SKIP: pip-audit not installed (pip install pip-audit)"
  fi
  echo ""

  # ── 3. safety — requirements.txt 알려진 취약점 체크 ───────────
  echo "[3/3] safety — requirements.txt 취약점 체크"
  echo "------------------------------------------------------------"
  if command -v safety &>/dev/null; then
    safety check -r "${REPO_ROOT}/requirements.txt" 2>&1 || EXIT_CODE=$?
  else
    echo "SKIP: safety not installed (pip install safety)"
  fi
  echo ""

  echo "============================================================"
  echo "감사 완료. 종료 코드: ${EXIT_CODE}"
  echo "보고서: ${REPORT_FILE}"
  echo "============================================================"
} | tee "${REPORT_FILE}"

exit ${EXIT_CODE}
