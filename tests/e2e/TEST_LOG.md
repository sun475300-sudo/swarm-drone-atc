# SDACS 시뮬레이터 — 테스트 로그 & 버그 리스트

> 대상: `swarm_3d_simulator.html` (메인 3D 웹 시뮬레이터)
> 테스트: `tests/e2e/smoke_sim.mjs` (Playwright 헤드리스, WebGL swiftshader)
> 실행: `npm run pw:install` 후 `python3 scripts/serve.py` → `npm run smoke`

---

## 1. 스모크 테스트 결과 (최근 실행)

환경: headless Chromium + `--use-angle=swiftshader`, `ignoreHTTPSErrors`, three.js r162(unpkg CDN)

```
PASS  드론 스폰 (50대)
PASS  이륙/비행 (8대 공중)
PASS  외부 탐지·식별 (탐지 12/식별 12/조류 6)
PASS  드론 선택 (DR-001)
PASS  호버 툴팁 (DR-002)
PASS  분석 뷰 ON
PASS  리플레이 레코더 (34 프레임)
PASS  리플레이 시크(0)
PASS  리포트 PNG 생성
PASS  대규모 InstancedMesh (1000대, inst=1000)
PASS  런타임 에러 0건

✅ 스모크 테스트 전체 통과 (11/11, exit 0)
```

| # | 검증 항목 | 대상 기능 | 결과 |
|---|---|---|---|
| 1 | 드론 스폰 | `createDrone`/`initDrones` | PASS |
| 2 | 이륙/비행 | `updateDrone` 상태머신 | PASS |
| 3 | 외부 탐지·식별 | DnI(`updateExternals`) | PASS |
| 4 | 드론 선택 | raycast/`selectDrone` | PASS |
| 5 | 호버 툴팁 | `hoverDrone`/`setHover` | PASS |
| 6 | 분석 뷰 | `toggleAnalysis` | PASS |
| 7 | 리플레이 레코더 | `recorder`/`recordSnapshot` | PASS |
| 8 | 리플레이 시크 | `replaySeek`/`applyFrame` | PASS |
| 9 | 리포트 PNG | `buildReportCanvas` | PASS |
| 10 | 대규모 InstancedMesh | `syncInstances`(megaMode) | PASS |
| 11 | 런타임 에러 0건 | pageerror 수집 | PASS |

> 주: 헤드리스 swiftshader FPS는 3~5fps로 실제 GPU 성능과 무관(렌더 병목). 본 스모크는 **기능·무에러 회귀** 검증용이며 FPS 수치는 측정 대상이 아니다.

---

## 2. 버그 리스트

### 2-1. 수정 완료 (Fixed)

| ID | 심각도 | 증상 | 원인 (주석) | 수정 | 커밋 |
|---|---|---|---|---|---|
| B1 | **CRITICAL** | 시뮬레이터 로드 즉시 크래시(`_sdacs` 미정의) | 병렬 커밋 `f9f843c` 머지로 `initDrones`에 정의 없는 `resetConflictViz()` 호출 잔존 | `resetConflictViz`/`resetAdvisory` 정의(충돌·어드바이저리 풀 초기화) | `a0eefaf` |
| B2 | HIGH | `updateConflictViz`/`updateAdvisoryOverlay` 매 프레임 2회 실행(낭비·플리커) | `f9f843c` 머지가 animate에 중복 호출 블록 추가 | 중복 블록 제거(정식 블록만 유지) | `afa66c2` |
| B3 | HIGH | `tg-atc` 토글 시 `null.visible` 가능성 | `atcLinkGroup`/`atcCoverageGroup`이 늦게 할당되는데 리스너에서 무가드 접근 | `if (group)` null 가드 | `afa66c2` |
| B4 | HIGH | 장시간 실행 시 GPU 메모리 누수 | DnI 외부 객체 퇴출 시 geometry/material/라벨 텍스처 `dispose` 누락 | `_disposeExt`에 traverse dispose + 라벨 map dispose | `afa66c2` |
| B5 | HIGH | 추적캠 이동 시 프러스텀 컬링 1프레임 지연(드론 깜빡임) | `syncInstances`가 `camera.matrixWorldInverse` 갱신 전 사용 | 컬링 전 `camera.updateMatrixWorld()` | `afa66c2` |
| B6 | HIGH | 저FPS(헤드리스)에서 외부 탐지 미동작 + 스모크 플래키 | 탐지 스로틀 `frameCount % 6`가 매초 리셋되어 저FPS서 6 도달 못 함 | 시간 기반 스로틀(0.3s 누적)로 교체 | `bb9c50f` |
| B7 | MEDIUM | 100~499대 구간 매 프레임 O(N·M) 센서 거리검사 | `updateExternals` 센서망 매 프레임 재구성·전수 검사 | 스로틀(시간 기반)로 빈도 감소 | `afa66c2`·`bb9c50f` |
| B8 | LOW | `updateDrone`에서 `d.rotor` 잠재 null 역참조 | `d.body` 가드 안에서 `d.rotor` 무가드 접근(향후 변경 취약) | `if (d.rotor)` 가드 | `afa66c2` |

### 2-2. 미해결 / 보류 (Open)

| ID | 심각도 | 내용 | 주석(사유/계획) |
|---|---|---|---|
| O1 | MEDIUM | 공역 레이어 패널 2개 중복(`Airspace Layers`/`layer-*` vs `공역·관제 레이어`/`tg-*`) — 체크박스 상태 desync 가능 | 병렬 Codex `applyLayerVisibility` 시스템과 얽혀 리팩터 충돌 위험 → 보류. 계획: `tg-*` 단일 소스로 통합 또는 중복 패널 숨김 |
| O2 | MEDIUM | `rebuildConflictLabels`가 ~3Hz로 `makeTextSprite`(canvas+texture) 반복 생성 | disposed되나 GC 압력. 계획: 라벨 6개 텍스처 사전생성·재사용 |
| O3 | LOW | 경로효율(detail 패널)이 1을 크게 초과 | `distanceTraveled`가 다중 트립 누적이라 단일 leg 기준 아님. 계획: per-leg 거리 추적 |
| O4 | INFO(프로세스) | 동일 브랜치에 병렬 Codex 세션 동시 커밋 → 반복 충돌·B1 크래시 유발 | 시뮬레이터 작업 전용 브랜치 분리 권장 |

---

## 3. 회귀 방지
- CI: `.github/workflows/sim-smoke.yml`가 push/PR마다 위 11항목 헤드리스 검증.
- 모든 시뮬레이터 변경은 루트 편집 후 `visualization/`·`docs/simulator.html`·`docs/swarm_3d_simulator.html` 동기화.
