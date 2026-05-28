# SDACS — Codex 실행 계획 (핸드오프 문서)

> 이 문서는 **Codex(코딩 에이전트)가 세션 컨텍스트 없이 단독 실행**할 수 있도록 작성된 자기완결적 계획서다.
> 작업 브랜치: `claude/ruview-wifi-analysis-2YG4p` (→ `main` 대상 PR #32).
> 모든 규칙은 `CLAUDE.md` 및 `.claude/rules/*`를 우선 준수한다.

---

## 0. 프로젝트 컨텍스트

- **SDACS** = 군집드론 공역통제 자동화 시스템. SimPy 이산 이벤트 시뮬레이션 + Three.js/Dash 시각화.
- **메인 시뮬레이터(캐논)**: 루트 `swarm_3d_simulator.html` — Three.js 단일 파일(~5,300줄). 프로젝트 대표 데모.
- **캐논 동기화 규칙(중요)**: 루트 `swarm_3d_simulator.html` 편집 후 반드시 아래 사본에 복사한다.
  - `visualization/swarm_3d_simulator.html` (main.py `visualize`가 서빙)
  - `docs/swarm_3d_simulator.html`, `docs/simulator.html` (GitHub Pages 진입점)
  - CI `.github/workflows/deploy-pages.yml`의 Sync 스텝이 `main` 머지 시 루트→docs 동기화(이미 `simulator.html` 별칭 포함).
  - 건드리지 말 것: `swarm_3d_simulator.v1.backup.html`(백업), `swarm_3d_simulator_v2.html`(경량 별도판).
- **Python 엔진**: `simulation/simulator.py`의 `SwarmSimulator`(정식, engine_legacy 삭제됨), `main.py`(CLI), `visualization/simulator_3d.py`(Dash).
- **테스트**: `pytest tests/ -v` (2,823+/3,481+ 수집). 변경 전후 수집·통과 유지 권장.
- **코딩 규칙 요약**: 한국어 주석 관례, `np.random.default_rng(seed)`(재현성, `random.random()` 금지), 시크릿 하드코딩 금지, 함수 <50줄·파일 <800줄 지향, 불변 패턴 선호.
- **이번 세션까지 완료(커밋됨, PR #32 포함)**:
  - `0611b62` 드론 호버 라이브 툴팁 + 클릭 상세 패널 + 진입점 일원화 + README 갱신.
  - `7d7b1a4` 2×2 분석 뷰(① 3D 궤적 ② XY 평면도(고도 컬러맵) ③ 배터리 추이 ④ KPI 대시보드).
  - `window._sdacs` API 확장: `selectDrone`/`hoverDrone`/`getSelected`/`clearHover`/`setAnalysisView`/`analysisMode`.

---

## Task A — 전체 소스코드 주석 (repo-wide) [선행, 저위험]

**목표**: 가독성을 위한 **의미 있는** 주석 추가. 자명한 내용 반복·줄단위 노이즈 금지. WHY/비자명 로직/섹션·함수 헤더 중심.

**범위(레포 전체)**
- Python: `simulation/**`, `src/**`, `main.py`, `chatbot/**`, `scripts/**`, `benchmarks/**`, `api/**`, `gen_*.py`.
- JS: `swarm_3d_simulator.html` 내 `<script type="module">` 전체(섹션 배너 + 함수 상단 1줄 + 비자명 알고리즘 주석).
- 기타 주요 소스. 생성물/벤더/`archive/**`/대용량 데이터는 제외.

**스타일**
- Python: 모듈·클래스·공개 함수에 한국어 docstring(목적/주요 인자/반환), 비자명 로직에 인라인 주석.
- JS: `// ===== 섹션 =====` 배너 유지·보강, 함수 상단 한 줄 요약, APF/CPA/GPU 등 비자명 로직 설명.

**제약(엄수)**
- **동작 변경 금지** — 주석만 추가. 토큰/공백 외 로직 diff 0.
- 자동 포맷(ruff/black, 프로젝트 설정 따름) 통과 유지. `.pre-commit-config.yaml` 준수.
- 대용량 파일(특히 HTML 5,300줄)은 청크 단위로 안전하게 편집. 편집 후 HTML은 module script 추출 `node --check`로 구문 검증.

**검증**: `pytest tests/` 수집·통과 동일, `ruff`/`mypy`(설정 존재 시) 통과, HTML 구문 유효, 캐논 사본 4개 동기화.

---

## Task B — 메인 시뮬레이터 로드맵 (Phase 1~5)

> 대상: `swarm_3d_simulator.html`. 각 Phase 완료 시 사본 동기화 + 커밋 + push. 헤드리스 스크린샷으로 검증.

### 재사용 자산 맵 (중복 구현 금지)
| 기능 | 심볼/위치 |
|---|---|
| 드론 생성/업데이트 | `createDrone`, `updateDrone`(거리 누적 `distanceTraveled += speed*dt`) |
| 충돌 회피(CPU 폴백) | `apfCollisionAvoidance` + `_conflictCooldown`/`_cooldown`/`_nearCooldown` |
| CPA 예측 | `CPA_LOOKAHEAD=12`, 함수 내 `tCPA`/`cpaDist`/`isConverging` 계산 |
| 거리 상수 | `EVADE_DIST=500`, `NEAR_MISS_DIST=100`, `COLLISION_DIST=30` |
| 근접선 풀 | `addProximityLine`, `_linePool`/`_linePoolIdx` |
| GPU/Worker APF | `_gpuDevice`/`applyGpuForces`/`dispatchGpuCompute`, `_apfWorker`/`applyWorkerForces` |
| 공역 요소 | NFZ `nfz`/`nfzEdge`/`inNFZ`(±500m), `ALTITUDE_LAYERS`(9), `scanRings`, `atcLinkGroup`/`updateATCLinks` |
| 차트 | `chartHistory`, `drawChart`/`drawLine`/`drawArea`/`drawBars`, `sampleChartData`, `renderAnalytics` |
| 통계 | `stats`{conflicts,nearMisses,collisions,advisories} |
| 분석 뷰 | `toggleAnalysis`/`drawTopDown`/`drawBatteryLines`/`renderKPI`, `battTracked` |
| 경량/대수 | `_lightweight`(>100대), `SCENARIOS`(최대 250대) |
| 외부 API | `window._sdacs`(start/stop/select/hover/analysis/captureScreenshot) |
| 라이브 데이터 | `simulation/ws_bridge.py`(ws://localhost:8765 스트리밍) |
| 리포트 레퍼런스 | `gen_report_v6.py`/`gen_report_v7_easy.py`(KPI 정의) |

### Phase 1 — 충돌·공역 관제 시각화 [BlueSky/U-TRAFMAN]
**주의**: `apfCollisionAvoidance`(CPU)는 GPU/Worker 미사용 시에만 도는 폴백이므로, **백엔드 독립적인 별도 시각화 패스**로 구현한다(별도 line pool 사용, APF 로직 비침습).
- **CPA 충돌 예측선**: `updateConflictViz()` 신규 — airborne 쌍 CPA 계산(기존 공식 재사용), 수렴(`isConverging`) & `cpaDist<NEAR_MISS_DIST` & `tCPA<CPA_LOOKAHEAD`이면 예측 최근접점 마커 + 연결선, TTC·이격거리 라벨, 위험도 색상. 토글, 저빈도(예 6프레임), 쌍 상한.
- **어드바이저리 오버레이**: `phase==='EVADING'`(및 RTL/HOLDING) 드론 위 빌보드 아이콘(점멸). `makeTextSprite` 재사용.
- **공역 레이어 토글 패널**: 좌측 `ctrl-panel`에 체크박스 — NFZ / 고도 레이어 / ATC 커버리지 / 충돌 예측선 show·hide(기존 씬 그룹 visible 토글).
- 분석 뷰 Q2(`drawTopDown`)에 충돌쌍·회랑 오버레이 동기화.

### Phase 4 — 리포트·내보내기 [gen_report 동등] (Phase 1 다음 권장, 저위험)
- **4분할 PNG 내보내기**: 합성 캔버스(3D `captureScreenshot()` + 2D 캔버스 3개) → 단일 리포트 PNG 다운로드.
- **CSV 내보내기**: `chartHistory` 시계열 + per-drone 텔레메트리 + KPI.
- **세션 리포트(HTML/MD)** 다운로드 + KPI 클립보드 복사.
- KPI 정의를 `gen_report_v6.py`와 일치(충돌해결률·경로효율·에너지효율 Wh/km·CBS·통신손실률).

### Phase 3 — 리플레이·멀티뷰 [Skybrush Live]
- **상태 레코더**: 0.5s 간격 스냅샷(위치/phase/battery) 링버퍼(메모리 상한).
- **타임라인 스크러버**: 재생/일시정지/속도/탐색 → 기록 재생(라이브↔리플레이 토글).
- **동기화 멀티뷰**: 분석 뷰 확장 — 3D + 2D맵 + 편대 리스트 + 타임라인, 선택 동기화.
- (옵션) `ws_bridge.py` 연동: 실 SwarmSimulator 데이터 라이브 수신 → 데모/실데이터 토글.

### Phase 2 — 대규모 GPU 군집 [three.js GPGPU / Potato] (고위험, 최후)
- **InstancedMesh 전환**: 드론 본체/로터를 개별 `THREE.Group`→`InstancedMesh`(인스턴스 행렬 + per-instance color). 목표 1,000~10,000대.
- 선택/툴팁 raycast를 인스턴스 id 기반으로 재작성, 트레일/글로우 상한, LOD·프러스텀 컬링.
- GPU APF 결과를 인스턴스 버퍼에 직접 기록. 신규 시나리오 `mega_swarm`(1000/5000) + 셀렉터.
- **회귀 위험 큼**: 기존 선택/툴팁/분석 뷰가 깨지지 않도록 단계적 전환 + 매 단계 스크린샷 검증.

### Phase 5 — 통합 & 검증
- 진입점 최종 정리(`docs/index.html` 데모 CTA, v2/backup 디프리케이트 명시), README 로드맵 반영.
- **Playwright 헤드리스 스모크 테스트**(각 뷰/토글/선택/리플레이) → `.github/workflows` CI 잡 추가.

---

## 실행 순서(권장 우선순위)
1. **Task A**(주석, 선행·저위험) → 2. **Phase 1**(충돌·공역 시각화) → 3. **Phase 4**(리포트, 저위험·고가치) → 4. **Phase 3**(리플레이) → 5. **Phase 2**(대규모 GPU, 고위험) → 6. **Phase 5**(통합·검증).

## 검증 방법(공통)
- 로컬: `python3 -m http.server 8123` 후 `http://localhost:8123/swarm_3d_simulator.html`.
- 헤드리스: Playwright Chromium(`/opt/pw-browsers`) + WebGL 플래그 `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`, 컨텍스트 `ignoreHTTPSErrors:true`(사내 CDN TLS 가로채기 대응). `window._sdacs`로 결정적 상태 트리거 후 `page.screenshot`.
- Python: `pytest tests/`, `ruff`, `mypy`(설정 존재 시).
- HTML 구문: module script 추출 후 `node --check`.

## Git 워크플로
- 작업 브랜치 `claude/ruview-wifi-analysis-2YG4p`에서 진행, push 후 PR #32 자동 갱신.
- 캐논 편집 시 사본 4개 동기화. 커밋 컨벤션 `feat:/fix:/refactor:/docs:/test:/chore:`. 시크릿 금지, 훅 우회 금지.
