#!/usr/bin/env bash
# =============================================================================
# setup-gpg-signing.sh
# GPG 커밋 서명 자동 설정 스크립트
#
# 사용법:
#   chmod +x scripts/setup-gpg-signing.sh
#   ./scripts/setup-gpg-signing.sh
#
# 이 스크립트는 다음을 자동으로 수행합니다:
#   1. GPG 키 생성 (RSA 4096비트)
#   2. 생성된 키의 ID를 git config에 등록
#   3. commit.gpgsign true 설정
#   4. GitHub에 등록할 공개키 출력
# =============================================================================

set -euo pipefail

# ── 색상 출력 헬퍼 ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 의존성 확인 ─────────────────────────────────────────────────────────────
if ! command -v gpg &>/dev/null; then
    error "gpg가 설치되어 있지 않습니다."
    error "설치 방법:"
    error "  macOS  : brew install gnupg"
    error "  Ubuntu : sudo apt-get install gnupg"
    exit 1
fi

# ── git user 정보 확인 ───────────────────────────────────────────────────────
GIT_NAME=$(git config --global user.name  2>/dev/null || true)
GIT_EMAIL=$(git config --global user.email 2>/dev/null || true)

if [[ -z "$GIT_NAME" || -z "$GIT_EMAIL" ]]; then
    error "git user.name 또는 user.email이 설정되지 않았습니다."
    error "먼저 다음 명령을 실행해 주세요:"
    error "  git config --global user.name  \"이름\""
    error "  git config --global user.email \"your@email.com\""
    exit 1
fi

info "Git 계정 정보"
info "  이름  : $GIT_NAME"
info "  이메일: $GIT_EMAIL"
echo

# ── 기존 키 확인 ─────────────────────────────────────────────────────────────
EXISTING_KEY=$(gpg --list-secret-keys --keyid-format=long "$GIT_EMAIL" 2>/dev/null \
    | grep '^sec' | awk '{print $2}' | cut -d'/' -f2 | head -n1 || true)

if [[ -n "$EXISTING_KEY" ]]; then
    warn "이미 해당 이메일로 생성된 GPG 키가 존재합니다: $EXISTING_KEY"
    warn "새로 생성하지 않고 기존 키를 사용합니다."
    KEY_ID="$EXISTING_KEY"
else
    # ── GPG 키 배치 생성 ─────────────────────────────────────────────────────
    info "GPG 키를 생성합니다 (RSA 4096비트)..."

    GPG_BATCH_FILE=$(mktemp -t gpg-batch.XXXXXX)
    cat > "$GPG_BATCH_FILE" <<EOF
%no-protection
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: ${GIT_NAME}
Name-Email: ${GIT_EMAIL}
Expire-Date: 1y
%commit
EOF

    gpg --batch --gen-key "$GPG_BATCH_FILE"
    rm -f "$GPG_BATCH_FILE"

    KEY_ID=$(gpg --list-secret-keys --keyid-format=long "$GIT_EMAIL" \
        | grep '^sec' | awk '{print $2}' | cut -d'/' -f2 | head -n1)

    success "GPG 키 생성 완료: $KEY_ID"
fi

# ── git config 설정 ──────────────────────────────────────────────────────────
info "git config 설정 중..."

git config --global user.signingkey "$KEY_ID"
git config --global commit.gpgsign  true

# gpg 프로그램 경로를 명시적으로 설정 (일부 환경에서 필요)
GPG_PATH=$(command -v gpg)
git config --global gpg.program "$GPG_PATH"

success "git config --global user.signingkey  $KEY_ID"
success "git config --global commit.gpgsign   true"
success "git config --global gpg.program      $GPG_PATH"
echo

# ── macOS pinentry 설정 ──────────────────────────────────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
    if command -v pinentry-mac &>/dev/null; then
        GNUPG_DIR="${GNUPGHOME:-$HOME/.gnupg}"
        mkdir -p "$GNUPG_DIR"
        AGENT_CONF="$GNUPG_DIR/gpg-agent.conf"
        PINENTRY_LINE="pinentry-program $(command -v pinentry-mac)"

        if ! grep -qF "$PINENTRY_LINE" "$AGENT_CONF" 2>/dev/null; then
            echo "$PINENTRY_LINE" >> "$AGENT_CONF"
            success "macOS pinentry-mac 설정 완료: $AGENT_CONF"
        else
            info "macOS pinentry-mac이 이미 설정되어 있습니다."
        fi

        # gpg-agent 재시작
        gpgconf --kill gpg-agent 2>/dev/null || true
    else
        warn "pinentry-mac이 설치되어 있지 않습니다. 필요한 경우:"
        warn "  brew install pinentry-mac"
    fi
fi

# ── GitHub 등록용 공개키 출력 ────────────────────────────────────────────────
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}GitHub에 등록할 공개키 (아래 내용을 복사하세요):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
gpg --armor --export "$KEY_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
info "다음 단계:"
info "  1. 위 공개키 블록(-----BEGIN PGP PUBLIC KEY BLOCK----- 포함)을 복사합니다."
info "  2. GitHub → Settings → SSH and GPG keys → New GPG key 에 붙여넣습니다."
info "  3. 이후 커밋부터 자동으로 GPG 서명이 적용됩니다. (✅ Verified)"
echo
success "GPG 서명 설정 완료!"
