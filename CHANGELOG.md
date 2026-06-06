# Changelog

이 프로젝트의 모든 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 기반으로 합니다.

## [Unreleased]

### 추가 (feat) — P711 React 대시보드 MVP
- `frontend/` Vite + React 공역 관제 대시보드 신설 (기존 FastAPI 백엔드 무변경 소비)
- 로그인(JWT/RBAC 역할 표시) · 시나리오 목록·실행 + run 폴링 · 공역 스냅샷 폴링 · WebSocket 텔레메트리 피드 · 헬스 배지
- `src/api.js` 응답 봉투 정규화 클라이언트 + vitest 단위 테스트 5개
- 실 백엔드(uvicorn) E2E 스모크 검증: 로그인·시나리오·run 생애주기·무인증 401 게이팅 확인
- ROADMAP P711 `[~] → [x]`, Track C 90% → 100%

## [v1.5.0] - 2026-06-05 — POST-UNIVERSE (Phase 151-200) · **𝟏 Unity 도달**

### 추가 (feat) — Track Ʊ Cosmic (151-160)
- 151 Galactic Network · 152 Dark Matter · 153 Pulsar Time Sync
- 154 Wormhole · 155 Gravitational Wave · 156 Antimatter
- 157 Black Hole Accretion · 158 Cosmic Ray Shield
- 159 Interstellar DTN · 160 1조 광년 SDACS 커버리지

### 추가 (feat) — Track Ϡ Time/Reality (161-170)
- 161 Retrocausal · 162 Causality Loop · 163 Tachyon · 164 Block Universe
- 165 Spacetime Edit · 166 Collapse Ctrl · 167 Quantum Eraser
- 168 Decoherence · 169 Timeline Branch · 170 Reality Editor

### 추가 (feat) — Track 𝛀 Consciousness (171-180)
- 171 Digital Human · 172 Mind Upload · 173 Memory Encode TB
- 174 Dream Share · 175 Telepathy · 176 Empathy · 177 Free Will
- 178 Personality Transfer · 179 Soul Continuity · 180 Conscious Drone

### 추가 (feat) — Track Ξ̃ Final Hurdles (181-190)
- 181 Heat Death Mitigation · 182 Entropy Reverse · 183 Info Preserve Forever
- 184 Boltzmann Brain Prevention · 185 Sim Hypothesis · 186 Vacuum Decay Shield
- 187 Strangelet · 188 Grey Goo · 189 Paperclip Max · 190 Existential Risk

### 추가 (feat) — Track ∅ Transcendence (191-200)
- 191 Beyond Math · 192 Beyond Logic · 193 Beyond Physics · 194 Beyond Computation
- 195 Beyond Time · 196 Beyond Space · 197 Beyond Existence
- 198 Pure Information · 199 Universal Identity
- **200 SDACS = 𝟏 (Unity)** — All Phases Complete

### 검증
- E2E **7/7** (`tests/e2e/test_simulator_post_universe.py`)
- 누적 **239/240 E2E + 4,140 회귀 = 4,379**
- `_sdacs` API: 330 → **388**

## [v1.4.0] - 2026-06-05 — ULTIMATE (Phase 101-150) · **Universe OS 도달**

### 추가 (feat) — Track ∞ Performance Beyond (101-110)
- 101 Petaflop GPU · 102 양자 spatial hash · 103 Photonic Compute
- 104 Optane Memory · 105 RDMA 100Gb/s · 106 FPGA APF
- 107 TPU v5 · 108 Neuromorphic · 109 DPU · **110 1B drone capacity**

### 추가 (feat) — Track ⌬ Materials & Nano (111-120)
- 111 Nano 1mm³ · 112 Smart Dust · 113 Graphene 10× battery
- 114 Self-healing · 115 Bio-degradable · 116 Atmo Harvester
- 117 Piezo · 118 Solar 100% · 119 Meta Invisibility · 120 Programmable Matter

### 추가 (feat) — Track ⚕ Bio-Hybrid (121-130)
- 121 Neuron-silicon · 122 DNA Storage · 123 Bacteria Propulsion
- 124 Algae Photo-charging · 125 Mycelium Repair · 126 Avian Partnership
- 127 Insect Swarm · 128 Symbiotic · 129 Bio-fluor · 130 Living Drone

### 추가 (feat) — Track ☉ Universal Standard (131-140)
- 131 IETF RFC · 132 ICAO · 133 ISO 21384-3 · 134 IEEE 802.UAS
- 135 ITU-R · 136 UN ECOSOC · 137 EU EASA · 138 FAA Part 108
- 139 중국 CAAC · **140 100% 글로벌 단일 ATC OS**

### 추가 (feat) — Track 🌀 SDACS Eternal (141-150)
- 141 Self-aware · 142 Recursive Sim · 143 Consciousness Experiment
- 144 Reality Blur · 145 Universal Translator · 146 Eternal Mission
- 147 Time Loop · 148 Multi-verse · 149 Theory of Everything
- **150 Universe OS** (`Universe-OS-1.0`)

### 검증
- E2E **17/17** (`tests/e2e/test_simulator_ultimate101_110.py` + `test_simulator_ultimate111_150.py`)
- 누적 232/233 E2E

## [v1.3.0] - 2026-06-05 — STELLAR FINAL (Phase 52-100) · **SDACS 2.0 표준**

### 추가 (feat) — Track Ω 자율결정 (52-55)
- 52 RLHF · 53 Causal Inference · 54 Adversarial Robust · 55 Explainable AI

### 추가 (feat) — Track Σ 초대규모 (56-60)
- 56 GPU 100K WGSL · 57 Distributed Sim · 58 Cloud Burst
- 59 10Gb/s Streaming · 60 Video Proc av1

### 추가 (feat) — Track Φ 물리트윈 (61-65)
- 61 Skybrush · 62 Cesium GIS · 63 UE5 · 64 ROS 2 + Gazebo · 65 Isaac Sim

### 추가 (feat) — Track Ψ 사회 (66-70) · Ξ 지구너머 (71-75) · Δ 양자 (76-80) · Λ XR (81-85) · Π 경제 (86-90) · Π+ Ultimate (91-95) · Ω+ Singularity (96-100)

### 검증
- E2E **22/22** (`tests/e2e/test_simulator_stellar.py`)
- 누적 215/216 E2E
- 100 Phase 마일스톤 도달

## [v1.2.0] - 2026-06-05 — HYPER FINAL (Phase 32-50 일괄 19개)

### 추가 (feat) — 통신·네트워크
- **Phase 32** Satellite Constellation (Starlink alt=550 inc=53 / OneWeb 1200/87 / Kuiper 590/51.9)
- **Phase 33** UUV 수중 드론 + 음파 통신 1 kbps
- **Phase 35** 5G MEC Edge Computing (노드 부하 기반 할당)
- **Phase 38** Realistic Audio (HRTF + Doppler 343 m/s)

### 추가 (feat) — AI·학습
- **Phase 34** Sensor Fusion Workbench (LiDAR/Radar/EO/IR/RF + Kalman/EKF/Particle)
- **Phase 36** Federated Learning (DP epsilon 소진, convex avg)
- **Phase 42** Eye-Tracking Heatmap (32×32 grid)
- **Phase 43** Voice Command Macros (시퀀스 등록·실행)

### 추가 (feat) — 운영·연동
- **Phase 37** Multi-Domain (공중+지상 UGV+해양 inter-domain handoff)
- **Phase 39** Photogrammetry Replay (외부 3D import)
- **Phase 41** Procedural City Generation
- **Phase 44** Time Compression/Dilation (0.1× - 10000×)
- **Phase 45** HITL Cluster (다중 Pixhawk)

### 추가 (feat) — 정책·시나리오
- **Phase 40** Esports Mode (PvP defender vs attacker)
- **Phase 46** National Airspace 1:1 (한국 6 공항 ICAO)
- **Phase 47** Climate Impact (0.434 kg CO2/kWh, 평균 250W)
- **Phase 48** Cross-Border Coordination
- **Phase 49** Mars/Lunar (중력 + 대기 밀도)
- **Phase 50** Public Demo Leaderboard + Daily Challenge

### 검증
- E2E **22/22** (`tests/e2e/test_simulator_phase32_50.py`)
- 누적 **193/194 E2E + 4,140 회귀 = 4,333 통과**
- `_sdacs` API: 170 → **231**

## [v1.1.0] - 2026-06-04 — HYPER MID (Phase 11-31)

### 추가 (feat)
- Phase 11 해양 ATC 콘솔 (8 명령 + TTS)
- Phase 12 Electron 멀티 윈도우 + IPC 시간축 동기
- Phase 13 WebGPU 50K 스캐폴드
- Phase 14 시나리오 갤러리 (5 카테고리)
- Phase 15 4언어 i18n (KO/EN/JA/ZH)
- Phase 16 CRDT 다중 관제 (Lamport)
- Phase 17 WebXR VR
- Phase 18 AR Overlay
- Phase 19 Mission Recorder 공유 (.sdacs-mission)
- Phase 20 AI Copilot (22 NLP 패턴)
- Phase 21 적대 드론 4종
- Phase 22 Digital Twin Pixhawk (MAVLink GPI)
- Phase 23 Wind Field 64×64
- Phase 24 NOTAM hook
- Phase 25 Battery Aging Model
- Phase 26 Acoustic Propagation (50dB 신고)
- Phase 27 Counter-UAS (RF/GPS/net/hijack)
- Phase 28 Choreography 5종
- Phase 29 Weather Forecast 120h
- Phase 30 UTM Federation
- Phase 31 PQC Telemetry (Kyber+Dilithium, ~52× overhead)

## [v1.0.0] - 2026-06-04 — MEGA (Phase 1-9)

### 추가 (feat)
- Phase 1 ATC 콘솔 (HOLD/RTB/REROUTE/ALT/SPD/TURN/CLEAR + TTS)
- Phase 2 TAC 전술 시각화 (예측 라인·CPA 마커·속도 벡터)
- Phase 3 CIN 시네마틱 (태양 24h + 입자 + MediaRecorder)
- Phase 4 CAM 카메라 모드 (FPV/chase/side + 7 프리셋)
- Phase 5 MIS 임무 계획 (5 템플릿)
- Phase 6 INJ 장애 주입 (GPS/모터/통신/Rogue/NFZ/EMP/EMI)
- Phase 7 ANA 분석 강화 (히트맵·KPI window·LaTeX)
- Phase 8 AUD 환경 사운드
- Phase 9 MOB 모바일/PWA
- Electron 데스크탑 v1.1 (Win NSIS / Mac DMG / Linux AppImage)
- CI 3-job (js-syntax + node-smoke + python-pytest)

## [Unreleased] - 2026-05-03

### 추가 (feat)

- `FormationPattern.DIAMOND` (5번째 편대 패턴) — 영상 컨셉 4방향 외곽 확장 (`a222b08`, PR #23)
- `swarm_autonomous_no_preplan` 시나리오 — 사전 경로 없이 자율 탐색 데모 (`4c67eac`, PR #23)
- `docs/MASTER_TODO_ATC.md` — 통합 백로그 (A0~A4 트랙 + Phase 691~720) (PR #19)
- `docs/REGRESSION_NOTES_2026-04-26.md` — torch DLL fallback + build-backend 회귀 노트 (PR #19)
- `docs/OPS_TRAFFIC_RED_ANALYSIS_2026-05-03.md` — ops_report traffic RED 의도된 동작 분석 (PR #26)
- `docs/faq.md` — 캡스톤 발표 Q&A 20문항 (PR #22)
- `docs/roadmap_public.md` — Phase 691~720 공개 로드맵 (PR #22)
- `CONTRIBUTING.md` — 학술 프로젝트용 기여 가이드 (PR #22)
- `SECURITY.md` — 책임 있는 신고 정책 (PR #19)

### 수정 (fix)

- torch import OSError 처리 — Windows DLL 차단 시 simulator graceful CPU fallback (PR #19, `0d4dafa`+`c13f72d`)
- `pyproject.toml` build-backend 오타 수정 (`setuptools.backends.legacy:build` → `setuptools.build_meta`) — CI 의존성 설치 단계 복구 (PR #19, `a59fd48`)
- `src/hardware/onboard_bridge.py` mypy 4건 회귀 — `[tool.mypy.overrides]` 에 `src.hardware.*` 추가 (PR #19, `d6b437f`)
- `python-app.yml` deprecated 빈 워크플로 — manual-dispatch 격리, 매 푸시 0초 fail 노이즈 제거 (PR #22)
- README 테스트 수 동기화 (2,722+ → 3,481+) (PR #19)

### 의존성 (deps)

- jinja2 3.1.4 → 3.1.6 (sandbox breakout 3건 patch, dependabot) (PR #21, `a73cd9b`)
- pytest 8.x 명시 핀 (`pytest>=8.4,<9`) — pytest 9 메이저 자동 PR 차단 (PR #24)
- imgur 외부 의존 제거 — 12개 이미지 `docs/images/imgur/` 로 로컬화 (1.9MB) (PR #25)

### 테스트 (test)

- `tests/test_apf_engine_fallback.py` — torch fallback 회귀 방지 4건 (PR #19)
- `tests/test_main_cli.py` — argparse 회귀 방어 8건 (PR #22)
- `tests/test_formation.py` — 5 패턴 30 회귀 (DIAMOND 신규 포함) (PR #23)
- `tests/test_e2e_reporter_traffic_thresholds.py` — traffic 임계 경계 8건 (PR #26)

### 외부 작업 (main 직접 푸시, Phase B 트랙)

- P701 paper topic 확정 — AIAA SciTech 2027 D-39 (`c54829f`)
- P702 prior-work survey 30 references (MAPF / Reactive / UTM / Swarm 4 buckets) (`b7fb88b`)
- P704 Reproducibility — centralized RNG + lock file (`f0ec08c`)
- P707 paper draft (Add) + MAVLink adapter 개선 (`155e2a1`)

### CI/배포

- 본 라운드 6 PR 머지 + 1 PR close (#19/#21/#22/#23/#24/#25 머지, #20 close)
- 열린 PR 0개 → main 깔끔한 상태 (2026-04-27 시점)

## [1.0.0] - 2026-04-13

### 추가 (feat)

- 12개 고급 확장 일괄 완료 (`0a43a9a`)
- PPO 강화학습 충돌 회피 에이전트 추가 (`04cda85`)
- ONNX 모델 내보내기 + GNN 드론 통신 네트워크 (`967a675`)
- 12개 확장 작업 일괄 완료 (`d0edbc5`)
- PyTorch 기반 ML 충돌 예측 모델 추가 (`ef92cbe`)
- FastAPI REST API 서버 추가 (`0cc2548`)
- WebSocket 실시간 브릿지 + GitHub Pages 링크 + MC 워커 호환성 (`d6e00e8`)
- 충돌해결률 97.5% 달성 + Docker GPU + 벤치마크 + 시나리오 대시보드 (`a624098`)
- Docker GPU 이미지 설정 (nvidia-docker) (`a0c8eae`)
- GPU 텐서 캐싱 + FP16 + CI 파이프라인 + Dash GPU 패널 (`b5f5bba`)
- 3D 시뮬레이터 HUD에 GPU 상태 표시 + DeprecationWarning 수정 (`94416f7`)
- CBS 충돌탐지 + Voronoi 공역분할 GPU 가속 추가 (`cb09562`)
- PyTorch CUDA GPU 가속 APF 엔진 추가 (`3103041`)

### 수정 (fix)

- waypoint_optimizer np.cross 2D DeprecationWarning 수정 (`42a3f89`)
- 20개 테스트 실패 수정 + deadlock 해결 → 2,722 전체 통과 (`3870551`)
- estimate_power_w ZeroDivisionError 방지 + ATC 드론 UI 크기 확대 (`91a8f7c`)

### 테스트 (test)

- airspace_controller 커버리지 강화 (11→29개) + flaky test 안정화 (`587eaf4`)

### 문서 (docs)

- README GPU 가속 가이드 및 테스트 현황 업데이트 (`00613e2`)
- 공모용 아이디어 상세설명 텍스트 추가 (`5a0c2de`)

### 기타

- Merge pull request #16 (`ae6d533`)
