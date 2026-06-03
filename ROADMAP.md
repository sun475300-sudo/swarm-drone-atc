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

### Phase 691-700: Aeronautical Information Management (완료)
- [x] NOTAM 전자 관리 시스템 (`notam_manager.py`)
- [x] TFR (Temporary Flight Restriction) 핸들러 (`tfr_handler.py`)
- [x] 버티포트 운영 관리 (`vertiport_ops.py`)
- [x] METAR/TAF 기상 보고 파서 (`metar_parser.py`)
- [x] 국경 간 비행 조율 (`cross_border_coord.py`)
- [x] 보험 리스크 계산기 (`insurance_risk.py`)
- [x] 항공 차트 데이터베이스 (`aero_charts.py`)
- [x] 비행 추적 서비스 (`flight_following.py`)
- [x] 통합 AIM 브리핑 서비스 (`aim_briefing.py`)
- [x] 후-비행 보고서 통합기 (`post_flight_report.py`)

---

## Progress Snapshot / 진행 현황 (2026-06-03 기준)

| 트랙 | 완료 | 진행률 | 비고 |
|---|---|---|---|
| Phase 1-690 (Core·이론·AI·HW·UTM·AIM) | 100% | ████████████ | 690 phases 모두 완료 |
| **Track A** (P691-700, 실기 드론) | 0% | ░░░░░░░░░░░░ | SW 컴포넌트 11개 통합 완료, 실기 검증 미시작 |
| **Track B** (P701-710, 논문화) | 40% | █████░░░░░░░ | P703-P706 완료, P701·P702·P707-P710 진행 예정 |
| **Track C** (P711-720, 서비스화) | 80% | █████████░░░ | P712-P719 완료, P711(React)·P720(베타) 진행 예정 |
| **Track D** (P721-735, 웹 시뮬레이터) | 60% | ███████░░░░░ | P721-P729 완료, P730-P735 진행 예정 |
| **Track E** (P736-745, 확장 연구) **NEW** | 0% | ░░░░░░░░░░░░ | 신설 — RL·UAS-T·Sim2Real·UAM·양자 |
| **Track F** (P746-755, 산학 실증) **NEW** | 0% | ░░░░░░░░░░░░ | 신설 — K-UAM·해수부·산림청·창업 |

**총 Phase 691-755 (65개) 중 22개 완료 = 34%** (Phase 1-690 포함 시 전체 712/755 = **94%**)

## In Progress / 진행 예정

> Phase 691부터는 3개 트랙(하드웨어 실기화 · 연구 논문화 · 배포 서비스화)을 **병렬로** 진행.
> Phase 736부터는 Track E(확장 연구) · Track F(산학 실증) 추가 신설.
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
- [x] **P703** — 벤치마크 데이터셋 공개화 — `benchmarks/` 10개 시나리오 + 3개 기준선(ORCA/VO/CBS) + CC-BY-4.0 + DATASET_CARD.md + CITATION.bib 완비 (2026-05-29)
- [x] **P704** — Reproducibility 패키지 — Dockerfile·Dockerfile.gpu·Dockerfile.reproducible + docker-compose.reproducible.yml (PYTHONHASHSEED=0, seed 고정) 완비 (2026-05-29)
- [x] **P705** — 평가 메트릭 정형화 — `src/analytics/metrics.py` NMR·MSD·PE·MS·FT·AU·RID_CR·RTF 8종 공식 정의 및 Evaluator 클래스 구현 (2026-05-29)
- [x] **P706** — 기여도 비교 실험 (vs ORCA, vs VO, vs 단일 CBS) — SDACS W2 APF+CBS 하이브리드 어댑터 완성, NMR·MSD·AU 유의미 개선 확인 (2026-06-01)
- [ ] **P707** — 논문 초안 작성 (IROS 2026 또는 AIAA SciTech 2027 투고 목표)
- [ ] **P708** — 내부 리뷰 3회 + 지도교수 피드백 반영
- [ ] **P709** — 공식 투고 및 arXiv 프리프린트 업로드
- [ ] **P710** — 학술대회 발표 슬라이드·포스터 (동강대 학술대회 4/23 포함)

### Track C — 배포·서비스화 (Phase 711-720)

공역 관리자용 대시보드를 SaaS 수준으로 안정화.

- [~] **P711** — FastAPI 백엔드 완성 (`api/fastapi_server.py` 769줄, 전체 엔드포인트 구현) — React 프론트엔드 미구현
- [x] **P712** — 인증·권한(OAuth2, RBAC) 및 감사 로그 — HS256 JWT + 3계층 RBAC(admin/operator/viewer) + 감사로그 완전 구현, 29개 테스트 통과 (2026-06-01)
- [x] **P713** — 실시간 WebSocket 채널 — `simulation/ws_bridge.py` 2Hz 스트리밍 + FastAPI `/ws/telemetry` 완비 (2026-05-29)
- [~] **P714** — PostgreSQL + TimescaleDB 이력 저장, 30일 보존 — `src/storage/timescale.py` asyncpg 클라이언트 + `db/migrations/001_initial_schema.sql` 하이퍼테이블·보존정책 완비, 36개 테스트 통과 (2026-06-03)
- [x] **P715** — Docker Compose → Kubernetes Helm 차트 변환 — `helm/sdacs/` Chart.yaml + values.yaml + 8개 템플릿 (Deployment·Service·Ingress·HPA·Redis·PostgreSQL) 완비 (2026-06-03)
- [x] **P716** — CI/CD 완비 — GitHub Actions 6개 워크플로우 (테스트 3-버전 매트릭스, lint, mypy, 재현성 검증, E2E smoke, Pages 배포) (2026-05-29)
- [x] **P717** — 부하 테스트 (100기 스웜 실시간 시각화, 60 FPS 유지) — 100드론 60s PASS (p99=10.74ms, RTF=140x), `scripts/load_test.py` (2026-06-01)
- [x] **P718** — 관측성 스택 — Prometheus + Grafana + Loki docker-compose, `monitoring/prometheus.yml` + `alerts.yml` + Grafana 대시보드 JSON + `src/monitoring/metrics.py` prometheus_client 미들웨어 완비 (2026-06-03)
- [x] **P719** — 보안 감사 — `scripts/security_audit.sh` (bandit·pip-audit·safety) + `.github/workflows/security.yml` (bandit SARIF + pip-audit + trivy) 완비 (2026-06-03)
- [ ] **P720** — 공개 베타 오픈 (3개 파일럿 기관, 피드백 수집 4주)

### Track D — 웹 시뮬레이터·시각화 (Phase 721-735)

브라우저 단독 실행(Three.js) 시뮬레이터를 데모·교육·검증 자산으로 고도화. 모든 항목 헤드리스 스모크(`tests/e2e/`) + CI(`sim-smoke.yml`)로 검증.

- [x] **P721** — Electron 데스크탑 앱 (Win NSIS / Mac DMG / Linux AppImage) — 홈 화면에서 두 시뮬레이터 카드 선택, three.js 로컬 vendor 패키징, GitHub Actions 3-OS 자동 빌드 → Releases 드래프트 (2026-06-03, .bat/.command/.sh + serve.py 폐기)
- [x] **P722** — 드론 상세/호버 툴팁·클릭 선택·2×2 분석 뷰 (2026-05)
- [x] **P723** — 외부 드론·조류 탐지·식별(DnI) + 식별 정확도 모델 (2026-05)
- [x] **P724** — 대규모 InstancedMesh 렌더(1k~10k) + 성능 측정 HUD(B6: draw call·FPS·삼각형) (2026-06-03)
- [x] **P725** — 드론 다중 선택(B4, Shift+클릭) + 집계 패널 (2026-06-03)
- [x] **P726** — 경로효율 per-leg 정정(B9) + CPA 라벨 스프라이트 풀 최적화(B10) (2026-06-03)
- [x] **P727** — 해양 소형선 감지 시뮬레이터 신설 — 레이더 물리(C1)·AIS융합(C2)·EO/IR(C3)·COLREG(C4)·트랙상세(C5)·리포트(C6)·해안선(C7)·시나리오8종(C8)·검증기록(C9) (2026-06-03)
- [x] **P728** — 해양 기술 문서(`docs/maritime_detection_technical.md`) + 헤드리스 스모크 17/17 (2026-06-03)
- [x] **P729** — 대규모 모드 글로우 InstancedMesh(B3) — 1k~10k 환경 단일 드로우콜 (2026-05-31, 커밋 `2f43895`)
- [ ] **P730** — UI 국제화(B5, KO/EN 토글) + 모바일·터치 대응
- [ ] **P731** — 공역 레이어 패널 중복 통합(O1) + 두 시뮬레이터 공통 컴포넌트 추출(D1)
- [ ] **P732** — 대규모 CPA 충돌예측 복원(B2, 공간 해시) — 1k+ 환경 충돌쌍 시각화
- [ ] **P733** — `ws_bridge` 실데이터 라이브 수신 토글(데모↔실측)
- [ ] **P734** — 리플레이·타임라인 스크러버 + 동기화 멀티뷰 고도화
- [ ] **P735** — 해양 EO/IR 실 카메라 프레임 연동(센서 SDK) — 실기화 연계

---

### Track E — 확장 연구·기술 심화 (Phase 736-745) **NEW**

논문·발표 이후 SDACS를 다음 단계 연구 자산으로 확장. 자율성·견고성·범용성에 초점.

- [ ] **P736** — 강화학습 기반 충돌 회피 정책(PPO/SAC) — 규칙 기반 APF·CBS와 동등 안전성 + 25% 효율 개선 검증
- [ ] **P737** — 비협조 침입자(UAS-T) 대응 — DnI 정확도 + 회피 결정 트리 통합, 적대적 시나리오 100건 평가
- [ ] **P738** — 도시 환경 LiDAR/Mesh 통합 — 3D 건물 데이터(국토부 NSDI) 임포트, NFZ 자동 생성
- [ ] **P739** — Sim-to-Real Domain Randomization — 풍속·센서 노이즈 분포 학습, 실기 일반화 성능 측정
- [ ] **P740** — 디지털 트윈 동기화 — 실기 텔레메트리 → SDACS 상태 갱신 <50ms, MAVLink2 헤더 확장
- [ ] **P741** — 페일오버 클러스터링 — AirspaceController 다중 인스턴스(Raft 합의) 마스터 장애 시 <1s 전환
- [ ] **P742** — eVTOL·UAM 시나리오 — 5kg+ 기체 · 회랑 1000ft+ · 인구 밀집 NFZ, K-UAM Grand Challenge 호환
- [ ] **P743** — 양자 안전 통신 — 포스트양자 KEM(Kyber/Dilithium) 텔레메트리 채널 PoC
- [ ] **P744** — 폐쇄망(MIL/L4) 운영 모드 — 외부 인터넷 0의존 + 자체 시각 SLAM, 군용 배포 베이스라인
- [ ] **P745** — 멀티 모달 LLM 관제 보조 — 음성·자연어 → ATC 명령 변환, Whisper + Claude/GPT 통합

### Track F — 산학 실증·사업화 (Phase 746-755) **NEW**

국내 기관·기업과 실증 협업을 통한 사회적 임팩트 확장.

- [ ] **P746** — 국토교통부 K-UAM 실증사업 신청 — 2027 Q1 공고 대비 컨소시엄 구성
- [ ] **P747** — 해양수산부 항만 드론 시범사업 — 해양 시뮬레이터 자산을 항만 보안 솔루션화
- [ ] **P748** — 산림청 산불 감시 협업 — 야간·악천후 IR 감시 모듈 + 자율 패트롤 알고리즘
- [ ] **P749** — KISA·국정원 보안 평가 — Track C 시스템에 대한 정보보안 감리(CSAP)
- [ ] **P750** — 농업용 방제 드론 통합 — 작업 영역 분할(Voronoi) + 농약 잔량 최적화
- [ ] **P751** — 도서·산간 의료 배송 PoC — 응급 의약품 우선순위 운영
- [ ] **P752** — 학회 워크숍 주최 — IROS/ICRA UAM workshop 기획·발표
- [ ] **P753** — 기술 이전 / 라이선싱 — Apache 2.0 듀얼 라이선스 + 상용 SLA 옵션
- [ ] **P754** — 후속 캡스톤 연계 — 목포대 후속 학번 인수인계 + 멘토링 체계 수립
- [ ] **P755** — 창업 / 분사 검토 — TIPS 패키지 신청 또는 사내 벤처 모델 비교

---

## Contributing / 기여

이 프로젝트는 목포대학교 캡스톤 디자인 프로젝트입니다.
기여를 원하시면 Issue를 통해 제안해 주세요.

*Last updated: 2026-06-03 — P729(B3 대규모 글로우 인스턴싱) 완료 체크 + 진행률 스냅샷 표 추가 + **Track E(확장 연구, P736-745)** 및 **Track F(산학 실증, P746-755)** 신설. 전체 진행률 94%(712/755). 테스트 3,830+개.*
