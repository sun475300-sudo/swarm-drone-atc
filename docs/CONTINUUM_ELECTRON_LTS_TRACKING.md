# 💻 SDACS Electron LTS 추적 정책 (Phase 484)

*ODYSSEY Track ♾️ Continuum — Phase 484 산출물*
*Created: 2026-06-24 · 데스크탑 앱 장기 지속성 보장*

## 1. 배경

SDACS Desktop App 은 **Electron** 기반 3-OS 빌드(Windows/macOS/Linux). Electron 은 6주 마이너·12주 메이저 릴리스 사이클 + Chromium·Node.js·V8 의 보안 패치 흡수가 핵심. v1.5.0 (2026-06) 빌드는 `electron@32.3.3` 으로 발행됐으나 현재 적체 PR(#426)이 `electron@42.4.1` 로 11 메이저 업그레이드 제안.

본 문서는 **v32 → v39 교훈 + 향후 LTS 추적 절차** 를 정의한다.

---

## 2. Electron 릴리스 모델

### 2.1 릴리스 주기 (2024년 이후)

| 항목 | 주기 |
|---|---|
| 메이저 버전 | 8주 (이전 12주 → 단축) |
| 동시 지원 메이저 | **최신 3개** (예: 41·40·39 active) |
| 보안 패치 | 1주 (zero-day 즉시) |
| LTS (Long-Term Support) | **별도 없음** — 최신 3개만 보장 |
| EOL | 4번째 이전 메이저 (예: 41 출시 시 38 EOL) |

### 2.2 Chromium 정렬

Electron N = Chromium (M - 7) 대략 정렬. 예:
- Electron 32 → Chromium 128
- Electron 39 → Chromium 135
- Electron 42 → Chromium 138

→ Chromium 보안 권고(CVE)가 직접 영향.

---

## 3. v32 → v39 마이그레이션 교훈

### 3.1 변경 영향

| 영역 | v32.3.3 (2026-06 빌드) | v39+ (목표) | 영향 |
|---|---|---|---|
| Node.js | 22.4 | 22.x LTS | 호환 (보안 패치만) |
| V8 | 12.8 | 13.x | ECMAScript proposals 진행 |
| Chromium | 128 | 135+ | CSP·WebGPU·CORS 정책 변화 가능 |
| `contextIsolation` | true (기본) | true (강제) | SDACS 이미 준수 |
| `nodeIntegration` | false | false (강제) | SDACS 이미 준수 |
| `sandbox` | true | true (강화) | SDACS 이미 준수 |

### 3.2 발견된 호환성 이슈 (v32 빌드 기준)

| 이슈 | 영향 |
|---|---|
| `screen.getAllDisplays()` reflection 변경 | 멀티-모니터 검출 — Electron 38+ |
| `BrowserWindow.setMenuBarVisibility` deprecation | Linux UI — Electron 40+ |
| `webContents.executeJavaScript` 동기 변형 제거 | (SDACS 미사용) |
| `app.getPath('userData')` permissions 변경 | macOS 14+ — 사용자 폴더 권한 |
| Chromium 130 → 135 WebGPU 안정화 | SDACS APF GPU 가속에 긍정적 |

### 3.3 v1.5.0 → v1.6.x 업그레이드 시 점검 항목

```
1. CHANGELOG 읽기 (electron, chromium, node)
   - https://www.electronjs.org/blog
   - https://chromereleases.googleblog.com/

2. 3-OS 자동 빌드 (.github/workflows/desktop-build.yml)
   - Windows: NSIS 인스톨러
   - macOS: DMG + notarization
   - Linux: AppImage

3. 회귀 점검
   - Playwright E2E (시뮬레이터 동작)
   - 브라우저 API 카나리 (Phase 482) → 폐기 API 자동 탐지
   - 4 사본 md5 일치
   - API 정합성 게이트

4. 보안 점검
   - Trivy 컨테이너 스캔
   - Bandit Python 정적 분석
   - pip-audit (Python 의존성)
   - npm audit (Node 의존성)

5. 사용자 영향 평가
   - 시작 시간 (cold start)
   - 메모리 사용량
   - GPU 호환성 (특히 Intel iGPU·구형 NVIDIA)
```

---

## 4. 추적 정책 (Tracking Policy)

### 4.1 일상 추적 (Quarterly Review)

- **분기마다** Electron Blog + Chromium Releases 점검
- 새 메이저 출시 시 본 문서에 표 1건 추가
- EOL 임박 시 (현재 사용 버전이 곧 EOL) → 마이그레이션 PR 우선순위 상향

### 4.2 자동 알림 (Dependabot)

`.github/dependabot.yml` 의 `npm` 생태계 weekly 업데이트로 자동 PR 발행. Phase 481 정책 §3.3 (Tier 3) 에 따라 Electron 메이저는 cautious 검토 (2주 SLO).

### 4.3 호환성 셰임 (Compatibility Shim)

deprecation 발견 시:
1. 즉시 호환 셰임 추가 (deprecated API → 신 API 변환 wrapper)
2. CHANGELOG 에 deprecation 명시
3. 다음 메이저 업그레이드 시 셰임 제거 + 직접 신 API 사용

예시 (가상):
```javascript
// Phase 484 셰임: setMenuBarVisibility deprecated (Electron 40+)
function setMenuBarVisibility(win, visible) {
  if (typeof win.setAutoHideMenuBar === 'function') {
    win.setAutoHideMenuBar(!visible);
    win.setMenuBarVisibility(visible);  // 호환 (Electron 32-39)
  } else {
    win.menuBarVisible = visible;  // Electron 40+
  }
}
```

---

## 5. 권장 업그레이드 일정

| 시점 | Electron 버전 | 사유 |
|---|---|---|
| **현재** | 32.3.3 (v1.5.0 빌드) | 안정·검증 완료 |
| 2026-Q4 | 39.x (3 메이저 점프) | Chromium 135 + 보안 패치 |
| 2027-Q1 | 41.x (Dependabot #426 후속) | 최신 active 진입 |
| 2027-Q2~ | 분기마다 1 메이저 점프 (점진) | EOL 임박 회피 |

**제약**: 사용자 테스트 (실제 데스크탑 환경) 의존. sandbox 에서는 정책 문서 + 3-OS CI 빌드만 가능.

---

## 6. 한계 (정직성 공시)

- 본 정책은 sandbox 가 수행 가능한 **빌드 검증** + **자동 회귀** 에 한정
- **인적 검증** (UX·UI·실 사용자 워크플로): 사용자 환경 의존
- **OS 별 특이 사항** (macOS notarization·Windows code signing): 사용자 인증서 필요
- **Electron 보안 권고 응답**: 본 문서 §4.2 자동 알림 + Phase 481 정책 보강

---

## 7. 참조

- Electron Blog: <https://www.electronjs.org/blog>
- Chromium Releases: <https://chromereleases.googleblog.com/>
- Electron Security: <https://www.electronjs.org/docs/latest/tutorial/security>
- `docs/V1_5_0_RELEASE_INSTRUCTIONS.md` — v1.5.0 빌드 절차
- `.github/workflows/desktop-build.yml` — 3-OS CI 빌드
- `docs/CONTINUUM_DEPENDABOT_POLICY.md` — Phase 481 (Tier 3 major 정책)
- `scripts/browser_api_canary.py` — Phase 482 (브라우저 API 폐기 감시)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track ♾️ — Phase 481-500
