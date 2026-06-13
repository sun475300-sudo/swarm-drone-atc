#!/usr/bin/env bash
# ODYSSEY Phase 486 — 독립 재현 자동화 스크립트.
#
# 새 컨테이너/머신에서 SDACS 빌드 상태를 검증한다. 출력은 ROADMAP
# "일일 점검" 형식과 호환되어 그대로 인용할 수 있다.
#
# 사용:
#   bash scripts/independent_reproduction.sh                    # 기본 (회귀+동기화+API 게이트)
#   bash scripts/independent_reproduction.sh --full             # +E2E 264건
#   bash scripts/independent_reproduction.sh --no-deps          # 의존성 설치 건너뜀
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── 옵션 파싱 ──
FULL=0; INSTALL=1
for arg in "$@"; do
    case "$arg" in
        --full) FULL=1 ;;
        --no-deps) INSTALL=0 ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

step() { echo; echo "──────── $1 ────────"; }
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
SUMMARY="/tmp/sdacs_reproduction_$(date +%s).txt"
HEAD="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

{
    echo "SDACS Independent Reproduction Report"
    echo "Generated: $(ts)"
    echo "Branch: $BRANCH @ $HEAD"
    echo
} > "$SUMMARY"

# ── 1) 의존성 ──
if [[ "$INSTALL" == "1" ]]; then
    step "1) Python deps"
    pip install -q -r requirements.txt 2>&1 | tail -3 || true
fi

# ── 2) 핵심 회귀 (e2e 제외) ──
step "2) Python regression"
REGRESSION_OUT="/tmp/_sdacs_regression.txt"
if python -m pytest tests/ --ignore=tests/e2e -q --no-cov -p no:cacheprovider > "$REGRESSION_OUT" 2>&1; then
    REG_LINE="$(grep -E '^=+.* passed' "$REGRESSION_OUT" | tail -1)"
    echo "✅ 회귀: $REG_LINE" | tee -a "$SUMMARY"
else
    echo "❌ 회귀 FAILED — 마지막 30줄:" | tee -a "$SUMMARY"
    tail -30 "$REGRESSION_OUT" | tee -a "$SUMMARY"
    exit 1
fi

# ── 3) 4 사본 md5 일치 ──
step "3) Simulator copy sync"
UNIQ=$(md5sum swarm_3d_simulator.html visualization/swarm_3d_simulator.html \
              docs/simulator.html docs/swarm_3d_simulator.html \
       | awk '{print $1}' | sort -u | wc -l)
if [[ "$UNIQ" == "1" ]]; then
    echo "✅ 사본 동기화: 군집 4 사본 md5 일치" | tee -a "$SUMMARY"
else
    echo "❌ 사본 불일치 — md5sum 결과:" | tee -a "$SUMMARY"
    md5sum swarm_3d_simulator.html visualization/swarm_3d_simulator.html \
           docs/simulator.html docs/swarm_3d_simulator.html | tee -a "$SUMMARY"
    exit 1
fi

# ── 4) JS 구문 ──
step "4) Simulator JS syntax"
python3 - <<'PY' > /tmp/_sim.mjs
import re
s = open('swarm_3d_simulator.html').read()
m = re.search(r'<script type="module">(.*?)</script>', s, re.DOTALL)
print(m.group(1))
PY
if node --check /tmp/_sim.mjs 2>&1 | tail -3; then
    echo "✅ JS 구문: node --check OK" | tee -a "$SUMMARY"
else
    echo "❌ JS 구문 실패" | tee -a "$SUMMARY"; exit 1
fi

# ── 5) API 문서 정합성 (Track G-2) ──
step "5) API doc-vs-live coherence"
if python scripts/extract_sdacs_api.py --check 2>&1 | tail -3; then
    echo "✅ 정합성 게이트: 문서-실측 일치" | tee -a "$SUMMARY"
else
    echo "❌ API 문서 불일치 — 'python scripts/extract_sdacs_api.py' 재생성 필요" | tee -a "$SUMMARY"
    exit 1
fi

# ── 6) (옵션) E2E 264건 ──
if [[ "$FULL" == "1" ]]; then
    step "6) Full E2E suite"
    E2E_OUT="/tmp/_sdacs_e2e.txt"
    if python -m pytest tests/e2e/ -q --no-cov -p no:cacheprovider > "$E2E_OUT" 2>&1; then
        E2E_LINE="$(grep -E '^=+.* passed' "$E2E_OUT" | tail -1)"
        echo "✅ E2E: $E2E_LINE" | tee -a "$SUMMARY"
    else
        echo "❌ E2E FAILED — 마지막 30줄:" | tee -a "$SUMMARY"
        tail -30 "$E2E_OUT" | tee -a "$SUMMARY"
        exit 1
    fi
else
    echo "↪️ E2E 264건: 건너뜀 (--full 로 실행)" | tee -a "$SUMMARY"
fi

step "DONE"
echo "독립 재현 GREEN — $(ts)" | tee -a "$SUMMARY"
echo "리포트 저장: $SUMMARY"
