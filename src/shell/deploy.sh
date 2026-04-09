#!/usr/bin/env bash
# SDACS 배포 자동화 스크립트
# ============================
# Docker Compose 기반 전체 시스템 배포
#
# 기능:
#   - 환경 검증 (Python, Node, Docker)
#   - 의존성 설치
#   - 테스트 실행 + 최소 통과율 검증
#   - Docker 이미지 빌드
#   - 서비스 시작/중지/상태 확인
#   - 로그 수집

set -euo pipefail

# ── 색상 ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
MIN_TESTS=1200
MIN_PASS_RATE=95

# ── 환경 검증 ───────────────────────────────────────────

check_env() {
    info "환경 검증 중..."

    # Python
    if command -v python3 &>/dev/null; then
        PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
        ok "Python $PY_VER"
    else
        err "Python 3 필요"; exit 1
    fi

    # pip
    if python3 -m pip --version &>/dev/null; then
        ok "pip 설치됨"
    else
        err "pip 필요"; exit 1
    fi

    # pytest
    if python3 -m pytest --version &>/dev/null; then
        ok "pytest 설치됨"
    else
        warn "pytest 미설치 — 설치 중..."
        python3 -m pip install pytest -q
    fi

    # Node.js (선택)
    if command -v node &>/dev/null; then
        ok "Node.js $(node --version)"
    else
        warn "Node.js 미설치 (대시보드 기능 제한)"
    fi

    # Docker (선택)
    if command -v docker &>/dev/null; then
        ok "Docker $(docker --version | awk '{print $3}')"
    else
        warn "Docker 미설치 (컨테이너 배포 불가)"
    fi

    ok "환경 검증 완료"
}

# ── 의존성 설치 ──────────────────────────────────────────

install_deps() {
    info "Python 의존성 설치 중..."
    cd "$PROJECT_DIR"

    if [ -f requirements.txt ]; then
        python3 -m pip install -r requirements.txt -q
        ok "requirements.txt 설치 완료"
    fi

    if [ -f package.json ]; then
        if command -v npm &>/dev/null; then
            npm install --silent 2>/dev/null || warn "npm install 실패 (무시)"
        fi
    fi

    ok "의존성 설치 완료"
}

# ── 테스트 실행 ──────────────────────────────────────────

run_tests() {
    info "테스트 실행 중..."
    cd "$PROJECT_DIR"

    # pytest 실행
    TEST_OUTPUT=$(python3 -m pytest tests/ -v --tb=short 2>&1) || true

    # 결과 파싱
    PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' || echo "0")
    FAILED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= failed)' || echo "0")
    ERRORS=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= error)' || echo "0")
    TOTAL=$((PASSED + FAILED + ERRORS))

    info "테스트 결과: ${PASSED} passed / ${FAILED} failed / ${ERRORS} errors (총 ${TOTAL})"

    if [ "$TOTAL" -lt "$MIN_TESTS" ]; then
        err "테스트 수 부족: ${TOTAL} < ${MIN_TESTS}"
        exit 1
    fi

    if [ "$TOTAL" -gt 0 ]; then
        PASS_RATE=$((PASSED * 100 / TOTAL))
        if [ "$PASS_RATE" -lt "$MIN_PASS_RATE" ]; then
            err "통과율 부족: ${PASS_RATE}% < ${MIN_PASS_RATE}%"
            exit 1
        fi
        ok "테스트 통과: ${PASSED}/${TOTAL} (${PASS_RATE}%)"
    fi
}

# ── 시뮬레이션 실행 ──────────────────────────────────────

run_simulation() {
    local duration=${1:-60}
    local seed=${2:-42}

    info "시뮬레이션 실행 (duration=${duration}s, seed=${seed})..."
    cd "$PROJECT_DIR"

    python3 main.py simulate --duration "$duration" --seed "$seed" 2>&1
    ok "시뮬레이션 완료"
}

# ── 3D 대시보드 시작 ────────────────────────────────────

start_dashboard() {
    info "3D 대시보드 시작 중..."
    cd "$PROJECT_DIR"

    python3 visualization/simulator_3d.py &
    DASH_PID=$!
    sleep 2

    if kill -0 "$DASH_PID" 2>/dev/null; then
        ok "대시보드 실행 중: http://localhost:8050 (PID: $DASH_PID)"
    else
        err "대시보드 시작 실패"
    fi
}

# ── 상태 확인 ────────────────────────────────────────────

status() {
    info "SDACS 시스템 상태"
    echo "─────────────────────────────────"

    # 파일 수
    PY_FILES=$(find "$PROJECT_DIR/simulation" -name "*.py" | wc -l)
    TEST_FILES=$(find "$PROJECT_DIR/tests" -name "test_*.py" | wc -l)
    MULTI_LANG=$(find "$PROJECT_DIR/src" -type f \( -name "*.ts" -o -name "*.rs" -o -name "*.go" -o -name "*.cpp" -o -name "*.java" -o -name "*.kt" -o -name "*.swift" -o -name "*.scala" -o -name "*.cs" -o -name "*.hs" -o -name "*.ex" -o -name "*.jl" -o -name "*.lua" -o -name "*.dart" -o -name "*.rb" -o -name "*.R" -o -name "*.proto" \) | wc -l)

    echo "  시뮬레이션 모듈: ${PY_FILES}"
    echo "  테스트 파일:     ${TEST_FILES}"
    echo "  다중 언어 모듈:  ${MULTI_LANG}"

    # LOC 카운트
    PY_LOC=$(find "$PROJECT_DIR" -name "*.py" -not -path "*/__pycache__/*" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
    echo "  Python LOC:      ${PY_LOC}"

    # Git 상태
    cd "$PROJECT_DIR"
    COMMIT=$(git log --oneline -1 2>/dev/null || echo "N/A")
    BRANCH=$(git branch --show-current 2>/dev/null || echo "N/A")
    echo "  Git 브랜치:      ${BRANCH}"
    echo "  최신 커밋:       ${COMMIT}"

    echo "─────────────────────────────────"
}

# ── 메인 ─────────────────────────────────────────────────

usage() {
    echo "SDACS 배포 도구"
    echo ""
    echo "사용법: $0 <명령>"
    echo ""
    echo "명령:"
    echo "  check      환경 검증"
    echo "  install    의존성 설치"
    echo "  test       테스트 실행"
    echo "  simulate   시뮬레이션 실행 [duration] [seed]"
    echo "  dashboard  3D 대시보드 시작"
    echo "  status     시스템 상태 확인"
    echo "  deploy     전체 배포 (check → install → test)"
    echo "  all        전체 실행 (deploy + simulate)"
}

case "${1:-help}" in
    check)     check_env ;;
    install)   install_deps ;;
    test)      run_tests ;;
    simulate)  run_simulation "${2:-60}" "${3:-42}" ;;
    dashboard) start_dashboard ;;
    status)    status ;;
    deploy)    check_env && install_deps && run_tests ;;
    all)       check_env && install_deps && run_tests && run_simulation 60 42 ;;
    *)         usage ;;
esac
