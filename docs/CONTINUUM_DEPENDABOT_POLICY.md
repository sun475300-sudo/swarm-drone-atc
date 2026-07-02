# ♾️ SDACS Dependabot 자동 갱신 정책 (Phase 481)

*ODYSSEY Track ♾️ Continuum — Phase 481 산출물*
*Created: 2026-06-24 · 10년 의존성 거버넌스 기준선*

## 1. 현황

`.github/dependabot.yml` 활성 — `github-actions` + `npm` 생태계 weekly (월요일 09:00 Asia/Seoul). open PR 한도 5건/생태계.

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    schedule: { interval: "weekly", day: "monday", time: "09:00", timezone: "Asia/Seoul" }
    open-pull-requests-limit: 5
  - package-ecosystem: "npm"
    schedule: { interval: "weekly", day: "monday", time: "09:15", timezone: "Asia/Seoul" }
    open-pull-requests-limit: 5
```

**현재 적체 (2026-06-22 기준)**: PR #267-#279, #367, #426-#427 = **14건 dependabot PR**.

---

## 2. 본 정책의 목적

dependabot PR 의 **자동 처리 규칙** 을 명문화하여 BDFL 1인이 (또는 Stage 2+ 위원회가) 결정적·예측 가능하게 처리한다. **회귀 게이트 + 자동 머지 정책** 으로 의존성 노후화를 차단한다.

---

## 3. 자동 머지 정책 (3-Tier)

### 3.1 Tier 1: 자동 승인+머지 (auto-merge)

**조건 (전부 충족)**:
- ✅ Dependabot 발행 PR (작성자: `dependabot[bot]`)
- ✅ semver **patch** 업데이트 (예: `1.2.3 → 1.2.4`)
- ✅ CI 전 잡 GREEN (18/18 — Trivy·Bandit·pip-audit 포함)
- ✅ `4 사본 md5 일치` 게이트 통과
- ✅ `API 정합성 게이트` GREEN

**적용 대상 (생태계)**:
- `github-actions` (모든 패치)
- `npm` 개발 의존성 (`devDependencies` 만)

**실행**: `gh pr merge --auto --squash` (또는 GitHub UI 자동 머지 활성화)

### 3.2 Tier 2: 사람 검토 + 머지 (manual review)

**조건**:
- semver **minor** 업데이트 (예: `1.2.x → 1.3.0`)
- 런타임 의존성 (production 영향)
- 새 lockfile entry (transitive dependency 추가)

**검토 항목**:
- CHANGELOG (upstream) 확인
- breaking change 가능성 (semver minor 라도 실제는 다를 수 있음)
- CI 전체 GREEN
- 회귀 5,000+ pass / 0 fail

**SLO**: 1주 내 결정 (승인 or close + 사유)

### 3.3 Tier 3: 신중 검토 (cautious)

**조건**:
- semver **major** 업데이트 (예: `1.x → 2.0`)
- 보안 알림 (Dependabot Security Update)
- 빌드 도구 변경 (electron, playwright 등)
- Python 메이저 (3.10 → 3.11 등)

**검토 항목**:
- breaking change 전수 검토
- 마이그레이션 가이드 정독
- 회귀 + E2E + 빌드 (3-OS) 검증
- 호환성 영향 평가 (`docs/API_DEPRECATION_POLICY.md`)
- 필요 시 별도 PR 분리

**SLO**: 2주 내 결정 (보안 알림은 72h)

---

## 4. 보안 업데이트 우선순위

GitHub Security Advisory (CVE) 매핑 시:

| CVSS | 처리 |
|:-:|---|
| **CRITICAL 9.0+** | 24h 내 패치 머지 (Tier 2/3 무관) |
| **HIGH 7.0-8.9** | 72h 내 |
| **MEDIUM 4.0-6.9** | 1주 내 |
| **LOW < 4.0** | 다음 정기 사이클 |

**보강**: Trivy + Bandit + pip-audit CI 잡 (이미 활성).

---

## 5. 게이트 (자동 검증)

본 정책은 다음 CI 게이트로 강제된다:

| 게이트 | 잡 | 패턴 |
|---|---|---|
| Python 회귀 | `test (3.10/3.11/3.12)` | `pytest tests/ --no-cov` |
| E2E | `Python Playwright E2E` | `pytest tests/e2e/` |
| Node 스모크 | `Node 헤드리스 스모크` | `node tests/e2e/smoke_*.mjs` |
| API 정합성 | `Python Playwright E2E` (게이트 단계) | `extract_sdacs_api.py --check` |
| 4 사본 md5 | `Python Playwright E2E` (게이트 단계) | md5sum + sort -u 단일 |
| Trivy 이미지 | `Trivy Container Scan` | Docker 이미지 CVE |
| Bandit Python | `Bandit Static Analysis` | 정적 보안 분석 |
| pip-audit | `pip-audit Dependency CVE Scan` | requirements.txt CVE |
| canonical-hash | `canonical-hash` | 결정적 해시 |

---

## 6. 적체 해소 (one-time, 2026-06)

현재 적체 14건 (PR #267-#279, #367, #426-#427) 일괄 처리 절차:

```bash
# Tier 1 후보 (patch + github-actions)
gh pr list --search "author:app/dependabot is:open" --json number,title,labels
# 각각: CI GREEN 확인 → gh pr merge <N> --squash --auto

# Tier 2/3 후보 (minor/major)
# 본 정책 §3.2/§3.3 절차로 개별 결정
```

**제약**: 위 명령은 사용자 환경 (gh CLI auth) 의존. sandbox 에서는 정책 문서화·CI 게이트 보강만 가능.

---

## 7. 분기 리뷰

- **분기마다** 본 정책 작동 평가
- 자동 머지 안전성 (false merge 0 확인)
- 적체 카운트 추적 (목표: open PR < 5 / 생태계)
- 평균 처리 시간 (Tier 1: 즉시, Tier 2: ≤ 7d, Tier 3: ≤ 14d)

---

## 8. 참조

- `.github/dependabot.yml` — 현재 활성 설정
- `.github/workflows/security.yml` — Trivy/Bandit 잡
- `.github/workflows/sim-smoke.yml` — pip-audit + 회귀 게이트
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Phase 481 — 본 문서의 ROADMAP 위치
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` Phase 487 — 위원회 의결 정합
- `docs/API_DEPRECATION_POLICY.md` Phase 209 — major 업데이트 시 적용
