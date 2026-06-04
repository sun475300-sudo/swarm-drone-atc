# SDACS 시뮬레이터 외부 API 레퍼런스

*MEGA 플랜 Phase 10 산출물 — `_sdacs`(메인 3D)·`_mds`(해양 탐지) 헤드리스 제어 API 전수 문서화*

본 문서는 브라우저 `window` 전역에 노출되는 두 시뮬레이터 제어 API를 정리합니다.
Playwright E2E 테스트(`tests/e2e/`)와 외부 자동화·데모 스크립트가 이 표면을 통해 시뮬레이터를 구동합니다.

- **`window._sdacs`** — `swarm_3d_simulator.html` (군집 3D 시뮬레이터, Phase 1~9 전 기능)
- **`window._mds`** — `maritime_detection_simulator.html` (소형 선박 탐지·식별)

> 규약: getter는 값을 읽고, 메서드는 상태를 바꾼 뒤 갱신된 값을 반환합니다.
> 드론/선박은 대부분 `id`(문자열) 또는 배열 인덱스(숫자) 어느 쪽으로도 지정할 수 있습니다.

---

## 1. `_sdacs` — 군집 3D 시뮬레이터

### 1.1 상태 조회 (getter)

| 속성 | 반환 | 설명 |
|---|---|---|
| `stats` | object | 누적 통계 스냅샷(충돌·충돌회피 등) 복사본 |
| `simTime` | number | 시뮬레이션 경과 시간(초) |
| `simRunning` | boolean | 실행 중 여부 |
| `droneCount` | number | 전체 드론 수 |
| `weather` | object | `{ icing, microbursts, stormCells, typhoonWind, turbulence, windSpd }` |
| `airborne` | number | 비행 중 드론 수(GROUNDED·FAILED 제외) |
| `failed` | number | FAILED 상태 드론 수 |
| `landed` | number | GROUNDED 상태 드론 수 |
| `megaMode` | boolean | 대규모(≥500기) 모드 여부 |
| `instanceCount` | number | InstancedMesh 인스턴스 수 |
| `visibleInstances` | number | 현재 컬링 후 가시 인스턴스 수 |
| `lang` | string | 현재 언어(`ko`/`en`) |
| `perf` | object | `{ fps, cpuMs, gpuMs, drawCalls, triangles, drones, megaMode, visibleInstances }` |
| `replayFrames` | number | 레코더에 저장된 프레임 수 |
| `dni` | object | 외부 동적 객체(DNI) 통계 + `objects` 수 |
| `wsConnected` / `wsFrames` / `liveMode` | boolean/number | WebSocket LIVE 상태 |
| `multiSelection` | string[] | 다중 선택된 드론 id 배열 |
| `analysisMode` | boolean | 4-뷰 분석 모드 여부 |
| `megaCull` | boolean | 대규모 컬링 on/off (set 가능) |
| `layers` | object | 레이어 가시성 맵 복사본 |
| `conflictPairs` | number | 현재 충돌 경고 라인 쌍 수 |

### 1.2 시뮬레이션 제어

| 메서드 | 반환 | 설명 |
|---|---|---|
| `startSim()` / `stopSim()` | — | 실행/정지 |
| `selectScenario(name)` | — | 시나리오 드롭다운 선택 + change 이벤트 발행 |
| `setLang(lang)` | string | 언어 전환 |
| `setLayer(name, on)` | boolean\|null | 레이어 가시성 설정(미존재 키는 null) |
| `goLive()` | — | WebSocket LIVE 모드 진입 |

### 1.3 드론 선택·호버

| 메서드 | 반환 | 설명 |
|---|---|---|
| `selectDrone(idOrIndex)` | id\|null | 단일 선택 |
| `deselectDrone()` | — | 선택 해제 |
| `getSelected()` | object\|null | 선택 드론 스냅샷(THREE 객체 제외) |
| `multiSelect(ids)` | number | 다중 선택, 선택 수 반환 |
| `clearMulti()` | — | 다중 선택 해제 |
| `hoverDrone(idOrIndex)` | id\|null | 호버 설정 |
| `clearHover()` | — | 호버 해제 |

### 1.4 리포트·내보내기

| 메서드 | 반환 | 설명 |
|---|---|---|
| `exportPNG` / `exportCSV` / `exportHTML` / `exportMD` | — | 각 포맷 다운로드 |
| `reportDataURL()` | Promise\<string\> | 리포트 캔버스 PNG dataURL |
| `captureScreenshot()` | string | 현재 렌더 프레임 PNG dataURL |

### 1.5 리플레이 (P734)

| 멤버 | 반환 | 설명 |
|---|---|---|
| `replay` | object | `{ mode, playing, speed, idx, totalFrames, t }` |
| `replaySeek(idx)` | number | 지정 프레임으로 이동(리플레이 진입) |
| `replayStep(delta=1)` | number\|null | 상대 이동(키보드 ←/→ 호환) |

### 1.6 Phase 1 — ATC 관제

| 멤버 | 반환 | 설명 |
|---|---|---|
| `atcCommand(did, cmd, params, source)` | 결과 | 관제 명령(HOLD/RTB/REROUTE/ALT±/SPD±/TURN/CLEAR) |
| `atcLog` | array | 관제 감사 로그 복사본 |
| `atcControlled` | array | 현재 명령 적용 드론 `{ id, cmd, lockUntil }` |
| `clearAllAtc()` | number | 전 드론 CLEAR, 해제 수 반환 |
| `setAtcAudio(on)` / `atcAudio` | boolean | TTS/비프 음성 토글·상태 |

### 1.7 Phase 2 — TAC 전술 시각화

| 멤버 | 반환 | 설명 |
|---|---|---|
| `setPredTrail(on)` / `predTrail` | boolean | 예측 비행경로 라인 |
| `setPredHorizon(s)` / `predHorizon` | number | 예측 수평선(2~20초) |
| `setVelArrow(on)` / `velArrow` | boolean | 속도 벡터 화살표 |
| `setCpaMarker(on)` / `cpaMarker` | boolean | CPA 충돌점 마커 |
| `cpaPairsCount` | number | 현재 CPA 마커 쌍 수 |

### 1.8 Phase 3 — CIN 시네마틱

| 멤버 | 반환 | 설명 |
|---|---|---|
| `setSunCycle(on)` / `sunEnabled` | boolean | 동적 태양 24h |
| `setSunHour(h)` / `sunHour` | number | 시각 설정(0~24) |
| `setSunAuto(on)` | boolean | 자동 시간 흐름 |
| `setRain(on, intensity)` | boolean | 비 입자(강도 0~1) |
| `setSnow(on, intensity)` | boolean | 눈 입자(강도 0~1) |
| `startRecording()` / `stopRecording()` / `recording` | — / boolean | MediaRecorder 화면 녹화 |

### 1.9 Phase 4 — CAM 카메라 모드

| 멤버 | 반환 | 설명 |
|---|---|---|
| `setCamMode(mode)` / `camMode` | string | FPV/추격/측면/탑/프리 등 모드 전환 |
| `focusDrone(idOrIndex)` | id\|null | 카메라 포커스 대상 지정 |

### 1.10 Phase 5 — MIS 임무 계획

| 멤버 | 반환 | 설명 |
|---|---|---|
| `missionAdd(droneId, waypoints, templateName)` | 결과 | 웨이포인트 임무 추가 |
| `missionTemplate(name, originX, originZ)` | waypoints | 템플릿 웨이포인트 생성(수색·정찰·배달·방제·의료) |
| `missionAssignTemplate(droneId, templateName)` | 결과\|null | 드론 위치 기준 템플릿 할당 |
| `missionClearAll()` | number | 전체 임무 제거, 잔여 수 반환 |
| `missions` | array | `{ id, droneId, wpCount, currentIdx, completion, template }` |

### 1.11 Phase 6 — INJ 장애 주입

| 멤버 | 반환 | 설명 |
|---|---|---|
| `injectFault(droneId, type, opts)` | 결과 | GPS손실/모터페일/통신두절/배터리급강하 |
| `injectRogue()` | 결과 | ROGUE 드론 스폰 |
| `injectDynamicNFZ(x, z, r, dur)` | 결과 | 동적 비행금지구역 |
| `injectScenario(name)` | 결과 | EMP/EMI 등 시나리오 일괄 |
| `injClearAll()` | 결과 | 전체 해제 |
| `injStats` | object | 장애 통계 카운터 |
| `dynamicNfzList` | array | 활성 동적 NFZ 목록 |

### 1.12 Phase 7 — ANA 분석 강화

| 멤버 | 반환 | 설명 |
|---|---|---|
| `setAnaHeatmap(on)` / `anaHeatmap` | boolean | 누적 위협 히트맵 |
| `anaKpiWindow` | object | `{ time, cr, avgBat, fps }` 슬라이딩 윈도우 |
| `exportLatexKpi()` | string | 논문용 LaTeX KPI 표 출력 |

### 1.13 Phase 8 — AUD 환경 사운드

| 멤버 | 반환 | 설명 |
|---|---|---|
| `setAmbientAudio(on)` / `ambientAudio` | boolean | 바람/우천/배터리 알람 Web Audio |

### 1.14 Phase 9 — MOB 모바일/PWA

| 멤버 | 반환 | 설명 |
|---|---|---|
| `isMobile` | boolean | 모바일 디바이스 감지 |
| `mobileLOD` | boolean | 자동 LOD 활성 여부 |
| `applyMobileLOD()` | boolean | 모바일 LOD 강제 적용 |

### 1.15 THREE.js 핸들

직접 렌더링 제어가 필요한 경우 다음 객체가 노출됩니다: `camera`, `renderer`, `scene`, `controls`.

---

## 2. `_mds` — 해양 탐지 시뮬레이터

### 2.1 상태 조회 (getter)

| 속성 | 반환 | 설명 |
|---|---|---|
| `total` | number | 전체 선박 수 |
| `detected` | number | 탐지된 선박 수 |
| `identified` | number | 식별된 선박 수 |
| `accuracy` | number | 식별 정확도(%) |
| `cpaWarn` | number | CPA 경고 수 |
| `fused` | number | 융합 트랙 수 (C2) |
| `encounters` | array | 조우 유형 `{ id, type }` (C4) |
| `tracks` | string[] | 탐지 트랙 id |
| `validation` | array | 시나리오별 검증 기록 (C9) |
| `horizonNM` | number | 평균 레이더 수평선(NM) (C1) |
| `selectedId` | string\|null | 선택 선박 id |
| `eoirSource` / `eoirSources` | string / string[] | 현재·등록 EO/IR 소스 |

### 2.2 제어·내보내기

| 메서드 | 반환 | 설명 |
|---|---|---|
| `start()` / `stop()` | — | 실행/정지 |
| `scenario(n)` | — | 시나리오 선택·초기화 |
| `select(id)` / `deselect()` | id\|null / — | 선박 선택/해제 (C5) |
| `lang(l)` | string | i18n 언어 전환 (B5) |
| `eoirMode(m)` | string | EO/IR 모드 전환 (C3) |
| `eoirDataURL()` | string\|null | EO/IR 캔버스 PNG dataURL (C3) |
| `registerEOIRSource(name, handler)` | string[] | EO/IR 소스 어댑터 등록 (P735) |
| `selectEOIRSource(name)` | 결과 | 등록 소스 선택 (P735) |
| `reportDataURL()` | string | 리포트 PNG dataURL (C6) |
| `csvText()` | string | CSV 텍스트(테스트용) (C6) |

---

## 3. E2E 검증 매트릭스

| Phase | E2E 파일 | 케이스 |
|---|---|---|
| 스모크 | `tests/e2e/smoke_sim.mjs` · `smoke_maritime.mjs` | 기동·핵심 API |
| 1 ATC | `tests/e2e/test_simulator_atc.py` | 10 |
| 2 TAC | `tests/e2e/test_simulator_tac.py` | 9 |
| 3·6 CIN/INJ | `tests/e2e/test_simulator_cin_inj.py` | 17 |
| 4·8 CAM/AUD | `tests/e2e/test_simulator_cam_aud.py` | 10 |
| 5·7·9 MIS/ANA/MOB | `tests/e2e/test_simulator_mis_ana_mob.py` | 15 |

CI 통합: `.github/workflows/sim-smoke.yml` (Playwright + Chromium 헤드리스).

---

## 4. 사용 예시

```js
// 헤드리스 시나리오 구동 + KPI 수집
_sdacs.selectScenario('high_density');
_sdacs.startSim();
// ... 일정 시간 경과 후
const kpi = _sdacs.perf;            // { fps, cpuMs, ... }
const latex = _sdacs.exportLatexKpi(); // 논문 §Results 삽입용 표

// 장애 주입 → 5계층 안전망 응답 관찰
_sdacs.injectFault('D-001', 'gps_loss');
console.log(_sdacs.injStats);

// 전술 시각화 토글
_sdacs.setPredTrail(true);
_sdacs.setCpaMarker(true);
```
