# PR 적체 트리아지 — 2026-06-20 (일일 점검)

> Phase 481 의존성 자동 갱신 게이트 정책(`simulation/dependency_gate.py`)을 **현재 열린 PR**에 실제 적용한 결정적 트리아지.
> 자문 문서이며 집행이 아님 — 머지는 사람이 결정한다. 본 보고서는 그 결정에 필요한 근거를 한 장에 모은다.

## 요약

- 열린 PR **19건**: dependabot **14건** + 기능/성능 드래프트 **2건**(#283 핫루프, #280 Maturity Badge) + 일일 점검 자기참조 드래프트 **3건**(#394·#396·#400).
- Phase 481 정책 적용 결과(게이트 GREEN 가정 시 정책 상한): **AUTO_MERGE 2 · REVIEW_REQUIRED 12 · BLOCK 0**.
- 실측 게이트 확인: **#272·#278 만** `mergeable_state: clean` + CI 전체 GREEN(단, CI 실행 시점 2026-06-12 — 현 main 대비 stale, 재검증 권장).

## 🔴 우선 조치 — 보안 관련

**#277 electron 39.8.10 → 42.4.0** (dev/MAJOR → REVIEW_REQUIRED)
- 릴리스 노트에 **CVE-2026-9115, CVE-2026-9116 백포트** 포함 + Chromium 148 + Node 24.16.
- Phase 484(`electron_lts_policy`)가 이미 현 핀 `^39`을 **`UPGRADE_NOW (EOL, lag=3)`** 으로 공시 — 보안 백포트 창을 벗어난 런타임.
- MAJOR 점프라 정책상 REVIEW(자동 머지 불가)이지만 **보안상 가장 시급**. `mergeable_state: unknown` → dependabot rebase 후 데스크탑 빌드(electron-builder #279 동반) 검증 필요.

## dependabot 14건 분류 (Phase 481 정책)

### AUTO_MERGE 적격 (2) — 게이트 GREEN 확인됨
| PR | 패키지 | 변경 | 분류 | 실측 게이트 |
|---|---|---|---|---|
| #272 | pyyaml | 6.0.2→6.0.3 | runtime/PATCH | `clean` · CI GREEN |
| #278 | playwright | 1.56.1→1.60.0 | dev/MINOR | `clean` · CI GREEN |

→ 정책상 자동 머지 필요조건 충족. **권장: 재검증(현 main 대비 CI 재실행) 후 머지.**

### REVIEW_REQUIRED (12) — 사람 판단 필요
| PR | 패키지 | 변경 | 사유 |
|---|---|---|---|
| #277 | electron | 39→42 | dev/MAJOR · **보안 CVE 백포트** (위 우선 조치) |
| #279 | electron-builder | 25→26 | dev/MAJOR · #277과 동반 검증 |
| #275 | kaleido | 0.2→1.3.0 | runtime/MAJOR · 차트 렌더 회귀 위험 |
| #271 | github/codeql-action | 3→4 | ci/MAJOR |
| #270 | softprops/action-gh-release | 2→3 | ci/MAJOR |
| #269 | actions/deploy-pages | 4→5 | ci/MAJOR |
| #268 | actions/cache | 4→5 | ci/MAJOR |
| #267 | actions/setup-python | 5→6 | ci/MAJOR |
| #367 | starlette | 1.2.1→1.3.1 | runtime/MINOR |
| #276 | pydantic-core | 2.46.4→2.47.0 | runtime/MINOR |
| #274 | matplotlib | 3.9.0→3.10.9 | runtime/MINOR |
| #273 | joblib | 1.4.2→1.5.3 | runtime/MINOR |

> CI MAJOR 8건은 워크플로 동작 변화 가능 — 머지 후 다음 CI 1회 관찰 권장.
> runtime MINOR 4건은 정책상 REVIEW(동작 변화 가능) — 회귀 GREEN 시 낮은 위험.

### BLOCK (0)
다운그레이드·게이트 RED 해당 없음.

## 일일 점검 드래프트 자기참조 (3) — 정리 필요
- #400 (58차) ← #393~#399 일원화 / #396 (54차) ← #394 / #394 (52차) Phase 491.
- 동일 ODYSSEY Continuum 세대 이양 작업(Phase 491·492)이 3개 드래프트로 분기 적체. **단일 PR로 수렴 후 나머지 close 권장** (기존 "적체 드래프트 일원화" 패턴과 동일).

## 권장 처리 순서
1. **#277 electron**(+#279) 보안 — rebase → 데스크탑 빌드 검증 → 머지.
2. **#272·#278** — 현 main 기준 CI 재실행 GREEN 확인 → 머지(정책 자동 머지 적격).
3. dependabot rebase 일괄(8일 stale) → REVIEW 12건 회귀 GREEN 확인.
4. 일일 점검 드래프트 #394·#396·#400 단일 PR 수렴.
