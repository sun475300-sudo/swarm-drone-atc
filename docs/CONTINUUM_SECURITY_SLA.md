# 🔐 SDACS 보안 장기 지원 정책 (Phase 488)

*ODYSSEY Track ♾️ Continuum — Phase 488 산출물*
*Created: 2026-06-24 · CVE 대응 SLA + 핀 갱신 절차*

## 1. 목적

SDACS 가 장기적으로 보안 권고(CVE)에 결정적·예측 가능하게 대응할 수 있도록 **응답 SLA + 핀(pin) 갱신 절차** 를 명문화한다. Phase 481 (Dependabot 정책) 의 보안 우선순위 매핑을 보강한다.

---

## 2. 대응 SLA (Service Level Agreement)

### 2.1 CVSS 기반 응답 시간

| CVSS 점수 | 등급 | 응답 시한 | 머지 시한 | 릴리스 |
|---:|:-:|:-:|:-:|:-:|
| **9.0~10.0** | 🚨 CRITICAL | **6h** | **24h** | 즉시 패치 릴리스 |
| **7.0~8.9** | 🔴 HIGH | **24h** | **72h** | 다음 마이너 |
| **4.0~6.9** | 🟡 MEDIUM | **3d** | **1w** | 다음 정기 |
| **0.1~3.9** | 🟢 LOW | **1w** | 다음 정기 | 다음 정기 |

> **응답 시한**: 보안팀(현재 BDFL)이 acknowledge + triage 까지의 시간.
> **머지 시한**: 패치 PR을 머지하기까지의 시간.

### 2.2 CRITICAL 즉시 대응 절차

```
T+0    GitHub Security Advisory 수신 (자동 알림)
T+1h   BDFL/Steward triage → CRITICAL 확정
T+2h   영향 평가 (어떤 모듈·어떤 버전 영향)
T+4h   패치 PR 생성 (Dependabot 또는 수동)
T+6h   CI 회귀 GREEN (필수: 5,000+ pass / 0 fail)
T+12h  4 사본 md5 일치 + API 게이트 검증
T+24h  머지 + 즉시 패치 릴리스 (v1.x.y → v1.x.y+1)
T+48h  공개 보안 권고 발행 (`docs/security/CVE-YYYY-XXXX.md`)
```

### 2.3 영향 평가 매트릭스

| 모듈 영향 | 추가 검증 |
|---|---|
| `api/auth.py` (JWT) | 토큰 무효화 검토 + 회귀 |
| `api/fastapi_server.py` (WS) | 입력 검증 회귀 |
| `simulation/ws_bridge.py` | loopback 검증 + host 가드 |
| `simulation/federation_*.py` | 감사 로그 무결성 (Phase 429 SHA-256 체인) |
| Docker 베이스 이미지 | Trivy 재스캔 + 빌드 |
| Electron | 3-OS 자동 빌드 (Phase 484 정책) |
| 시뮬레이터 HTML | 4 사본 md5 + CSP 회귀 |

---

## 3. 핀(Pin) 갱신 정책

### 3.1 현재 핀 정책

| 의존성 | 핀 방식 | 사유 |
|---|---|---|
| Python `requirements.txt` | `~=` (compatible release) | 마이너만 자동, 메이저는 수동 |
| Node `package.json` | `^` (caret) | 마이너 자동 + 메이저 Dependabot |
| Docker `image.tag` | semver 명시 (`v1.5.0`) | latest 금지 (`docs/CONTINUUM_DEPENDABOT_POLICY.md`) |
| GitHub Actions | major (예: `@v4`) | Dependabot Tier 1 (auto-merge) |
| Electron | exact (`32.3.3`) | 메이저 업그레이드 별 검토 (Phase 484) |
| Playwright | exact (`1.56.1`) | 브라우저 호환 (Phase 482 카나리) |

### 3.2 핀 갱신 트리거

1. **CVSS HIGH+** → 즉시 갱신 (본 SLA §2.1)
2. **Upstream EOL** → EOL 60d 전 갱신 시작
3. **분기 정기** → 보안 외 마이너 정합성 점검
4. **CI 실패** → 의존성 conflict 해결 후 갱신

### 3.3 핀 다운그레이드 (롤백) 정책

신규 핀이 회귀를 유발 시:
1. 즉시 롤백 PR (이전 핀 복원)
2. 회귀 시나리오 명시 (`docs/security/ROLLBACK_YYYY-MM-DD.md`)
3. upstream issue 보고
4. workaround 패치 또는 다음 마이너 대기

---

## 4. 감사 로그 (Audit Trail)

### 4.1 보안 응답 기록

모든 CRITICAL/HIGH CVE 응답은 다음 형식으로 영구 기록:

```
docs/security/CVE-2026-XXXXX.md
  - CVE ID + 심각도 (CVSS)
  - 영향 받은 SDACS 버전 / 모듈
  - 발견 시각 (T+0) + 응답 시각 + 머지 시각
  - 패치 커밋 SHA + 릴리스 버전
  - 회귀 결과 (테스트 카운트)
  - upstream 출처 (GitHub Security Advisory URL)
```

### 4.2 정기 보고

분기마다 다음 집계 보고:
- 본 분기 응답한 CVE 개수 (등급별)
- 평균 응답·머지 시간 (SLA 준수율)
- 미대응 항목 (예외 사유)

→ `docs/security/QUARTERLY_REPORT_YYYY-QN.md`

---

## 5. 자동 도구

### 5.1 활성

| 도구 | 잡 | 주기 |
|---|---|:-:|
| **Trivy** | `.github/workflows/security.yml` Trivy Container Scan | PR + push |
| **Bandit** | Python 정적 보안 분석 | PR + push |
| **pip-audit** | `requirements.txt` CVE 매핑 | PR + push |
| **Dependabot** | `.github/dependabot.yml` (Phase 481) | weekly |
| **CodeQL** | Phase 488 후속 도입 후보 | (계획) |

### 5.2 미도입 (후속 후보)

- **OSV-Scanner** (Google Open Source Vulnerabilities) — Python·npm·Go 통합
- **Snyk** — 의존성 + 컨테이너 + IaC (상용)
- **GitHub Advanced Security** — secret scanning + push protection

---

## 6. 키 관리 (Cryptographic Material)

### 6.1 보유 키

| 키 | 보유자 | 갱신 주기 | 키 길이 |
|---|---|:-:|:-:|
| `SDACS_JWT_SECRET` | 운영 환경 (Helm Secret) | 분기 | 256+ bit |
| GPG commit signing | BDFL | 2년 | 4096 bit |
| Docker 이미지 signing | (미도입, 후보) | — | — |

### 6.2 키 유출 응답 (CRITICAL)

키 유출 발견 시:
1. **즉시** (T+0): 모든 호환 토큰 무효화
2. **T+1h**: 새 키 발행 + 환경변수 갱신
3. **T+6h**: 패치 릴리스
4. **T+24h**: 보안 권고 발행 + 사용자 안내
5. **T+1w**: 사후 분석 보고서

---

## 7. 한계 (정직성 공시)

본 정책이 다루지 않는 것:
- **실 비행 보안 (드론 hijacking)**: HW 의존, Track A
- **공급망 공격 (xz utils 류)**: upstream 도구(SLSA·Sigstore)는 도입 후보 (Phase 489)
- **운영 환경 관리 (시크릿 매니저)**: 사용자 환경 (Vault·AWS Secrets Manager 등)
- **GDPR / 개인정보**: SDACS 텔레메트리는 익명 시뮬 데이터, 개인정보 미수집

본 정책은 **BDFL 단일 책임 모델** 기준이며 Phase 487 Tri-Maintainer 전환 시 §2.1 SLA 가 위원회 의결로 강화될 수 있다.

---

## 8. 참조

- `docs/CONTINUUM_DEPENDABOT_POLICY.md` — Phase 481 (자동 머지 정책)
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` — Phase 487 (BDFL → 위원회)
- `docs/CONTINUUM_ELECTRON_LTS_TRACKING.md` — Phase 484 (Electron 업그레이드)
- `scripts/browser_api_canary.py` — Phase 482 (브라우저 API 카나리)
- `api/auth.py` — JWT prod 강제 + alg 검증
- `.github/workflows/security.yml` — Trivy + Bandit + pip-audit 잡
- GitHub Security Advisory: <https://github.com/advisories> (외부)
- CVE Database: <https://cve.mitre.org> (외부)
- CVSS 3.1 Calculator: <https://www.first.org/cvss/calculator/3.1> (외부)
