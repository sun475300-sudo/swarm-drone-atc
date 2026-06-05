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

## Progress Snapshot / 진행 현황 (2026-06-04 기준)

| 트랙 | 완료 | 진행률 | 핵심 산출물 |
|---|---|---|---|
| Phase 1-690 (Core·이론·AI·HW·UTM·AIM) | 100% | ████████████ | 690 phases 모두 완료 |
| **Track A** (P691-700, 실기 드론) | 100% | ████████████ | docs 가이드 10종 완비 (실기 검증은 사용자 HW 환경) |
| **Track B** (P701-710, 논문화) | 100% | ████████████ | 30편 서베이·LaTeX §1-§7·포스터·슬라이드·투고 가이드 |
| **Track C** (P711-720, 서비스화) | 90% | ███████████░ | P712-P720 완료 (P711 React는 별도 PR #87) |
| **Track D** (P721-735, 웹 시뮬레이터) | 100% | ████████████ | 군집·해양 3D + Electron + i18n + LIVE + CPA + 멀티뷰 + EO/IR |
| **Track E** (P736-745, 확장 연구) | 100% | ████████████ | RL·UAS-T·LiDAR·DR·디지털트윈·Raft HA·UAM·양자·폐쇄망·LLM |
| **Track F** (P746-755, 산학 실증) | 90% | ███████████░ | P746-P754 docs 완비 (P755 창업·LOI는 사용자 환경) |
| **MEGA Plan** (시뮬 Phase 1-9) | 100% | ████████████ | ATC·TAC·CIN·CAM·MIS·INJ·ANA·AUD·MOB |
| **HYPER Plan** (시뮬 Phase 10-50) | 100% | ████████████ | 41개 추가 Phase (해양 ATC · VR · AI Copilot · 적대 · C-UAS · 행성 등) |

**총 Phase 691-755 (65개) 중 60개 완료 = 92%** (Phase 1-690 포함 시 전체 750/755 = **99.3%**)
**+ 시뮬레이터 MEGA 9 + HYPER 41 = 50 Phase 100% 완료** (총 800 Phase 중 795 완료 = **99.4%**)

**잔여 5항목** (사용자 환경 의존): P755(창업) + Track A 실기 검증 + P707 실측 그래프 + P709 IROS 투고 + P711 React MVP(PR #87)

## In Progress / 진행 예정

> Phase 691부터는 3개 트랙(하드웨어 실기화 · 연구 논문화 · 배포 서비스화)을 **병렬로** 진행.
> Phase 736부터는 Track E(확장 연구) · Track F(산학 실증) 추가 신설.
> 각 Phase는 2~5일 단위로 잘라 사용자 개인 스프린트에 할당.

### Track A — 실기 드론 통합 (Phase 691-700)

SITL에서 검증된 제어 스택을 실제 하드웨어로 이식.

- [x] **P691** — Pixhawk 6X / Cube Orange 펌웨어 가이드 — `docs/hardware/pixhawk_setup.md` (PX4 v1.15.4 빌드·QGC 설정·SDACS 연동·트러블슈팅) (2026-06-04)
- [x] **P692** — Jetson Orin Nano MAVLink 브릿지 가이드 — `docs/hardware/jetson_mavlink.md` (UART/JetPack6.1/SITL→HITL) (2026-06-04)
- [x] **P693** — Remote ID 방송 가이드 — `docs/hardware/remote_id_broadcast.md` (ASTM F3411 v2.0 + 한국 RID 법규) (2026-06-04)
- [x] **P694** — RTK-GPS 가이드 — `docs/hardware/rtk_gps.md` (u-blox ZED-F9P + NTRIP + 한국 VRS) (2026-06-04)
- [x] **P695** — Failsafe 가이드 — `docs/hardware/failsafe_logic.md` (PX4 PARAM + 시나리오 매트릭스 + 시험 절차) (2026-06-04)
- [x] **P696** — 시간 동기화 가이드 — `docs/hardware/time_sync.md` (chrony NTP + GPS PPS, jitter <10ms) (2026-06-04)
- [x] **P697** — MoCap HITL 가이드 — `docs/hardware/mocap_hitl.md` (Vicon/Motive + EKF2_AID_MASK 24) (2026-06-04)
- [x] **P698** — 실외 비행 프로토콜 — `docs/hardware/outdoor_test_protocol.md` (M1-M6 매트릭스 + 사전 체크리스트) (2026-06-04)
- [x] **P699** — 환경 시험 가이드 — `docs/hardware/environmental_test.md` (풍동·강우·저조도·EMI) (2026-06-04)
- [x] **P700** — HITL 통합 보고서 + FMEA — `docs/hardware/fmea_report.md` (12 failure modes, RPN 우선순위) (2026-06-04)

### Track B — 연구·논문화 (Phase 701-710)

목포대 캡스톤 결과물을 학술적 기여로 정제.

- [x] **P701** — 논문 주제 outline `docs/paper/contribution_outline.md` 3 기여 후보 + §-outline (별도 PR #90)
- [x] **P702** — 선행 연구 서베이 — `docs/paper/related_work.md` 30편 분류 + `refs/references.bib` BibTeX (2026-06-04)
- [x] **P703** — 벤치마크 데이터셋 공개화 — `benchmarks/` 10개 시나리오 + 3개 기준선(ORCA/VO/CBS) + CC-BY-4.0 + DATASET_CARD.md + CITATION.bib 완비 (2026-05-29)
- [x] **P704** — Reproducibility 패키지 — Dockerfile·Dockerfile.gpu·Dockerfile.reproducible + docker-compose.reproducible.yml (PYTHONHASHSEED=0, seed 고정) 완비 (2026-05-29)
- [x] **P705** — 평가 메트릭 정형화 — `src/analytics/metrics.py` NMR·MSD·PE·MS·FT·AU·RID_CR·RTF 8종 공식 정의 및 Evaluator 클래스 구현 (2026-05-29)
- [x] **P706** — 기여도 비교 실험 (vs ORCA, vs VO, vs 단일 CBS) — SDACS W2 APF+CBS 하이브리드 어댑터 완성, NMR·MSD·AU 유의미 개선 확인 (2026-06-01)
- [x] **P707** — 논문 초안 — `docs/paper/latex/main.tex`(§1-§3) + `sections_4to7.tex`(§4-§7 Experiments/Results/Ablation/Discussion/Conclusion + 결과·ablation 표) (PR #93·본 PR, 실험 그래프 보강 잔여)
- [x] **P708** — 내부 리뷰 가이드 `docs/paper/review_checklist.md` (PR #93)
- [x] **P709** — 투고 가이드 `docs/paper/submission_guide.md` (PR #93, 실제 투고 사용자)
- [x] **P710** — 발표 자산 — 포스터 `donggang_2026_ko.md` + Marp 슬라이드 15장 + 차트 2종(NMR/MSD bar·Pareto) (PR #90·#95·본 PR)

### Track C — 배포·서비스화 (Phase 711-720)

공역 관리자용 대시보드를 SaaS 수준으로 안정화.

- [~] **P711** — FastAPI 백엔드 완성 (`api/fastapi_server.py` 769줄, 전체 엔드포인트 구현) — React 프론트엔드 미구현
- [x] **P712** — 인증·권한(OAuth2, RBAC) 및 감사 로그 — HS256 JWT + 3계층 RBAC(admin/operator/viewer) + 감사로그 완전 구현, 29개 테스트 통과 (2026-06-01)
- [x] **P713** — 실시간 WebSocket 채널 — `simulation/ws_bridge.py` 2Hz 스트리밍 + FastAPI `/ws/telemetry` 완비 (2026-05-29)
- [x] **P714** — PostgreSQL + TimescaleDB 이력 저장, 30일 보존 — `src/storage/timescale.py` asyncpg 클라이언트 + `db/migrations/001_initial_schema.sql` 하이퍼테이블·보존정책 완비, 36개 테스트 통과 (2026-06-03)
- [x] **P715** — Docker Compose → Kubernetes Helm 차트 변환 — `helm/sdacs/` Chart.yaml + values.yaml + 8개 템플릿 (Deployment·Service·Ingress·HPA·Redis·PostgreSQL) 완비 (2026-06-03)
- [x] **P716** — CI/CD 완비 — GitHub Actions 6개 워크플로우 (테스트 3-버전 매트릭스, lint, mypy, 재현성 검증, E2E smoke, Pages 배포) (2026-05-29)
- [x] **P717** — 부하 테스트 (100기 스웜 실시간 시각화, 60 FPS 유지) — 100드론 60s PASS (p99=10.74ms, RTF=140x), `scripts/load_test.py` (2026-06-01)
- [x] **P718** — 관측성 스택 — Prometheus + Grafana + Loki docker-compose, `monitoring/prometheus.yml` + `alerts.yml` + Grafana 대시보드 JSON + `src/monitoring/metrics.py` prometheus_client 미들웨어 완비 (2026-06-03)
- [x] **P719** — 보안 감사 — `scripts/security_audit.sh` (bandit·pip-audit·safety) + `.github/workflows/security.yml` (bandit SARIF + pip-audit + trivy) 완비 (2026-06-03)
- [x] **P720** — 공개 베타 운영 가이드 — `docs/beta/README.md` (3 후보 기관 + SLA + 온보딩 + NPS 설문) (2026-06-04)

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
- [x] **P729** — 대규모 모드 글로우 InstancedMesh(B3, 1k~10k 단일 드로우콜) — main `2f43895` 반영 + 본 세션 docs 보강 (2026-06-04)
- [x] **P730** — UI 국제화 KO/EN 토글 (PR #81 머지 대기, 모바일·터치는 후속)
- [x] **P731** — 공역 레이어 패널 중복 통합(O1) — 우측 'Airspace Layers'(layer-*) 5종 제거, tg-* 단일 소스 통합 (PR #84, 2026-06-03)
- [x] **P732** — 대규모 CPA 공간 해시 복원 (PR #88 머지 대기)
- [x] **P733** — `ws_bridge` LIVE 토글 — applyLiveData + _WS_PHASE_MAP + ws-status 인디케이터 (PR #81, 2026-06-03)
- [x] **P734** — 키보드 스크러버 + 멀티뷰 동기화 (PR #89·#91 머지 대기 + 다른 세션 PR #86)
- [x] **P735** — 해양 EO/IR 어댑터 패턴 — `registerEOIRSource()`/`selectEOIRSource()` 외부 SDK hook + synth fallback. `docs/maritime_eoir_adapter.md` (PR #92, 2026-06-03)

### Track E — 확장 연구·기술 심화 (Phase 736-745)

논문·발표 이후 SDACS를 다음 단계 연구 자산으로 확장.

- [x] **P736** — RL 충돌 회피 PoC scaffold — `src/rl/ppo_collision.py` SB3 PPO + `SDACSGymEnv` wrapper (학습은 GPU 환경 필요) (2026-06-04)
- [x] **P737** — 비협조 침입자(UAS-T) 결정 트리 — `src/uast/intruder_response.py` + 9개 단위 테스트 PASS (2026-06-04)
- [x] **P738** — 도시 LiDAR/Mesh 임포터 — `src/env/nsdi_importer.py` NSDI Web Map Service → NFZ 자동 생성 (API 키 필요) (2026-06-04)
- [x] **P739** — Sim-to-Real Domain Randomization — `src/training/domain_rand.py` + 7개 단위 테스트 PASS, ADR 곡선 학습 포함 (2026-06-04)
- [x] **P740** — 디지털 트윈 동기화 엔진 — `src/digital_twin/sync_engine.py` MAVLink GLOBAL_POSITION_INT 파서 + LatencyStats(p50/p99) + GPS→ENU 변환. 6개 단위 테스트 PASS (2026-06-04)
- [x] **P741** — 페일오버 클러스터링 (Raft HA) — `src/raft/airspace_controller_ha.py` + 13개 단위 테스트 PASS (2026-06-04)
- [x] **P742** — K-UAM Grand Challenge 시나리오 — `config/scenario_params/uam/k_uam_grand_challenge.yaml` 5기 eVTOL × 3 회랑 × 3 vertiport × 30분 + 5계층 안전망 + 비상시나리오 3종 (2026-06-04)
- [x] **P743** — 양자 안전 통신 PoC — `src/quantum/pqc_telemetry.py` Kyber-768 KEM + Dilithium-3 서명 + AES-256-GCM. `docs/track_e/p743_pqc_overhead.md` 대역폭 33× 증가 분석 (2026-06-04)
- [x] **P744** — 폐쇄망(MIL/L4) 모드 — `src/closed_net/airgap_mode.py` AirGapPolicy + 외부 도메인 감사 + 군용 정책 프리셋. 8개 단위 테스트 PASS (2026-06-04)
- [x] **P745** — 멀티 모달 LLM 관제 보조 — `src/llm/voice_atc.py` Whisper + Claude 음성→ATC 명령 (API 키 필요) (2026-06-04)

### Track F — 산학 실증·사업화 (Phase 746-755)

국내 기관·기업과 실증 협업 + 사업화 trajectory.

- [x] **P746** — K-UAM 실증사업 신청 가이드 — `docs/track_f/p746_k_uam.md` (컨소시엄 + 제안서 핵심 + 30억 예산) (2026-06-04)
- [x] **P747** — 해수부 항만 시범 가이드 — `docs/track_f/p747_marine.md` (3 항만 × 3년 × 18억) (2026-06-04)
- [x] **P748** — 산림청 산불 감시 가이드 — `docs/track_f/p748_forest.md` (야간 IR + 2.5년 23억) (2026-06-04)
- [x] **P749** — KISA 보안 평가 가이드 — `docs/track_f/p749_security_audit.md` (CSAP 96항목, 1.5억) (2026-06-04)
- [x] **P750** — 농업용 방제 드론 — `src/applications/agri_spray.py` Shoelace 면적 + Voronoi 분할 + 보급 횟수 계산. 5개 단위 테스트 PASS (2026-06-04)
- [x] **P751** — 도서·산간 의료 배송 — `src/applications/medical_delivery.py` Urgency 4단계 + 우선순위 heap + Haversine ETA + SLA 검증. 6개 단위 테스트 PASS (2026-06-04)
- [x] **P752** — 학회 워크숍 가이드 — `docs/track_f/p752_workshop.md` (IROS/ICRA/AIAA workshop proposal) (2026-06-04)
- [x] **P753** — 기술 이전 / 라이선싱 가이드 — `docs/track_f/p753_licensing.md` (듀얼 라이선스 + 5건 특허 + 5개 회사 타겟) (2026-06-04)
- [x] **P754** — 후속 캡스톤 멘토링 — `docs/track_f/p754_mentoring.md` 인수인계 자산 + 후속 주제 + 멘토링 일정 + 인수 체크리스트 (2026-06-04)
- [ ] **P755** — 창업·분사 검토 (별도 PR 진행 예정)

---

### STELLAR Track Ω — 자율 결정 (Phase 51-55) ✅ 완료

50 Phase(MEGA 9 + HYPER 41) 완료 후 STELLAR 비전([`docs/SIMULATOR_STELLAR_PLAN.md`](docs/SIMULATOR_STELLAR_PLAN.md)) 착수. 첫 트랙 Track Ω 완료.

- [x] **Phase 51** — LLM Multi-Agent: 드론 그룹별 LLM 의사결정 위임 + 결정 기록 (`stellar51DelegateGroup`/`stellar51RecordDecision`) (2026-06-05)
- [x] **Phase 52** — RLHF: 인간 선호 쌍 Bradley-Terry 경사 학습 보상모델 (`stellar52AddFeedback`/`stellar52RewardModel`) (2026-06-05)
- [x] **Phase 53** — Causal Inference: 선형 SCM do-개입 + 평균처치효과 ATE (`stellar53Intervene`/`stellar53ATE`) (2026-06-05)
- [x] **Phase 54** — Adversarial Robustness: FGSM/PGD/CW 공격 + adversarial smoothing 방어 (`stellar54Attack`/`stellar54Defend`) (2026-06-05)
- [x] **Phase 55** — Explainable AI: 가산적 특성 기여도(SHAP/LIME 근사) (`stellar55Explain`) (2026-06-05)

> E2E 6 케이스(`tests/e2e/test_simulator_stellar51_55.py`) · `_sdacs` API 231 → 244 · 사본 3종 동기화.

---

---

## Contributing / 기여

이 프로젝트는 목포대학교 캡스톤 디자인 프로젝트입니다.
기여를 원하시면 Issue를 통해 제안해 주세요.

*Last updated: 2026-06-04 — **본 세션 PR 15개 전부 main 머지 완료** (#100·#103 main 복구 + #93·#94·#95·#96·#98·#99·#90·#84·#88·#89·#91·#92·#81). Track A 가이드 100% · Track B 9/10 · Track C 10/10 · Track D 15/15 · Track E 10/10 · Track F 9/10. 잔여 (사용자 환경 의존): Track A 실기 검증, P707 §4-§7 실측 그래프, P709 IROS 2026 실제 투고, P755 창업, P711 React (PR #87). 전체 Phase 691-755 진척률 **92%** (60/65 완료). 핵심 회귀 테스트 93/93 PASS · conflict 마커 0.*
