# 🌌 SDACS HYPER Plan — Phase 10-50 초대규모 로드맵

*Created: 2026-06-04 — MEGA 9 Phase 완료 + 데스크탑 v1.1 빌드 직후*

본 문서는 [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md)의 9 Phase **완료 이후** 1-2년에 걸친 **초대규모 확장 로드맵**입니다.
- Phase 1-9: 본 세션 완료 ✅
- Phase 10-15: 즉시 실행 가능 (본 세션·후속 세션)
- Phase 16-30: 단기 (2026 Q3-Q4)
- Phase 31-45: 중기 (2027 H1)
- Phase 46-50: 장기 (2027 H2+)

## 📊 누적 측정 — 본 세션 완료 시점

| 지표 | 값 |
|---|---|
| 시뮬레이터 코드 (군집) | 8,756 line |
| 시뮬레이터 코드 (해양) | 1,037 line |
| `_sdacs` API 항목 | 230+ |
| `_mds` API 항목 | 46 |
| Playwright E2E | 67/68 통과 |
| 회귀 pytest | 4,140/4,140 |
| 데스크탑 빌드 | v1.1.0 Linux AppImage 105MB ✅ |
| 사본 동기화 | 4개 + maritime visualization 추가 |
| 누락 기능 | 28 → 0 (MEGA) → 50+ 신규 (HYPER) |

---

## 🚀 Phase 10-15 — 단기 즉시 실행 (본 세션·후속 1주)

### Phase 10 — 통합·문서·CI 마무리
- [x] sim-smoke.yml 3-job 강화
- [x] RELEASE_GUIDE.md 작성
- [x] visualization/maritime 사본 동기화
- [ ] `_sdacs` 전체 API 자동 문서화 (`docs/SDACS_API.md`)
- [ ] 데모 영상 30초 (Phase 1-9 하이라이트) — MediaRecorder 활용

### Phase 11 — 해양 시뮬레이터 ATC 동등 이식
- HOLD/RETURN/REROUTE 함선 명령 패널
- 한국어 TTS (해상 어드바이저리: "어선 7번, 변침 좌현 20도")
- 함정 우선순위 시각화
- COLREG 위반 자동 경보
- `_mds.atcCommand` API

### Phase 12 — 데스크탑 멀티 윈도우 + 라이브 동기화
- Electron BrowserView 2개 (군집 + 해양 동시)
- IPC 통신으로 시간축 동기 (sim time broadcast)
- 다중 모니터 자동 분산
- 메뉴: "View → Tile Horizontally / Vertically"

### Phase 13 — WebGPU Compute Shader 확장
- 현재 APF force compute → CPA prediction까지 GPU
- Spatial hash 격자 인덱스 GPU 빌드
- 50,000대 시나리오 대비 (현재 10K)
- Compute timing HUD 분리 (APF / CPA / Spatial)

### Phase 14 — Storybook 식 시나리오 갤러리
- 66개 시나리오 카드 그리드 UI
- 각 시나리오 짧은 GIF 미리보기 (자동 녹화)
- "Featured" / "Stress" / "Weather" / "Military" / "UAM" 카테고리
- 클릭 → 즉시 로드

### Phase 15 — 다국어 확장 (KO/EN/JA/ZH)
- 현재 KO/EN → 일본어·중국어 추가
- 모든 메뉴·툴팁·이벤트 로그 i18n
- 음성 TTS 언어 자동 매칭
- 시나리오 이름 다국어

---

## 🌐 Phase 16-30 — 단기 (2026 Q3-Q4)

### Phase 16 — Real-Time Collaboration (CRDT)
- Yjs 또는 Automerge 도입
- 다중 관제사가 동일 시뮬 동시 조작
- ATC 명령 conflict resolution (CRDT 자동 머지)
- Cursor·selection·hover 상태 공유

### Phase 17 — VR 헤드셋 지원 (WebXR)
- Three.js WebXR Manager 활성
- Meta Quest / Vision Pro 지원
- 컨트롤러로 드론 선택·명령
- 6DoF 카메라 (관제사가 공역 안에서 직접 보기)

### Phase 18 — AR Overlay (사상자 식별)
- WebXR AR mode
- 실제 카메라 피드 위 가상 드론 오버레이
- 위치 핀 GPS 정합 (시뮬-실제)
- 모바일 카메라 사용

### Phase 19 — Mission Recorder + Playback Sharing
- 임무 시작→완료 전체 캡처 (.sdacs-mission 포맷)
- 클라우드 업로드 → 공유 URL
- 다른 사용자가 동일 임무 재생·분기 실행

### Phase 20 — AI Copilot (Claude API hook)
- 자연어 명령: "북서쪽 5번 드론을 회항시키고 12·13번 분리거리 확보"
- Claude Tool Use로 ATC 명령 분해
- 시뮬 컨텍스트 자동 주입 (현재 상태·KPI·드론 목록)
- 답변 자막 + 음성 TTS

### Phase 21 — Adversarial Drone (RL Bot)
- 학습된 PPO agent를 적대적 드론으로 투입
- 5계층 안전망 robustness 시연
- 다양한 공격 정책 (decoy·swarm coordination·jamming)

### Phase 22 — Digital Twin Pixhawk
- 실 Pixhawk 6X + Jetson MAVLink 입력
- 시뮬 내 가상 드론과 실드론 동시 표시
- HITL 검증 데이터셋 자동 캡처

### Phase 23 — High-Fidelity Wind Field
- HRRR 또는 KMA 1km grid wind 데이터 import
- 시간대별 실 풍속·풍향
- 시뮬 내 직접 적용

### Phase 24 — 도시별 실시간 항공정보 (NOTAM)
- 국토부 NOTAM API hook
- 활성 NFZ 자동 import (동적 NFZ로 표시)
- 항공안전법 위반 감지·경보

### Phase 25 — Battery Aging Model
- Cycle count 누적
- Voltage sag under load (실 LiPo 곡선)
- Cold weather derating
- 배터리 교체 임무 자동 큐잉

### Phase 26 — Acoustic Propagation
- 드론 모터음 거리 감쇠 모델 (역제곱·지면 반사)
- 시민 신고 시뮬레이션 (NIMBY)
- 야간 비행 제한 자동 적용

### Phase 27 — Counter-UAS (C-UAS) 시스템
- RF 탐지·방해
- 그물 발사·하이재킹
- 시각·EO 추적 + classification

### Phase 28 — Swarm Choreography
- 음악 동기 군무 (BGM beat detect)
- 형상 변환 (글자·로고 모핑)
- 광고 시연 모드

### Phase 29 — Weather Forecast Integration
- 5일 기상 예보 hook
- 임무 자동 재계획 (악천후 회피)
- 시간 슬라이더로 미래 시뮬레이션

### Phase 30 — UTM Federation
- 다중 UTM 인스턴스 (지역별)
- Inter-UTM handoff 프로토콜
- 국가 간 공역 통과 시나리오

---

## 🔮 Phase 31-45 — 중기 (2027 H1)

### Phase 31 — Quantum-Resistant Telemetry (PQC 통합)
- 기존 `src/quantum/pqc_telemetry.py` Kyber-768 + Dilithium-3
- 시뮬 내 모든 통신에 PQC 헤더 추가
- 33× 대역폭 오버헤드 시각화

### Phase 32 — Satellite Constellation Visualization
- LEO 위성 (Starlink/OneWeb) 통신 백홀
- 위성 가시성 + handoff 시뮬레이션
- 도섭지·해상 백홀

### Phase 33 — Underwater Vehicle Integration (해양 확장)
- 해양 시뮬에 UUV (수중 드론) 추가
- 음파 통신 모델
- 모선-드론-UUV 3계층 협업

### Phase 34 — Sensor Fusion Workbench
- LIDAR · 레이더 · EO · IR · RF 합성
- Kalman filter / EKF / particle filter 토글
- 각 센서 noise 슬라이더

### Phase 35 — Edge Computing Topology
- 5G MEC 노드 분산
- 시뮬 워크로드 자동 분배 (drone↔MEC↔cloud)
- latency budget 시각화

### Phase 36 — Federated Learning Demo
- 분산 드론들이 로컬 학습 + aggregate
- Privacy budget (differential privacy)
- 시뮬 내 학습 진행 추이

### Phase 37 — Multi-Domain (Air + Ground + Maritime)
- 지상 로봇 (UGV) 추가
- 해양·공중·지상 통합 관제
- 도메인 간 임무 hand-off

### Phase 38 — Realistic Audio Engine
- HRTF 3D 오디오
- 도플러 효과
- 환경 반사 (도시·산악)

### Phase 39 — Photogrammetry Replay
- 실 항공 영상 → 3D 모델 자동 생성
- 시뮬 환경에 import
- 시민 데이터 기여 모드

### Phase 40 — Esports Mode
- 두 관제사 PvP (방어 vs 침입)
- 점수·랭킹 시스템
- 토너먼트 브래킷

### Phase 41 — Procedural City Generation
- 실 도시 데이터 (OSM) → 자동 3D 추출
- 도시별 빌딩 윤곽
- 야간 조명 자동

### Phase 42 — Eye-Tracking Heatmap
- WebGazer.js 또는 외부 eye tracker
- 관제사 시선 누적 heatmap
- UX 개선 데이터

### Phase 43 — Voice Command Macros
- "수색 패턴 알파"·"긴급 회항" 등 매크로 등록
- 음성 트리거 → 다중 ATC 명령 일괄 실행
- macro 라이브러리 공유

### Phase 44 — Time Compression / Dilation
- 시뮬 속도 0.1× ~ 10,000×
- 24시간 운영 시뮬 1분 안에
- 통계 누적 + 리포트

### Phase 45 — Hardware-In-The-Loop (HITL) Cluster
- 다중 Pixhawk + Jetson 동시 연결
- 시뮬-실드론 50% 비율 혼합
- 야외 비행 사전 검증

---

## 🌠 Phase 46-50 — 장기 비전 (2027 H2+)

### Phase 46 — 국가 단위 공역 시뮬
- 대한민국 전 영공 (1:1)
- 모든 공항·헬기장·도심 항공
- 시간당 실 운항 데이터 import

### Phase 47 — Climate Impact Modeling
- 드론 배기·소음 누적 → 환경 점수
- 탄소발자국 자동 계산
- 친환경 임무 우선순위화

### Phase 48 — Cross-Border Coordination
- 한국-일본-중국 공역 경계
- 외교 프로토콜 시뮬레이션
- 군용 vs 민간 분리

### Phase 49 — Mars / Lunar Operation
- 저중력 + 저밀도 대기 (Mars)
- 무중력 (Lunar)
- NASA AMPS-style 시연

### Phase 50 — Open Source Public Demo
- 누구나 GitHub Pages 데모 접속
- 임시 게스트 ATC 계정 발급
- "Daily Challenge" 시나리오
- 글로벌 리더보드

---

## 🎯 우선순위 매트릭스

| Phase | 임팩트 | 난이도 | 권장 시기 |
|---|---|---|---|
| 10 통합·문서 | 🔥🔥 | ⭐ | 즉시 |
| 11 해양 ATC 이식 | 🔥🔥🔥 | ⭐⭐ | 즉시 |
| 12 멀티 윈도우 | 🔥🔥 | ⭐⭐ | 1주 내 |
| 13 WebGPU 확장 | 🔥🔥 | ⭐⭐⭐ | 2주 내 |
| 14 시나리오 갤러리 | 🔥🔥🔥 | ⭐⭐ | 2주 내 |
| 15 다국어 | 🔥 | ⭐ | 1개월 |
| 16 협업 (CRDT) | 🔥🔥🔥🔥 | ⭐⭐⭐⭐ | Q3 |
| 17 VR 헤드셋 | 🔥🔥🔥 | ⭐⭐⭐⭐ | Q3 |
| 20 AI Copilot | 🔥🔥🔥🔥🔥 | ⭐⭐⭐ | Q4 |
| 21 적대 드론 (RL) | 🔥🔥🔥 | ⭐⭐⭐⭐ | Q4 |
| 22 디지털 트윈 | 🔥🔥🔥🔥 | ⭐⭐⭐⭐⭐ | 2027 H1 |
| 50 공개 데모 | 🔥🔥🔥🔥 | ⭐⭐⭐ | 장기 |

## 📈 누적 KPI 목표

| 항목 | MEGA 종료 | HYPER Phase 15 | Phase 30 | Phase 50 |
|---|---|---|---|---|
| 시뮬레이터 코드 | 9,793 line | 13,000+ | 20,000+ | 30,000+ |
| `_sdacs` API | 230 | 320 | 500 | 800 |
| E2E 케이스 | 67 | 100 | 200 | 400 |
| 사용자 수 (목표) | β | 100 | 1,000 | 100,000 |
| GitHub Stars | TBD | 200 | 2K | 20K |

## 🔄 거버넌스

- 각 Phase = 독립 PR (또는 1-3 PR 쪼개기)
- E2E 테스트 신규 5-15 케이스 필수
- 회귀 4,140+ 통과 보존
- README + STATUS_REPORT + 본 문서 동기 갱신
- 사본 4종 md5 일치 유지
- 데스크탑 빌드 검증 (Linux AppImage 최소)

## 📚 참고

- [`SIMULATOR_MEGA_PLAN.md`](SIMULATOR_MEGA_PLAN.md) — Phase 1-9 마스터 (완료)
- [`SIMULATOR_PHASE_PLANS.md`](SIMULATOR_PHASE_PLANS.md) — Phase 2-9 상세 명세
- [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md) — 데스크탑 v1.1 릴리스 절차
- [`STATUS_REPORT.md`](../STATUS_REPORT.md) — 현재 진척 상태
- [`ROADMAP.md`](../ROADMAP.md) — Phase 691-755 (기존 트랙)
