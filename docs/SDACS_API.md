# SDACS 3D 시뮬레이터 `_sdacs` API 레퍼런스

*Phase 10 (통합·문서) 산출물 — MEGA Ultra Plan 9 Phase 완료 후 전체 API 정리*

브라우저 단독 실행 시뮬레이터(`swarm_3d_simulator.html`)는 전역 객체
`window._sdacs`를 통해 외부 제어·관측 인터페이스를 노출합니다. Playwright
헤드리스 E2E 테스트(`tests/e2e/test_simulator_*.py`)와 LIVE 브릿지
(`simulation/ws_bridge.py`)가 이 API를 기준으로 동작하므로, 시그니처 변경 시
해당 테스트와 사본(`visualization/`·`docs/×2`)을 함께 갱신해야 합니다.

> 사본 동기화 규칙: `swarm_3d_simulator.html` → `visualization/swarm_3d_simulator.html`
> → `docs/swarm_3d_simulator.html` → `docs/simulator.html` (md5 일치 필수).

---

## 1. 시뮬레이션 상태 (read-only getter)

| 속성 | 반환 | 설명 |
|---|---|---|
| `stats` | object | 누적 통계 스냅샷(복사본) |
| `simTime` | number | 시뮬레이션 경과 시간(초) |
| `simRunning` | boolean | 실행 중 여부 |
| `droneCount` | number | 전체 드론 수 |
| `airborne` | number | 비행 중(GROUNDED·FAILED 제외) |
| `failed` | number | FAILED 상태 드론 수 |
| `landed` | number | GROUNDED 상태 드론 수 |
| `weather` | object | 결빙·마이크로버스트·스톰셀·태풍·난류·풍속 |
| `perf` | object | fps·cpuMs·gpuMs·drawCalls·triangles·drones·megaMode·visibleInstances (B6) |
| `megaMode` | boolean | 대규모(≥500) 모드 여부 |
| `instanceCount` | number | InstancedMesh 인스턴스 수 |
| `visibleInstances` | number | 컬링 후 가시 인스턴스 수 |
| `conflictPairs` | number | 현재 충돌 라인 페어 수 |

## 2. 시뮬레이션 제어

| 메서드 | 설명 |
|---|---|
| `startSim()` | 시뮬레이션 시작 |
| `stopSim()` | 시뮬레이션 정지 |
| `selectScenario(name)` | 시나리오 드롭다운 선택 + change 이벤트 디스패치 |

## 3. 드론 선택·호버 (B4 다중 선택)

| 메서드 / 속성 | 반환 | 설명 |
|---|---|---|
| `selectDrone(idOrIndex)` | id\|null | 단일 선택 |
| `deselectDrone()` | — | 선택 해제 |
| `getSelected()` | object\|null | 선택 드론 스냅샷(THREE 핸들 제외) |
| `multiSelect(ids)` | number | 다중 선택, 선택 수 반환 |
| `clearMulti()` | — | 다중 선택 해제 |
| `multiSelection` | id[] | 현재 다중 선택 id 목록 |
| `hoverDrone(idOrIndex)` | id\|null | 호버 강조 |
| `clearHover()` | — | 호버 해제 |

## 4. 분석 뷰 · 리포트

| 메서드 / 속성 | 설명 |
|---|---|
| `setAnalysisView(on)` | 2×2 분석 뷰 토글 |
| `analysisMode` | 분석 뷰 활성 여부 |
| `reportDataURL()` | async, 리포트 캔버스 PNG dataURL |
| `exportPNG / exportCSV / exportHTML / exportMD` | 각 포맷 리포트 내보내기 |
| `captureScreenshot()` | 현재 씬 렌더 후 PNG dataURL |

## 5. 국제화 · LIVE 브릿지

| 메서드 / 속성 | 설명 |
|---|---|
| `lang` / `setLang(lang)` | 현재 언어 / KO·EN 전환 |
| `wsConnected` | WebSocket 연결 여부 |
| `wsFrames` | 수신 프레임 수 |
| `liveMode` | LIVE 데이터 적용 중 여부 |
| `goLive` | LIVE 모드 전환 함수 |

## 6. 리플레이 (P734 스크러버 호환)

| 메서드 / 속성 | 설명 |
|---|---|
| `replay` | {mode, playing, speed, idx, totalFrames, t} 스냅샷 |
| `replayFrames` | 레코딩된 프레임 수 |
| `replaySeek(idx)` | 인덱스로 점프 |
| `replayStep(delta=1)` | 상대 프레임 이동(←/→ 키 호환) |

## 7. Phase 1 — ATC 관제 콘솔

| 메서드 / 속성 | 설명 |
|---|---|
| `atcCommand(did, cmd, params, source)` | 관제 명령 발행 |
| `atcLog` | 관제 로그 배열(복사본) |
| `atcControlled` | 현재 ATC 제어 중 드론 [{id, cmd, lockUntil}] |
| `clearAllAtc()` | 전체 CLEAR, 해제된 드론 수 반환 |
| `setAtcAudio(on)` / `atcAudio` | TTS 음성 토글 / 상태 |

**지원 `cmd` 값:** `HOLD`, `RESUME`/`CLEAR`, `ALT`(고도), `SPD`(속도), `TURN`,
`REROUTE`, `RTB`/`RTL`(복귀), `TAKEOFF`, `LANDING`.

## 8. Phase 2 — TAC 전술 시각화

| 메서드 / 속성 | 설명 |
|---|---|
| `setPredTrail(on)` / `predTrail` | 예측 비행경로 라인(8초) 토글 |
| `setPredHorizon(s)` / `predHorizon` | 예측 지평(2~20초) |
| `setVelArrow(on)` / `velArrow` | 속도 벡터 화살표 토글 |
| `setCpaMarker(on)` / `cpaMarker` | CPA 충돌점 마커 토글 |
| `cpaPairsCount` | 현재 CPA 마커 페어 수 |

> LOD 정책: 드론 수에 따라 step·frame 간격 자동 조절, megaMode(≥500) 강제 OFF.

## 9. Phase 3 — CIN 시네마틱

| 메서드 / 속성 | 설명 |
|---|---|
| `setSunCycle(on)` / `sunEnabled` | 동적 태양 사이클 토글 |
| `setSunHour(h)` / `sunHour` | 시각(0~24) 설정 |
| `setSunAuto(on)` | 시각 자동 진행 |
| `setRain(on, intensity)` | 강우 입자 (강도 0~1) |
| `setSnow(on, intensity)` | 강설 입자 (강도 0~1) |
| `startRecording()` / `stopRecording()` / `recording` | MediaRecorder 화면 녹화 |

## 10. Phase 4 — CAM 카메라 모드

| 메서드 / 속성 | 설명 |
|---|---|
| `setCamMode(mode)` / `camMode` | 카메라 모드 전환 |
| `focusDrone(idOrIndex)` | 지정 드론으로 카메라 포커스 |

**지원 `mode` 값:** `orbit`(자동 회전), `reset`, `top`, `side`, `follow`,
`fpv`(1인칭), `chase`(추격). `fpv`/`chase`는 드론 선택 필요.

## 11. Phase 5 — MIS 임무 계획

| 메서드 / 속성 | 설명 |
|---|---|
| `missionAdd(droneId, waypoints, templateName)` | 웨이포인트 임무 직접 할당 |
| `missionTemplate(name, originX, originZ)` | 템플릿 웨이포인트 생성 |
| `missionAssignTemplate(droneId, templateName)` | 드론 위치 기준 템플릿 할당 |
| `missionClearAll()` | 전체 임무 제거 |
| `missions` | 활성 임무 목록 [{id, droneId, wpCount, currentIdx, completion, template}] |

**템플릿 이름:** `search_grid`(4×4 격자), `recon_orbit`(원형 8점), `delivery`(직선),
`spray_voronoi`(지그재그 8점), `medical_heap`(우선순위 5점).

## 12. Phase 6 — INJ 장애 주입

| 메서드 / 속성 | 설명 |
|---|---|
| `injectFault(droneId, type, opts)` | 단일 드론 장애 주입 |
| `injectRogue()` | Rogue 드론 스폰 |
| `injectDynamicNFZ(x, z, r, dur)` | 동적 비행금지구역 생성 |
| `injectScenario(name)` | 광역 시나리오 주입 |
| `injClearAll()` | 전체 장애 해제 |
| `injStats` | 장애 통계 스냅샷 |
| `dynamicNfzList` | 동적 NFZ 목록 |

**`type` 값:** `GPS_LOSS`, `MOTOR_FAIL`, `BATTERY_DRAIN`, `COMMS_LOSS`.
**`injectScenario` name:** `EMP`(30% GPS 손실), `EMI`(50% 통신 두절),
`BAT_LIMIT`(저배터리 급강하).

## 13. Phase 7 — ANA 분석 강화

| 메서드 / 속성 | 설명 |
|---|---|
| `setAnaHeatmap(on)` / `anaHeatmap` | 누적 히트맵 토글 |
| `anaKpiWindow` | 실시간 KPI 윈도우 {time, cr, avgBat, fps} |
| `exportLatexKpi()` | LaTeX KPI 표 문자열 생성 |

## 14. Phase 8 — AUD 환경 사운드

| 메서드 / 속성 | 설명 |
|---|---|
| `setAmbientAudio(on)` / `ambientAudio` | 환경음(풍속·우천·천둥) 토글 |

## 15. Phase 9 — MOB 모바일 / PWA

| 메서드 / 속성 | 설명 |
|---|---|
| `isMobile` | 모바일 디바이스 감지 여부 |
| `mobileLOD` | 자동 LOD 적용 상태 |
| `applyMobileLOD()` | 모바일 LOD 적용 |

## 16. 공역 레이어 (O1 통합)

| 메서드 / 속성 | 설명 |
|---|---|
| `setLayer(name, on)` | 레이어 가시성 설정(tg-* 체크박스 자동 동기화) |
| `layers` | 전체 레이어 가시성 맵 |
| `dni` | 탐지·식별 통계 {…, objects} |

## 17. THREE.js 핸들 (고급)

`camera`, `renderer`, `scene`, `controls` — Playwright·스크립트에서 직접 렌더·
스크린샷 캡처에 사용. 일반 사용 시 직접 조작 비권장.

---

## E2E 테스트 매핑

| Phase | 테스트 파일 |
|---|---|
| ATC | `tests/e2e/test_simulator_atc.py` |
| TAC | `tests/e2e/test_simulator_tac.py` |
| CIN·INJ | `tests/e2e/test_simulator_cin_inj.py` |
| CAM·AUD | `tests/e2e/test_simulator_cam_aud.py` |
| MIS·ANA·MOB | `tests/e2e/test_simulator_mis_ana_mob.py` |

헤드리스 스모크: `tests/e2e/smoke_sim.mjs`, `smoke_maritime.mjs` (CI: `.github/workflows/sim-smoke.yml`).
