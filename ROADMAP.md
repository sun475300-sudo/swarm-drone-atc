# SDACS Roadmap / 개발 로드맵

## Completed / 완료

### Phase 1-470: Core System (완료)
- SimPy 이산 이벤트 시뮬레이션 엔진
- AirspaceController 1Hz 충돌 감지/해결
- CPA 90초 선제 충돌 예측
- APF 인공 포텐셜 장 충돌 회피
- Voronoi 동적 공역 분할
- CBS 다중 에이전트 경로 계획
- Monte Carlo 시나리오 검증 (7개 시나리오)
- Dash 3D 시각화 대시보드
- 25개 언어 다중 언어 확장 (Phase 471-500)

### Phase 501-600: Deep Theory & Expansion (완료)
- Quantum communications, Blockchain v2, GAN, Edge ML
- Swarm intelligence, Visual rendering, DSP
- Reaction-diffusion, QEC, IIT consciousness, Neural ODE
- Phase 600 Grand Unified Controller

### Phase 601-610: Advanced Simulation Models (완료)
- Swarm Topology Control (algebraic connectivity)
- Vickrey Auction (second-price resource allocation)
- Fisher Information Field (sensor fusion)
- PRM + A* Path Planning
- Laplacian Consensus (formation control)
- Optogenetics-inspired Control
- Multi-Fidelity Simulation (adaptive LOD)
- Bayesian Reputation System
- Coulomb Electrostatics Swarm
- CSP Solver (AC-3 + backtracking)

### Phase 611-620: Multi-Language V (완료)
TypeScript, Swift, Kotlin, PHP, Haskell, COBOL, R, Perl, Scheme, Octave

### Phase 621-630: Deep Mathematics (완료)
- Bravais Lattice Crystallography
- Digital Pheromone (ACO)
- Hyperbolic Embedding (Poincare Disk)
- Navier-Stokes Hydraulics
- HTM Cortical Column
- NEAT Evolutionary Architecture
- Knot Theory Path Analysis
- Order Book Market Maker
- Persistent Homology (Rips Complex)
- Plasma Physics (Vlasov Simulator)

### Phase 631-640: Multi-Language VI + Benchmark (완료)
- Julia ODE Solver (RK4)
- Scala Stream Processor
- Elixir OTP Fault Supervisor
- Dart Flutter Dashboard
- Lua Config Scripting Engine
- Ruby DevOps Pipeline
- Clojure CQRS Event Sourcing v2
- Erlang Raft Distributed Consensus
- Fortran CFD Wind Tunnel (3D FDM)
- System Benchmark Report Generator

### Phase 641-650: Production Hardening (완료)
- KDTree Spatial Index — O(N^2) → O(N log N) 충돌 스캔
- Telemetry Compression — Delta + RLE 대역폭 최적화
- Health Predictor — Holt 지수평활 잔여수명 예측
- Adaptive Sampling — 밀도 인식 텔레메트리 주기 조절
- Swarm Raft Consensus — 분산 합의 기반 의사결정
- Anomaly Detector — Isolation Forest 이상 비행 탐지
- Mission Scheduler — 우선순위 기반 미션 할당
- Energy Optimizer — 에너지 최적 경로 계획
- Formation GA — 유전 알고리즘 최적 포메이션
- Phase 650 Integration Runner — 통합 벤치마크

### Phase 651-660: Multi-Language VII (완료)
- Go Realtime Monitor (goroutine 기반 병렬 수집)
- Rust Safety Verifier (형식 안전 속성 검증)
- C++ Particle Filter (Monte Carlo 위치 추정)
- Zig Ring Buffer v2 (무잠금 FIFO 오버라이트)
- Ada TMR Voter v2 (비잔틴 장애 허용)
- VHDL FIR Filter (FPGA 디지털 신호 처리)
- Prolog Airspace Rules v2 (상황 인식 적응형 규칙)
- Assembly Kalman Filter (SSE2 1D 고도 추정)
- Nim Async Dispatcher (비동기 이벤트 라우팅)
- OCaml Type Checker (ADT 기반 비행 명령 타입 시스템)

---

### Phase 661-670: Advanced AI (완료)
- [x] Transformer 기반 궤적 예측 (`transformer_trajectory.py`)
- [x] Federated Learning (분산 학습) (`federated_learning_v3.py`)
- [x] GNN 기반 군집 행동 예측 (`gnn_communication.py`)
- [x] Diffusion Model 경로 생성 (`diffusion_path_generator.py`)
- [x] BurnySc2 Behavior Tree + JPS Pathfinder + Frame Cache

### Phase 671-680: Hardware Integration (완료)
- [x] PX4/ArduPilot SITL 연동 (`px4_sitl_bridge.py`)
- [x] ROS2 메시지 브릿지 (`ros2_bridge.py`)
- [x] MQTT/DDS 실시간 통신 (`mqtt_dds_bridge.py`)
- [x] 드론 비행 테스트 프레임워크 (`flight_test_framework.py`)
- [x] 엣지 디바이스 배포 Jetson Nano/Xavier/Orin (`jetson_edge_deployer.py`)

### Phase 681-690: UTM Standards Compliance (완료)
- [x] K-UTM 표준 프로토콜 준수 (`kutm_protocol.py`)
- [x] ADS-B 수신 데이터 통합 (`adsb_receiver.py`)
- [x] ASTM F3411 Remote ID 지원 (`remote_id.py`)
- [x] FAA LAANC 연동 인터페이스 (`faa_laanc.py`)
- [x] 국제 표준 ICAO Doc 10019 준수 (`icao_doc10019.py`)

---

## In Progress / 진행 예정

> Phase 691부터는 3개 트랙(하드웨어 실기화 · 연구 논문화 · 배포 서비스화)을 **병렬로** 진행.
> 각 Phase는 2~5일 단위로 잘라 사용자 개인 스프린트에 할당.

### Track A — 실기 드론 통합 (Phase 691-700)

SITL에서 검증된 제어 스택을 실제 하드웨어로 이식.

- [ ] **P691** — Pixhawk 6X / Cube Orange 보드 펌웨어 플래싱 및 PX4 v1.15+ 연동
- [ ] **P692** — Jetson Orin Nano 컴패니언 컴퓨터 MAVLink 브릿지 (`onboard_bridge.py`)
- [ ] **P693** — 실기 Remote ID 방송 (ASTM F3411 v2.0 Broadcast/Network 모드)
- [ ] **P694** — RTK-GPS 센티미터 정밀도 측위 및 AirspaceController 피드백
- [ ] **P695** — 전파 간섭·통신 단절 대비 Failsafe 로직 (Return-to-Launch / Geofence)
- [ ] **P696** — 다중 기체 스웜 프레임 동기화 (PTP / NTP, <10ms jitter)
- [ ] **P697** — 실내 Motion Capture (Vicon/Optitrack) HITL 셋업
- [ ] **P698** — 실외 소규모 스웜 비행 시험 (3-5기 정지비행·포메이션)
- [ ] **P699** — 풍동·강우·저조도 환경 시나리오 실측
- [ ] **P700** — HITL 통합 보고서 + 안전 분석 (FMEA)

### Track B — 연구·논문화 (Phase 701-710)

목포대 캡스톤 결과물을 학술적 기여로 정제.

- [ ] **P701** — 논문 주제 확정 및 기여 포인트 3개 도출 (CBS+APF 하이브리드? Voronoi 분할?)
- [ ] **P702** — 선행 연구 서베이 (최소 30편, IROS/ICRA/AIAA 기준)
- [ ] **P703** — 벤치마크 데이터셋 공개화 (7개 Monte Carlo 시나리오 + 3개 실기 로그)
- [ ] **P704** — Reproducibility 패키지 (Docker 이미지, 시드 고정, 결과 재현 스크립트)
- [ ] **P705** — 평가 메트릭 정형화 (near-miss rate, airspace utilization, path efficiency)
- [ ] **P706** — 기여도 비교 실험 (vs ORCA, vs VO, vs 단일 CBS)
- [ ] **P707** — 논문 초안 작성 (IROS 2026 또는 AIAA SciTech 2027 투고 목표)
- [ ] **P708** — 내부 리뷰 3회 + 지도교수 피드백 반영
- [ ] **P709** — 공식 투고 및 arXiv 프리프린트 업로드
- [ ] **P710** — 학술대회 발표 슬라이드·포스터 (동강대 학술대회 4/23 포함)

### Track C — 배포·서비스화 (Phase 711-720)

공역 관리자용 대시보드를 SaaS 수준으로 안정화.

- [ ] **P711** — Dash 대시보드를 FastAPI + React로 리팩토링
- [ ] **P712** — 인증·권한(OAuth2, RBAC) 및 감사 로그
- [ ] **P713** — 실시간 WebSocket 채널 (서버 → 브라우저 1 kHz 업데이트)
- [ ] **P714** — PostgreSQL + TimescaleDB 이력 저장, 30일 보존
- [ ] **P715** — Docker Compose → Kubernetes Helm 차트 변환
- [ ] **P716** — CI/CD (GitHub Actions → 컨테이너 레지스트리 → 스테이징)
- [ ] **P717** — 부하 테스트 (100기 스웜 실시간 시각화, 60 FPS 유지)
- [ ] **P718** — 관측성 스택 (Prometheus + Grafana + Loki)
- [ ] **P719** — 보안 감사 (OWASP ZAP, 의존성 CVE 스캔)
- [ ] **P720** — 공개 베타 오픈 (3개 파일럿 기관, 피드백 수집 4주)

---

## Contributing / 기여

이 프로젝트는 목포대학교 캡스톤 디자인 프로젝트입니다.
기여를 원하시면 Issue를 통해 제안해 주세요.

*Last updated: 2026-04-19 (Phase 690 완료, Phase 691-720 로드맵 추가)*
