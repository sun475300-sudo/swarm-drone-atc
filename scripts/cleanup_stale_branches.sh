#!/usr/bin/env bash
# SDACS 원격 stale 브랜치 정리 — 안전 dry-run + 사용자 확인 후 삭제.
#
# 사용:
#   ./scripts/cleanup_stale_branches.sh                  # dry-run (기본)
#   ./scripts/cleanup_stale_branches.sh --dry-run        # 명시 dry-run
#   ./scripts/cleanup_stale_branches.sh --interactive    # 1개씩 확인 후 삭제
#   ./scripts/cleanup_stale_branches.sh --pattern "claude/fervent-babbage-*"
#   ./scripts/cleanup_stale_branches.sh --delete-all     # 자동 일괄 삭제 (위험)
#
# 안전 보장:
#   - origin/main 에 흡수 완료(ahead=0) 브랜치만 후보
#   - SAFETY_LIST (main / 현재 작업 / 명시 보존) 자동 제외
#   - dry-run 이 기본 (--delete-all / --interactive 없으면 출력만)
#
# CLAUDE.md: NEVER push to a different branch without explicit permission.
# 본 스크립트는 사용자가 직접 실행 (sandbox 자동 실행 금지).

set -uo pipefail

# ============================================================
# 설정
# ============================================================
SAFETY_LIST=(
    "origin/main"
    "origin/HEAD"
    "origin/claude/ruview-wifi-analysis-2YG4p"   # 현 작업 브랜치
    "origin/fix/desktop-build-cache"             # 미머지
    "origin/fix/main-merge-conflicts"            # 미머지
    "origin/perf/simulator-hotloop-allocations"  # 미머지
)

MODE="dry-run"
PATTERN=""

# ============================================================
# 인자 파싱
# ============================================================
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)       MODE="dry-run" ;;
        --interactive)   MODE="interactive" ;;
        --delete-all)    MODE="delete-all" ;;
        --pattern)       PATTERN="$2"; shift ;;
        --help|-h)
            grep -E '^# ' "$0" | sed 's/^# //'
            exit 0 ;;
        *)
            echo "❌ 알 수 없는 옵션: $1"
            exit 1 ;;
    esac
    shift
done

# ============================================================
# safety_list 검사
# ============================================================
is_safe() {
    local br="$1"
    for safe in "${SAFETY_LIST[@]}"; do
        if [ "$br" = "$safe" ]; then return 1; fi
    done
    return 0
}

# ============================================================
# stale 브랜치 식별 (origin/main 에 ahead=0)
# ============================================================
echo "🔍 stale 브랜치 식별 중..."
git fetch origin --prune >/dev/null 2>&1

STALE_BRANCHES=()
for br in $(git branch -r --format='%(refname:short)' | grep -v "origin/HEAD"); do
    # safety list 제외
    if ! is_safe "$br"; then continue; fi
    # 패턴 필터
    if [ -n "$PATTERN" ]; then
        case "$br" in
            origin/$PATTERN) ;;
            *) continue ;;
        esac
    fi
    # ahead 검사
    ahead=$(git rev-list --count origin/main.."$br" 2>/dev/null) || continue
    if [ "$ahead" = "0" ]; then
        STALE_BRANCHES+=("$br")
    fi
done

TOTAL=${#STALE_BRANCHES[@]}
echo "📊 stale 브랜치: $TOTAL 개 (origin/main 흡수 완료)"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo "✅ 삭제 후보 없음."
    exit 0
fi

# ============================================================
# 모드별 처리
# ============================================================
case "$MODE" in
    dry-run)
        echo "📋 dry-run — 다음 브랜치가 삭제 후보입니다 (실제 삭제 X):"
        printf '  %s\n' "${STALE_BRANCHES[@]}"
        echo ""
        echo "삭제하려면:"
        echo "  ./scripts/cleanup_stale_branches.sh --interactive    # 1개씩 확인"
        echo "  ./scripts/cleanup_stale_branches.sh --delete-all     # 일괄 삭제 (위험)"
        ;;

    interactive)
        echo "⚠️  --interactive: 1개씩 확인 후 삭제합니다."
        echo "    각 브랜치마다 [y/N] 입력 — y 시 삭제, 그 외는 건너뜀."
        echo ""
        DELETED=0
        for br in "${STALE_BRANCHES[@]}"; do
            local_name="${br#origin/}"
            printf "삭제? %s [y/N] " "$br"
            read -r answer < /dev/tty
            if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
                git push origin --delete "$local_name" && DELETED=$((DELETED+1))
            fi
        done
        echo ""
        echo "✅ 삭제 완료: $DELETED / $TOTAL"
        ;;

    delete-all)
        echo "🚨 --delete-all: 자동 일괄 삭제."
        echo "    최종 확인 [yes 입력 시 진행, 그 외 취소]:"
        read -r confirm < /dev/tty
        if [ "$confirm" != "yes" ]; then
            echo "❌ 취소됨."
            exit 1
        fi
        DELETED=0
        for br in "${STALE_BRANCHES[@]}"; do
            local_name="${br#origin/}"
            if git push origin --delete "$local_name" 2>/dev/null; then
                DELETED=$((DELETED+1))
            fi
        done
        echo ""
        echo "✅ 삭제 완료: $DELETED / $TOTAL"
        ;;
esac
