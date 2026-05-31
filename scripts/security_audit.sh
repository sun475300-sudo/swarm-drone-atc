#!/usr/bin/env bash
# P719 — Security Audit Script
# Runs pip-audit (dependency CVE scan) and bandit (static analysis).
# Exits 0 even if issues found — just report.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTFILE="${1:-${REPO_ROOT}/results/security_audit_$(date +%Y%m%d).txt}"

mkdir -p "$(dirname "$OUTFILE")"

{
  echo "=== SDACS Security Audit ==="
  echo "Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "Repo: ${REPO_ROOT}"
  echo ""

  # --- pip-audit: dependency CVE scan ---
  echo "=== pip-audit (dependency CVE scan) ==="
  if command -v pip-audit >/dev/null 2>&1; then
    pip-audit 2>&1 || true
  else
    echo "[SKIP] pip-audit not installed"
  fi
  echo ""

  # --- bandit: static analysis (medium/high only) ---
  echo "=== bandit (static analysis, severity>=MEDIUM, confidence>=MEDIUM) ==="
  if command -v bandit >/dev/null 2>&1; then
    bandit -r "${REPO_ROOT}/src/" "${REPO_ROOT}/simulation/" "${REPO_ROOT}/api/" \
      -ll -ii 2>&1 || true
  else
    echo "[SKIP] bandit not installed"
  fi
  echo ""

  echo "=== Audit complete ==="
} | tee "$OUTFILE"

echo ""
echo "Output saved to: $OUTFILE"
exit 0
