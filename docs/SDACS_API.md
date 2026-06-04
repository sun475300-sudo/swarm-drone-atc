# SDACS 시뮬레이터 자동화 API 레퍼런스

브라우저 단독 실행 시뮬레이터 2종이 노출하는 `window` 전역 자동화 API 문서입니다.
헤드리스 E2E 테스트(`tests/e2e/`), 외부 SDK 연동, LIVE 텔레메트리 브릿지에서 사용합니다.

| 시뮬레이터 | 전역 객체 | 파일 |
|---|---|---|
| 군집 드론 3D | `window._sdacs` | `swarm_3d_simulator.html` |
| 해양 소형선 감지 | `window._mds` | `maritime_detection_simulator.html` |

> 본 문서는 소스 코드(`window._sdacs = { ... }` / `window._mds = { ... }` 정의 블록)에서 직접 도출했습니다.
> 시그니처 변경 시 본 문서와 `tests/e2e/` 스모크를 함께 갱신하세요.

---

## 1. `window._sdacs` — 군집 드론 3D 시뮬레이터

### 1.1 상태 조회 (getter)

| 멤버 | 반환 | 설명 |
|---|---|---|
| `stats` | object | 누적 통계 스냅샷(복사본) |
| `simTime` | number | 시뮬레이션 경과 시간(s) |
| `simRunning` | boolean | 실행 중 여부 |
| `droneCount` | number | 전체 드론 수 |
| `weather` | object | `{ icing, microbursts, stormCells, typhoonWind, turbulence, windSpd }` |
| `airborne` | number | 비행 중(GROUNDED·FAILED 제외) 드론 수 |
| `failed` | number | FAILED 상태 드론 수 |
| `landed` | number | GROUNDED 상태 드론 수 |
| `megaMode` | boolean | 대규모(InstancedMesh) 렌더 모드 여부 |
| `instanceCount` | number | body InstancedMesh 인스턴스 수 |
| `visibleInstances` | number | 컬링 후 가시 인스턴스 수 |
| `perf` | object | `{ fps, cpuMs, gpuMs, drawCalls, triangles, drones, megaMode, visibleInstances }` (B6) |
| `conflictPairs` | number | 현재 충돌쌍(conflict) 라인 수 |

### 1.2 시뮬레이션 제어

| 메서드 | 반환 | 설명 |
|---|---|---|
| `startSim()` | — | 시뮬레이션 시작 |
| `stopSim()` | — | 시뮬레이션 정지 |
| `selectScenario(name)` | — | 시나리오 드롭다운 선택 + change 이벤트 발생 |

### 1.3 드론 선택·호버 (B4)

| 메서드 | 반환 | 설명 |
|---|---|---|
| `selectDrone(idOrIndex)` | id\|null | 단일 선택(id 문자열 또는 인덱스) |
| `deselectDrone()` | — | 선택 해제 |
| `getSelected()` | object\|null | 선택 드론 스냅샷(three.js 핸들 제외) |
| `multiSelect(ids)` | number | 다중 선택, 선택 수 반환 |
| `clearMulti()` | — | 다중 선택 해제 |
| `multiSelection` (get) | string[] | 다중 선택 id 목록 |
| `hoverDrone(idOrIndex)` | id\|null | 호버 강조 |
| `clearHover()` | — | 호버 해제 |

### 1.4 분석 뷰·리포트

| 멤버 | 반환 | 설명 |
|---|---|---|
| `setAnalysisView(on)` | boolean | 2×2 분석 뷰 토글 |
| `analysisMode` (get) | boolean | 분석 뷰 상태 |
| `reportDataURL()` | Promise\<string> | 리포트 캔버스 PNG dataURL |
| `exportPNG` / `exportCSV` / `exportHTML` / `exportMD` | — | 리포트 내보내기 함수 |
| `captureScreenshot()` | string | 현재 렌더 PNG dataURL |

### 1.5 렌더·LIVE·리플레이

| 멤버 | 반환 | 설명 |
|---|---|---|
| `megaCull` (get/set) | boolean | 대규모 모드 컬링 on/off |
| `replayFrames` (get) | number | 녹화된 리플레이 프레임 수 |
| `replaySeek(idx)` | number | 리플레이 진입 + 해당 프레임 적용 |
| `replayStep(delta=1)` | number | 리플레이 프레임 이동(±) |
| `replay` (get) | object | `{ mode, playing, speed, idx, totalFrames, t }` (P734) |
| `goLive` | — | LIVE 모드 복귀 |
| `wsConnected` (get) | boolean | WebSocket 연결 여부 |
| `wsFrames` (get) | number | 수신 프레임 수 |
| `liveMode` (get) | boolean | LIVE 데이터 적용 중 여부 |
| `dni` (get) | object | 외부 드론·조류 탐지/식별 통계 (P723) |
| `lang` (get) / `setLang(lang)` | string | UI 언어(KO/EN) (P730) |
| `setLayer(name, on)` / `layers` (get) | — | 공역 레이어 가시성 (O1) |
| `camera` / `renderer` / `scene` / `controls` | — | three.js 핸들(고급 검사용) |

### 1.6 Phase 1 — ATC 관제 콘솔

| 메서드 | 반환 | 설명 |
|---|---|---|
| `atcCommand(did, cmd, params, source)` | — | 관제 명령(HOLD/RTB/REROUTE/ALT±/SPD±/TURN/CLEAR) |
| `atcLog` (get) | array | 관제 명령 감사 로그 |
| `atcControlled` (get) | array | `{ id, cmd, lockUntil }` 제어 중 드론 |
| `setAtcAudio(on)` | boolean | 한국어 TTS·비프 음성 토글 |
| `atcAudio` (get) | boolean | 음성 상태 |
| `clearAllAtc()` | number | 전체 ATC 명령 해제, 해제 수 반환 |

### 1.7 Phase 2 — TAC 전술 시각화

| 메서드 | 반환 | 설명 |
|---|---|---|
| `setPredTrail(on)` / `predTrail` (get) | boolean | 예측 비행경로 라인 |
| `setPredHorizon(s)` / `predHorizon` (get) | number | 예측 지평(2~20s) |
| `setVelArrow(on)` / `velArrow` (get) | boolean | 속도 벡터 화살표 |
| `setCpaMarker(on)` / `cpaMarker` (get) | boolean | CPA 충돌점 마커 |
| `cpaPairsCount` (get) | number | 현재 CPA 마커 쌍 수 |

### 1.8 Phase 3 — CIN 시네마틱

| 메서드 | 반환 | 설명 |
|---|---|---|
| `setSunCycle(on)` / `sunEnabled` (get) | boolean | 동적 태양 주기 |
| `setSunHour(h)` / `sunHour` (get) | number | 시간대(0~24) |
| `setSunAuto(on)` | boolean | 자동 시간 흐름 |
| `setRain(on, intensity)` | boolean | 비 입자(강도 0~1) |
| `setSnow(on, intensity)` | boolean | 눈 입자(강도 0~1) |
| `startRecording()` / `stopRecording()` | — | MediaRecorder 화면 녹화 |
| `recording` (get) | boolean | 녹화 중 여부 |

### 1.9 Phase 4 — CAM 카메라 모드

| 메서드 | 반환 | 설명 |
|---|---|---|
| `setCamMode(mode)` / `camMode` (get) | string | 카메라 모드(기본/탑다운/추적/오빗/FPV/측면) |
| `focusDrone(idOrIndex)` | id\|null | 특정 드론에 카메라 포커스 |

### 1.10 Phase 5 — MIS 임무 계획

| 메서드 | 반환 | 설명 |
|---|---|---|
| `missionAdd(droneId, waypoints, templateName)` | object | 드론에 웨이포인트 임무 주입 |
| `missionTemplate(name, originX, originZ)` | array | 템플릿 웨이포인트 생성(수색/정찰/배달 등) |
| `missionAssignTemplate(droneId, templateName)` | object\|null | 드론 위치 기준 템플릿 임무 할당 |
| `missionClearAll()` | number | 전체 임무 해제, 남은 수 반환 |
| `missions` (get) | array | `{ id, droneId, wpCount, currentIdx, completion, template }` |

### 1.11 Phase 6 — INJ 장애 주입

| 메서드 | 반환 | 설명 |
|---|---|---|
| `injectFault(droneId, type, opts)` | — | GPS 손실/모터 페일/통신 두절/배터리 급강하 |
| `injectRogue()` | — | ROGUE 침입 드론 스폰 |
| `injectDynamicNFZ(x, z, r, dur)` | — | 동적 비행금지구역 |
| `injectScenario(name)` | — | EMP/EMI 등 시나리오 일괄 |
| `injClearAll()` | — | 전체 장애 해제 |
| `injStats` (get) / `dynamicNfzList` (get) | object/array | 통계·동적 NFZ 목록 |

### 1.12 Phase 7 — ANA 분석 강화

| 메서드 | 반환 | 설명 |
|---|---|---|
| `setAnaHeatmap(on)` / `anaHeatmap` (get) | boolean | 누적 위협 히트맵 |
| `anaKpiWindow` (get) | object | `{ time, cr, avgBat, fps }` 슬라이딩 윈도우 |
| `exportLatexKpi()` | string | 논문 §Results용 LaTeX 표 출력 |

### 1.13 Phase 8 — AUD 환경 사운드

| 메서드 | 반환 | 설명 |
|---|---|---|
| `setAmbientAudio(on)` / `ambientAudio` (get) | boolean | 바람·우천 Web Audio 환경음 |

### 1.14 Phase 9 — MOB 모바일/PWA

| 메서드 | 반환 | 설명 |
|---|---|---|
| `isMobile` (get) | boolean | 모바일 환경 감지 |
| `mobileLOD` (get) | boolean | 자동 LOD 적용 여부 |
| `applyMobileLOD()` | boolean | 모바일 LOD 적용 |

---

## 2. `window._mds` — 해양 소형선 감지 시뮬레이터

### 2.1 상태 조회 (getter)

| 멤버 | 반환 | 설명 |
|---|---|---|
| `total` | number | 전체 선박 수 |
| `detected` | number | 레이더 탐지 수 |
| `identified` | number | 식별 수 |
| `accuracy` | number | 식별 정확도(%) |
| `cpaWarn` | number | CPA 경고 수 |
| `fused` | number | AIS 융합 트랙 수 (C2) |
| `encounters` | array | `{ id, type }` COLREG 조우 (C4) |
| `tracks` | string[] | 탐지된 트랙 id |
| `validation` | array | 시나리오별 검증 기록 (C9) |
| `horizonNM` | number | 평균 레이더 수평선(NM) (C1) |
| `selectedId` | string\|null | 선택 트랙 id |
| `titleText` | string | 현재 언어 제목(i18n 검증용) |

### 2.2 제어·선택

| 메서드 | 반환 | 설명 |
|---|---|---|
| `start()` / `stop()` | — | 시뮬레이션 시작/정지 |
| `scenario(n)` | — | 시나리오 선택·초기화 |
| `select(id)` / `deselect()` | id\|null | 트랙 선택/해제 (C5) |
| `lang(l)` | string | UI 언어 전환(B5 i18n) |

### 2.3 EO/IR (C3 · P735 어댑터)

| 메서드 | 반환 | 설명 |
|---|---|---|
| `eoirMode(m)` | 'EO'\|'IR' | EO/IR 모드 전환 |
| `eoirDataURL()` | string\|null | EO/IR 캔버스 PNG dataURL |
| `registerEOIRSource(name, handler)` | string[] | 외부 EO/IR SDK 어댑터 등록. `handler(ctx, w, h, info)`, `info = { eoMode, vessel, NM, distNM, speedKn, sourceLabel }` |
| `selectEOIRSource(name)` | — | 등록 소스 선택 |
| `eoirSource` (get) / `eoirSources` (get) | string/string[] | 현재 소스·등록 목록 |

### 2.4 리포트

| 메서드 | 반환 | 설명 |
|---|---|---|
| `reportDataURL()` | string | 리포트 PNG dataURL (C6) |
| `csvText()` | string | 트랙 CSV 텍스트 (C6, 테스트용) |

### 2.5 three.js 핸들

`camera` · `scene` · `renderer` — 고급 검사용 직접 핸들.

---

## 3. 사용 예시 (헤드리스 E2E)

```js
// 군집 시뮬레이터 — 시나리오 실행 + ATC 명령 + 검증
await page.evaluate(() => window._sdacs.selectScenario('high_density'));
await page.evaluate(() => window._sdacs.startSim());
await page.evaluate(() => window._sdacs.atcCommand(0, 'HOLD'));
const controlled = await page.evaluate(() => window._sdacs.atcControlled);

// 해양 시뮬레이터 — 시나리오 + 정확도 측정
await page.evaluate(() => window._mds.scenario(3));
await page.evaluate(() => window._mds.start());
const acc = await page.evaluate(() => window._mds.accuracy);
```

관련 스모크: `tests/e2e/smoke_sim.mjs` · `tests/e2e/smoke_maritime.mjs` ·
`tests/e2e/test_simulator_*.py` (Playwright)
