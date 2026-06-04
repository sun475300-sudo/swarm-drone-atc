# 🚀 SDACS 시뮬레이터 MEGA Ultra Plan (Phase 1-10)

*Created: 2026-06-04 — 정밀 감사 후 통합 마스터 플랜*

## 📊 정밀 감사 결과 (2026-06-04)

### 현재 보유 (✅ 22개)
InstancedMesh · mega_swarm 4종 · CPA 예측 · APF · GPU compute · Web Worker · Chart history · Replay 레코더 · 4-view 분석 · 다중 선택 · 호버 툴팁 · 상세 패널 · 이벤트 로그 · NFZ · 9-layer 고도 · 회랑 · 정밀 기상(마이크로버스트·스톰셀·태풍·결빙·돌풍) · 22 직군 · 66 시나리오 · 21 ATC zones · PNG/CSV/HTML/MD 리포트 · **🎮 ATC 콘솔 (Phase 1 완료)**

### 누락 (❌ 28개)
predictedTrail · velocityArrow · separationBubble · priorityIcon · cumulativeHeatmap · missionPlanning · A* · RRT · MediaRecorder · sunCycle · fog/rain/snow particles · UnrealBloom · SMAA · SSAO · FPVcamera · chaseCamera · PiP · faultInjection · GPSloss · motorFail · rogueDrone · dynamicNFZ · EMP · touchGesture · PWA · LaTeX · abComparison · 모바일 자동 LOD

---

## 🎯 통합 로드맵 (9 Phase, ~4,500 line, ~72 E2E 케이스)

| Phase | 트랙 | 상태 | 코드 | 테스트 | 우선순위 |
|---|---|---|---|---|---|
| **1** | **ATC** 관제 콘솔 | ✅ **완료** | +451 | 10/11 | P0 |
| **2** | **TAC** 전술 시각화 | ✅ **완료** | ~700 | 10 | P1 |
| **3** | **CIN** 시네마틱 | ✅ **완료** | ~600 | 8 | P2 |
| **4** | **CAM** 카메라 모드 | ✅ **완료** | ~450 | 6 | P2 |
| **5** | **MIS** 임무 계획 UI | ✅ **완료** | +350 | 9 | P3 |
| **6** | **INJ** 장애 주입 | ✅ **완료** | ~450 | 10 | P3 |
| 7 | ANA 분석 강화 | 후속 | ~550 | 8 | P3 |
| **8** | **AUD** 음성 확장 | ✅ **완료** | ~300 | 5 | P2 |
| 9 | MOB 모바일/PWA | 후속 | ~450 | 6 | P4 |
| 10 | 통합·문서·CI | 후속 | ~200 | — | — |

---

## Phase 2 — TAC 전술 시각화 (즉시 진행)

**5개 항목 우선순위:**
1. **TAC-1 예측 비행경로 라인** (가장 가치 높음, ~200 line)
2. **TAC-2 CPA 충돌점 마커** (논문 시연용, ~150 line)
3. **TAC-3 속도 벡터 화살표** (선택 드론, ~120 line)
4. **TAC-4 분리 거품** (선택 드론, ~150 line)
5. **TAC-5 우선순위 심볼** (~80 line)

### TAC-1 데이터 모델
```js
d._predTrail = {
  line: THREE.Line,
  geometry: BufferGeometry,
  positions: Float32Array(N*3),
  dirty: true,
  lastUpdate: 0,
};
const _predTrailGroup = new THREE.Group();
let _predHorizon = 8.0;       // seconds lookahead
let _predSteps = 8;           // 1초 간격 8 step
let _predEnabled = true;
let _predLOD = false;         // megaMode 자동 OFF
```

### TAC-1 알고리즘
```
for each drone (visible):
  for step = 0..N:
    t = step * (horizon / N)
    // 등속 직선 외삽 + APF 보정
    nx = wx + vx * t
    nz = wz + vz * t
    ny = wy + vy * t (clamp 5..180)
  vertex color gradient: alpha = 1 - step/N
  update BufferGeometry attribute
```

### TAC-1 UI 토글
좌측 공역·관제 레이어 패널에 추가:
```html
<label class="av-toggle"><input type="checkbox" id="tg-pred-trail" checked> 예측 경로 (8초)</label>
<label class="av-toggle"><input type="checkbox" id="tg-vel-arrow"> 속도 벡터</label>
<label class="av-toggle"><input type="checkbox" id="tg-sep-bubble"> 분리 거품</label>
```

### TAC-1 LOD 정책
- 드론 수 < 100: 8 steps × full update / frame
- 100 - 200: 4 steps × every 2 frames
- 200 - 500: 2 steps × every 4 frames
- megaMode (≥500): 자동 OFF (강제)

### TAC-1 E2E 테스트 (5)
1. 토글 ON 시 line 객체 생성 확인
2. positions.length === (N+1) * 3
3. mega 시나리오 자동 OFF
4. 등속 외삽 정확성 (vx=10 → t=4s → +40m)
5. `_sdacs.setPredTrail(false)` 즉시 비활성

---

## Phase 3 — CIN 시네마틱 모드 (후속)

핵심: 동적 태양·입자·포스트프로세싱·녹화·시네마틱 카메라·LUT.
의존: `three/addons/postprocessing/` 5종 모듈, MediaRecorder API.
세부 명세는 [`SIMULATOR_PHASE_PLANS.md`](SIMULATOR_PHASE_PLANS.md) §3 참조.

---

## Phase 4 — CAM 카메라 모드 (후속)

핵심: FPV / Chase / Top / Side / Free / PiP × 3.
단축키 1-4 모드 전환, T/S/O/F/R 시점 단축키.

---

## Phase 5 — MIS 임무 계획 (후속)

핵심: 클릭 웨이포인트·드론 할당·A\* 우회·5개 템플릿(수색/정찰/배달/방제/의료).
기존 `src/applications/agri_spray.py` (Voronoi)·`medical_delivery.py` (heap) 재사용.

---

## Phase 6 — INJ 장애 주입 (후속)

핵심: GPS 손실 / 모터 페일 / 배터리 급강하 / 통신 두절 / Rogue spawn / 동적 NFZ + EMP·EMI 시나리오 4종.
5계층 안전망 응답 시간 측정.

---

## Phase 7 — ANA 분석 강화 (후속)

핵심: 누적 히트맵 · 실시간 KPI 차트 · A·B 비교 · LaTeX 표 · 책임 분석 · 드론별 텔레메트리 CSV.

---

## Phase 8 — AUD 음성 확장 (후속)

핵심: 환경 사운드(풍속·우천·천둥) · 드론 모터음 · 임계 알람 톤 · TTS 50개 표준 문구.

---

## Phase 9 — MOB 모바일/PWA (후속)

핵심: 터치 제스처 · 반응형 UI · 자동 LOD · PWA Manifest · Service Worker · 풀스크린.

---

## Phase 10 — 통합·문서·CI (마지막)

- README 최신화 (모든 신규 기능 반영)
- `_sdacs` API 전체 문서화 (`docs/SDACS_API.md`)
- E2E 테스트 통합 매트릭스 (`.github/workflows/sim-smoke.yml`)
- 데모 영상 녹화 (Phase 3 CIN 녹화 기능 사용, 2분)
- 라이브 데모 GitHub Pages 동기화

---

## 📈 누적 KPI 목표

| 항목 | Phase 1 종료 | Phase 9 종료 (목표) |
|---|---|---|
| 시뮬레이터 코드 | 7,515 line | ~12,000 line |
| _sdacs API 항목 | 186 | ~280 |
| E2E 테스트 | 10/11 | ~75 |
| 회귀 pytest | 4,140 | 4,140 (보존) |
| 누락 기능 | 28 | 0 |
| 60fps 유지 (50대) | ✅ | ✅ |

---

## 🔁 실행 규칙

1. **각 Phase는 독립 PR** — 충돌 최소화
2. **Playwright E2E 테스트 필수** — 매 Phase 5-10 케이스 신설
3. **사본 동기화** — `swarm_3d_simulator.html` → `visualization/` → `docs/×2` (md5 확인)
4. **회귀 통과** — `pytest tests/ --no-cov` 4,140/4,140 보존
5. **README 즉시 반영** — 신규 기능 배지·하이라이트 갱신
6. **`node --check` JS 구문** 검증 필수

---

## 🎬 본 세션 즉시 진행 (Phase 2 TAC)

- [x] 정밀 감사 (위 §1)
- [x] MEGA 플랜 문서 작성 (본 문서)
- [▶] TAC-1 예측 비행경로 라인 구현
- [▶] TAC-2 CPA 충돌점 마커 + TTC 라벨
- [▶] TAC-3 속도 벡터 화살표
- [▶] E2E 테스트 추가
- [▶] 사본 동기화 + 회귀
- [▶] README 업데이트
- [▶] commit + push

후속: TAC-4/5 + Phase 3 CIN.
