# 🎮 SDACS 시뮬레이터 Ultra Plan v3 — 기능 업그레이드 로드맵

*Created: 2026-06-04 — 본 세션 PR 15개 main 머지 후 추가 업그레이드 단계*

현재 시뮬레이터(`swarm_3d_simulator.html` 7,070 lines + `maritime_detection_simulator.html` 1,037 lines)에 들어갈 신규 기능을 우선순위 + 트랙별로 정리. 본 문서는 **사용자 요청 "시뮬레이터를 더 업그레이드"** 에 대한 실행 계획.

## 0. 현재 보유 기능 (참고)

이미 구현된 것 (작업 중복 방지):
- InstancedMesh 메가 군집 (500/1K/5K/10K) + 프러스텀 컬링
- CPA 충돌 예측선 + 어드바이저리 빌보드
- 4-View 분석 모드(3D · 평면도 · 충돌 히트맵 · 차트)
- 리플레이 타임라인 스크러버 (←/→/Home/End/L)
- WebSocket LIVE 브리지 (ws_bridge.py 연동)
- 정밀 기상 (마이크로버스트·스톰셀·결빙·돌풍)
- PNG/CSV/HTML/MD 리포트 내보내기
- 다중 선택 (Shift+클릭) + 집계 패널
- 22종 직군 + 63 시나리오

## 1. 트랙 분류 + 우선순위

| 트랙 | 영역 | 우선순위 | 본 세션 진행 |
|---|---|---|---|
| **ATC** | 관제사 콘솔·명령·음성 | **P0** ⭐ | ✅ Phase 1부터 시작 |
| TAC | 전술 시각화 (예측경로·CPA 마커) | P1 | 후속 |
| CIN | 시네마틱 (조명·포스트·녹화) | P2 | 후속 |
| CAM | 카메라 모드 (FPV·follow·PiP) | P2 | 후속 |
| MIS | 임무 계획 UI (웨이포인트) | P3 | 후속 |
| INJ | 장애 주입 콘솔 | P3 | 후속 |
| ANA | 분석 강화 (누적 히트맵·비교) | P3 | 후속 |
| AUD | 음성·사운드 | P2 | ATC와 묶음 |
| MOB | 모바일·터치 | P4 | 후속 |

---

## 2. Track ATC — 관제사 콘솔 (P0)

### Phase 1A — ATC 명령 패널 (즉시 시작)
드론 선택 시 상세 패널에 명령 버튼 그리드 추가:
- `[HOLD]` — 현재 위치 호버 (phase=HOLDING)
- `[RTB]` — 출발 패드로 귀환 (phase=RTL)
- `[ALT+]` `[ALT-]` — 목표고도 ±10m
- `[SPD+]` `[SPD-]` — 최대속도 ±20%
- `[L]` `[R]` — 즉시 좌/우 30° 헤딩 변경
- `[REROUTE]` — 다른 가용 패드로 목표 변경
- `[CLEAR]` — 모든 ATC 오버라이드 해제 + 자율로 복귀

`d.atc = { cmd, ts, lockUntil, params }` 데이터 모델, 비행 phase 루프에서 우선순위 적용.

### Phase 1B — 명령 로그 + 감사 (즉시 시작)
- 좌측 하단 명령 로그 패널 (마지막 20개 ATC 명령)
- 형식: `[01:23] 드론7 HOLD (관제사)`
- CSV 내보내기에 atc_commands 시트 추가
- 감사용 timestamp + 명령자(`controller`/`auto`) 기록

### Phase 1C — 시각 큐 (즉시 시작)
- ATC-제어 중인 드론은 **시안색 발광 링** (자율 드론과 구분)
- 헤더 상단 `🎮 ATC 모드: 3 드론 수동 제어 중` 카운터
- `atc-controlled` CSS 클래스 + 펄스 애니메이션

### Phase 1D — 음성 어드바이저리 (한국어 TTS) (다음)
- Web Speech API `speechSynthesis` 한국어 음성
- 충돌 임박 시 자동 발화: "드론 7번, 즉시 좌선회"
- ATC 명령 발행 시 발화: "드론 7번, 호버 명령"
- 토글 버튼 (음소거 / 음량 / 속도)

### Phase 1E — 사운드 효과 (다음)
- 충돌 경보 비프 (Web Audio API 합성)
- 근접경고 띵 (NEAR_MISS)
- 어드바이저리 차임
- 배터리 임계 알람 (배터리 < 15%)

---

## 3. Track TAC — 전술 시각화 (P1, 다음)

- 예측 비행경로 라인 (5~10초 궤적, 곡선 보간)
- CPA 충돌점 마커 + TTC 라벨 + 위험도 색상 (gradient)
- 속도 벡터 화살표 (heading × magnitude)
- 분리 표준 거품 (separation bubble, 와이어프레임 구체)
- 우선순위 표시 (드론 위 별★/■/▲)
- 회피 의도선 (planned APF vector)
- 관제 명령 의도 미리보기 (HOLD/RTB 클릭 전 호버 시 미리보기)

---

## 4. Track CIN — 시네마틱 (P2)

- 동적 태양 (시간대 슬라이더 0-24시) + 그림자 캐스팅
- 안개·비·눈 입자 (THREE.Points)
- UnrealBloomPass + SMAA + SSAO 포스트프로세싱 토글
- 영상 녹화 (MediaRecorder API → WebM 다운로드)
- 시네마틱 카메라 프리셋 (오프닝 dolly-in, 충돌순간 줌, 종료 wide)
- 색감 LUT (필름 / 야간투시 / 열영상)

---

## 5. Track CAM — 카메라 모드 (P2)

- 1인칭 onboard FPV (드론 카메라 시점 + HUD 오버레이)
- 추적 카메라 (드론 follow, 부드러운 spring 보간)
- 톱다운 / 사이드 / 자유시점 빠른 전환 (1/2/3/4 단축키)
- 다중 카메라 PiP (메인 + 4개 작은 뷰)
- 동시 다중 드론 비교 (분할 화면)

---

## 6. Track MIS — 임무 계획 UI (P3)

- 맵 클릭 → 웨이포인트 추가 (Shift+클릭 = 다중)
- 드론에 임무 할당 (드래그앤드롭 또는 우클릭 메뉴)
- 실시간 임무 재계획 (running drone에 새 목표 푸시)
- 자동 우회경로 미리보기 (A* / RRT)
- 임무 템플릿 (수색·정찰·배달·방제)

---

## 7. Track INJ — 장애 주입 콘솔 (P3)

- GPS 손실 (위치 노이즈 ±20m)
- 모터 페일 (속도 50% 감소)
- 배터리 급강하 (5%/s 소모)
- 통신 두절 (ATC 명령 무시)
- 로그 손상 (텔레메트리 dropout)
- Rogue 드론 즉시 발생
- 동적 NFZ 생성/소멸
- 일괄 시나리오 (e.g., "도시 EMP")

---

## 8. Track ANA — 분석 강화 (P3)

- 누적 충돌 히트맵 (세션 전체, decay 옵션)
- 실시간 KPI 오버레이 그래프 (좌측 작은 패널, FPS 무관)
- 시나리오 A·B 사이드바이사이드 (분할 화면 + KPI 비교 표)
- LaTeX 표 자동 생성 (논문용 \\begin{table}...)
- 충돌 책임 분석 (CPA 시점 누가 회피했어야 하는지 색상)
- 드론별 텔레메트리 CSV (각 드론마다 10Hz 샘플 라인)

---

## 9. Track AUD — 음성·사운드 (P2, ATC와 함께)

(위 Phase 1D/1E 참조)

---

## 10. Track MOB — 모바일·터치 (P4)

- 터치 제스처 (pinch zoom · pan · double-tap select)
- 반응형 UI (1024px↓ 자동 패널 접기)
- 모바일 자동 LOD (FPS < 30 시 인스턴스 50% 감소)
- viewport meta + safe-area-inset
- Apple Pencil / S-Pen hover 지원

---

## 11. 실행 순서 + 본 세션 진행

| 단계 | 작업 | 상태 |
|---|---|---|
| 1 | Ultra Plan v3 문서 작성 | ✅ |
| 2 | ATC 명령 데이터 모델 (`d.atc`) 추가 | ▶ 진행 |
| 3 | 상세 패널에 명령 버튼 그리드 추가 | ▶ 진행 |
| 4 | phase 루프에서 ATC 오버라이드 적용 | ▶ 진행 |
| 5 | 명령 로그 패널 + 시안색 발광 링 | ▶ 진행 |
| 6 | Web Speech API 한국어 TTS | 다음 |
| 7 | Web Audio API 비프/차임 | 다음 |
| 8 | `visualization/`·`docs/` 사본 동기화 | ▶ 진행 |
| 9 | 커밋 + main 푸시 | ▶ 진행 |

후속: Track TAC (예측경로) → CIN (시네마틱) → CAM (카메라) → MIS / INJ / ANA / MOB.

---

## 12. 검증

- Playwright 헤드리스 스모크 (`_sdacs.atcCommand('drone7', 'HOLD')` API)
- 50대 / 200대 / 1000대 시나리오에서 ATC 명령 응답성 확인
- 명령 발행→3D 시각 큐(시안 링) 한 프레임 내 반영
- CSV 내보내기에 atc_commands 시트 존재 확인
- 회귀: 기존 자율 시나리오(50대 기본) 성공률·통계 변화 없음

---

## 13. 외부 의존성

- Web Speech API (Phase 1D) — Chrome/Edge 한국어 기본 보이스 사용
- Web Audio API (Phase 1E) — 외부 음원 없이 합성
- MediaRecorder API (Track CIN 녹화) — Chromium 계열 표준
- 추가 npm 패키지 없음 (vanilla Three.js + 브라우저 표준만)

---

**참고 문서:**
- [`STATUS_REPORT.md`](../STATUS_REPORT.md) — 본 세션 PR 15개 머지 현황
- [`docs/ULTRA_PLAN.md`](ULTRA_PLAN.md) — 잔여 5항목 실행 플레이북
- [`ROADMAP.md`](../ROADMAP.md) — Phase 691-755 진행 현황
