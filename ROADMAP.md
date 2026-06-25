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
| **STELLAR~POST-UNIVERSE** (시뮬 Phase 51-200) | 100% | ████████████ | Phase 200 = 𝟏 (Unity) · Phase 51 LLM Multi-Agent 격상 (단, 다수 mock/speculative — maturity 공시) |
| **TRANSCENDENCE** (시뮬 Phase 201-300) | 10% | █░░░░░░░░░░░ | Phase 201-208 Maturity Honesty 완료 (분류·Mock Detector·experimental·beta·production 회귀) |
| **GENESIS** (시뮬 Phase 301-400) | 43% | █████░░░░░░░ | 301-317·322·341·342·362·364·367·381-400 완료 — 인증·CSAP카탈로그·UAM운용기준·감항인증·도구자격TQL5·빌드환경사양·SQA감사·자율·교육·실증·아카이브·체험판·성과요약·성숙도·인수인계·교육자산·종합보고·자생력·공개준비·통합게이트·Legacy선언 |
| **ODYSSEY** (시뮬 Phase 401-500) | 5% | █░░░░░░░░░░░ | 408 ICAO 매핑·447 fuzzing·448 property·466 schema·486 재현 완료 |

**총 Phase 691-755 (65개) 중 61개 완료 = 94%** (Phase 1-690 포함 시 전체 751/755 = **99.5%**)
**+ 시뮬레이터 MEGA 9 + HYPER 41 = 50 Phase 100% 완료** (총 800 Phase 중 796 완료 = **99.5%**)

**잔여 4항목** (사용자 환경 의존): P755(창업) + Track A 실기 검증 + P707 실측 그래프 + P709 IROS 투고
(P711 React MVP는 2026-06-09 `frontend/` 통합으로 완료 — 마지막 코드 로드맵 항목 종료)

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
- [x] **P707** — 논문 초안 — `docs/paper/latex/main.tex` §1-§7 완성(§2 RELATED WORK narrative + 10개 인용 검증, §3 `APF_PARAMS_WINDY` 표, §4-§7 `sections_4to7.tex` `\input` 통합) + `sections_4to7.tex`(Experiments/Results/Ablation/Discussion/Conclusion) (PR #93·#205, 실측 실험 그래프 보강만 잔여)
- [x] **P708** — 내부 리뷰 가이드 `docs/paper/review_checklist.md` (PR #93)
- [x] **P709** — 투고 가이드 `docs/paper/submission_guide.md` (PR #93, 실제 투고 사용자)
- [x] **P710** — 발표 자산 — 포스터 `donggang_2026_ko.md` + Marp 슬라이드 15장 + 차트 2종(NMR/MSD bar·Pareto) (PR #90·#95·본 PR)

### Track C — 배포·서비스화 (Phase 711-720)

공역 관리자용 대시보드를 SaaS 수준으로 안정화.

- [x] **P711** — FastAPI 백엔드 + React 프론트엔드 완성 — `api/fastapi_server.py` 전체 엔드포인트 + `frontend/` Vite+React 18 대시보드(로그인·시나리오 실행·스냅샷·WS 텔레메트리). vitest 5/5 + vite 프로덕션 빌드 통과 (2026-06-09)
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

- [x] **P736** — RL 충돌 회피 PoC — `src/rl/ppo_collision.py` SB3 PPO + `SDACSGymEnv` (경량 point-mass 운동학으로 reset/step/observation/reward 완전 구현, GPU 없이 rollout·evaluate 동작) + 12개 단위 테스트 PASS. 학습만 GPU 필요 (2026-06-09)
- [x] **P737** — 비협조 침입자(UAS-T) 결정 트리 — `src/uast/intruder_response.py` + 9개 단위 테스트 PASS (2026-06-04)
- [x] **P738** — 도시 LiDAR/Mesh 임포터 — `src/env/nsdi_importer.py` NSDI Web Map Service → NFZ 자동 생성 (API 키 필요) (2026-06-04)
- [x] **P739** — Sim-to-Real Domain Randomization — `src/training/domain_rand.py` + 7개 단위 테스트 PASS, ADR 곡선 학습 포함 (2026-06-04)
- [x] **P740** — 디지털 트윈 동기화 엔진 — `src/digital_twin/sync_engine.py` MAVLink GLOBAL_POSITION_INT 파서 + LatencyStats(p50/p99) + GPS→ENU 변환. 6개 단위 테스트 PASS (2026-06-04)
- [x] **P741** — 페일오버 클러스터링 (Raft HA) — `src/raft/airspace_controller_ha.py` RPC 핸들러 + `src/raft/cluster.py` 결정론적 인프로세스 합의 루프(실제 선거·하트비트·quorum 복제·페일오버) + Raft §5.3 로그 일관성 검사·팔로워 catch-up(next_index/match_index) + 29개 단위 테스트 PASS (2026-06-09)
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

### Track G — 시뮬레이터 TRANSCENDENCE (Phase 201-300) · 2026-06-12 신설

> 상세: [`docs/SIMULATOR_TRANSCENDENCE_PLAN.md`](docs/SIMULATOR_TRANSCENDENCE_PLAN.md) · 실행 일정: [`docs/MASTER_PLAN_2026H2.md`](docs/MASTER_PLAN_2026H2.md)

- [x] **Phase 201-202** — API Maturity Registry + `maturityReport()` (407 API → production 93·beta 98·mock 110·speculative 103) (2026-06-12)
- [x] **Phase 207-208** — SDACS_API.md maturity 컬럼 + README maturity 섹션 (2026-06-12)
- [x] **Phase 203 + 206** — Mock Detector(console.warn + `mockCalls` 카운트) + `experimental.*` 네임스페이스 격리, E2E 2건 + CI 정합성 게이트(G-2·G-4) (2026-06-12)
- [x] **Phase 204** — Production 핵심 12종 회귀 강화 — `test_simulator_production_core.py` (getter 전수 + 12종 호출 + 93 회귀 방지) (2026-06-12)
- [x] **Phase 205** — Beta API 부분 검증 — `test_simulator_beta_subset.py` (Copilot·적대·C-UAS·WindField·PQC, 5건) (2026-06-12)
- [x] **Phase 209-210** — API Deprecation Policy + SemVer 규약 — `docs/API_DEPRECATION_POLICY.md`, `docs/API_SEMVER_POLICY.md` (성숙도별 유예 기간 + SemVer↔API 영향 + 긴급 보안 폐기 + CI 규칙) (2026-06-18)
- [ ] **Phase 211-220** — production 격상 (12 → 30 API)
- [ ] **Phase 221-240** — Real Validation (WebGPU 실 WGSL·CRDT Yjs·MAVLink SITL·KMA 풍속장)
- [ ] **Phase 241-260** — Multi-User Reality (WS 관제 서버·다중 관제사·TimescaleDB·부하 100명)
- [ ] **Phase 261-280** — Hardware Loop (Pixhawk HITL·Jetson 엣지·RTK·실 비행 데이터셋) *(사용자 HW 의존)*
- [x] **Phase 286** 🏆 안전망 Ablation 자동화 — `scripts/ablation_study.py` (APF·CBS 계층 제거 효과 측정, baseline/no_apf/no_cbs/no_apf_no_cbs × N 시드 → 충돌·근접경고·해결률 markdown+JSON), 시뮬레이터·컨트롤러 `ablation.disable_apf/disable_cbs` 토글(기본 미설정 = 전 계층 활성) + 12개 단위 테스트 PASS (2026-06-13)
- [ ] **Phase 281-285·287-300** — Academic Impact (IROS 투고·Zenodo DOI·K-UTM 표준 제안)

### Track H — 시뮬레이터 GENESIS (Phase 301-400) · 2026-06-12 수립

> 상세: [`docs/SIMULATOR_GENESIS_PLAN.md`](docs/SIMULATOR_GENESIS_PLAN.md) — *"이것은 세상에 남는가"*

- [x] **Phase 301** 🏭 항공안전법·드론활용촉진법 적합성 매트릭스 — `docs/certification/AIR_SAFETY_ACT_MATRIX.md` (2026-06-12)
- [x] **Phase 302** 🏭 SORA 자동 계산기 — `_sdacs.soraAssess()` JARUS 2.0 결정적 구현, E2E 6건 (2026-06-12)
- [x] **Phase 304** 🏭 KC 전파인증 체크리스트 — `docs/certification/KC_RADIO_CERTIFICATION.md` (2026-06-12)
- [x] **Phase 306** 🏭 RTM 5계층 커버리지 — `docs/certification/RTM_5LAYER_COVERAGE.md` 21건 추적 (2026-06-12)
- [x] **Phase 309** 🏭 조종자 자격증명 매핑 — `docs/certification/PILOT_LICENSE_MAPPING.md` (2026-06-12)
- [x] **Phase 308** 🏭 배상책임보험 요율 산정 API — `simulation/insurance_rate_quote.py` (Phase 67 mock 격상 — 항공사업법 §70 의무보험 스펙, MTOW·운용·ILF·NCB·경력·야간/BVLOS 결정적 산정, 33건 PASS) (2026-06-15)
- [x] **Phase 303·305·307·310** 🏭 인증 문서 세트 — `FLIGHT_PLAN_FORM.md`, `DO178C_GAP_ANALYSIS.md`, `ACCIDENT_REPORT_FORM.md`, `NIGHT_BVLOS_APPROVAL.md` (2026-06-18)
- [x] **Phase 311** 🏭 KISA CSAP 자가진단 자동화 — `simulation/csap_self_assessment.py` (CSAP 정보보호 기준 14개 통제분야 정렬·이행 상태 4종 결정적 점수화·영역별 이행률·종합 준비도 판정·JSON/텍스트 export, 20건 PASS) (2026-06-15)
- [x] **Phase 312** 🏭 CSAP 통제항목 카탈로그 확장 — `simulation/csap_catalog_extension.py` (Phase 311 확장: 35개 SCAN_RULES 기반 파일시스템 자동 스캔, 14개 통제분야×2~3항목 glob 패턴 매칭, ScanResult/CatalogScanReport frozen dataclass, scan_catalog/get_domain_scan/list_domains, CLI --scan/--domain/--domains/--json, 37건 PASS) (2026-06-25)
- [x] **Phase 313** 🏭 UAM 운용기준 정렬 점검 — `simulation/uam_operating_standards.py` (한국 UAM ConOps 10개 기준영역×23항목 파일시스템 스캔, ALIGNED/PARTIAL/NOT_ALIGNED 결정적 판정, _EXCLUDE_DIRS 비소스 디렉토리 제외, ComplianceResult/ComplianceReport frozen dataclass, check_standards/get_category_report/list_categories, CLI --check/--category/--categories/--json, 38건 PASS) (2026-06-25)
- [x] **Phase 314** 🏭 감항 인증 준비 체크리스트 — `simulation/airworthiness_checklist.py` (DO-178C DAL-D 수준 6개 프로세스 영역×20개 항목 파일시스템 스캔, COMPLIANT/PARTIAL/NON_COMPLIANT 결정적 판정, AirworthinessResult/AirworthinessReport frozen dataclass, check_airworthiness/get_process_report/list_processes, CLI --check/--category/--categories/--json, 38건 PASS) (2026-06-25)
- [x] **Phase 315** 🏭 DO-178C 도구 자격 평가 (TQL-5) — `simulation/tool_qualification.py` (DO-178C §12.2 기준 4개 카테고리×12개 도구 설치/설정 증거 파일시스템 스캔, QUALIFIED/PARTIAL/NOT_QUALIFIED 결정적 판정, ToolQualResult/ToolQualReport frozen dataclass, assess_tools/get_category_report/list_categories, CLI --assess/--category/--categories/--json, 38건 PASS) (2026-06-25)
- [x] **Phase 316** 🏭 빌드 환경 사양서 자동 수집 — `simulation/build_env_spec.py` (DO-178C §11.6 기준 5개 카테고리×15개 항목 런타임/파일 존재 검사, DOCUMENTED/PARTIAL/UNDOCUMENTED 결정적 판정, EnvItem/EnvReport frozen dataclass, collect_env/get_category_report/list_categories, CLI --collect/--category/--categories/--json, 37건 PASS) (2026-06-25)
- [x] **Phase 317** 🏭 SQA 감사 로그 — `simulation/sqa_audit.py` (DO-178C §8 SQA 5개 목표×15개 점검 항목 파일시스템 스캔, MET/PARTIAL/NOT_MET 결정적 판정, SqaFinding/SqaReport frozen dataclass, run_sqa_audit/get_objective_report/list_objectives, CLI --audit/--objective/--objectives/--json, 37건 PASS) (2026-06-25)
- [ ] **Phase 318-320** 🏭 Certification & Compliance 잔여 — CCB 변경통제·테스트절차서·4대계획서
- [x] **Phase 322** 🌍 `.sdacs-scenario` 스키마 + 검증기 — `simulation/scenario_schema.py` + `docs/schemas/sdacs-scenario.schema.json`, 20건 PASS (2026-06-15)
- [ ] **Phase 321-340** 🌍 Ecosystem & Open Source — 플러그인 SDK·`@sdacs/core` npm·`sdacs-sim` PyPI·v2.0 API 안정화
- [x] **Phase 341** 🏙 목포 해역 실 좌표계 임포트 — `src/applications/mokpo_harbor.py` 해도 기반 NFZ 4종(부두·대교·지형·정박지)·회랑 3종 결정적 배치 + 레이 캐스팅 NFZ 판정·회랑 충돌 검사, 8건 PASS (2026-06-15)
- [x] **Phase 342** 🏙 전남 도서(신안·완도) 의료 배송 거점 DB — `src/applications/jeonnam_island_sites.py` 실 좌표·거점·Haversine ETA, 7건 PASS (2026-06-15)
- [ ] **Phase 341-360** 🏙 Real Deployment — 목포 해역 실 좌표·전남 도서 의료 배송·90일 파일럿 백서
- [x] **Phase 367** 🤖 스웜 자가 치유 — `src/autonomy/swarm_self_healing.py` 결손 드론 임무 자동 재분배, 12건 PASS (2026-06-15)
- [x] **Phase 362** 🤖 APF+RL 하이브리드 충돌 회피 — `src/autonomy/hybrid_collision_avoidance.py` FIRAS APF(0.7)+PPO RL(0.3) 가중 결합, 안전 우선 오버라이드(5m 이내 APF 전용), frozen dataclass 구성, 에피소드 평가 CLI, 27건 PASS (2026-06-20)
- [x] **Phase 364** 🤖 V2X 드론 간 통신 메시지 규격 — `simulation/v2x_message.py` SAE J2735 BSM 적응 UAS 메시지(DroneBasicSafetyMessage 192B·EmergencyAlert 162B), JSON+바이너리 라운드트립 코덱, 범위 필터링·결정적 패킷 손실 채널, 22건 PASS (2026-06-20)
- [ ] **Phase 361-380** 🤖 Next-Gen Autonomy 잔여 — 온보드 RL 추론·양방향 디지털 트윈
- [x] **Phase 381** 🎓 교육 모드 — 시뮬레이터 `tutorialStart/Next/Status()` 5단계 (2026-06-12)
- [x] **Phase 382** 🎓 실습 과제 10종 — `simulation/practice_assignments.py` 학부 수업용 시나리오·채점 기준·검증 스크립트 (입문~고급 14주 배치, frozen dataclass, 결정적 채점, CLI --list/--detail/--rubric, 44건 PASS) (2026-06-25)
- [x] **Phase 384** 🎓 조종자 자격 이론 연계 문제은행 — `simulation/pilot_exam_bank.py` 1~4종 자격증명 이론시험 유형 ↔ SDACS 시뮬 상황 매핑 40문항(종별 10문항, 4과목: 항공법규·비행이론·기상학·안전관리), frozen dataclass·MappingProxyType, 채점(grade_exam)·과목별 분석·합격 판정(70%), CLI --list/--grade/--question/--subject/--stats/--json, 49건 PASS (2026-06-25)
- [x] **Phase 385** 🎓 후속 기수 온보딩 자동화 — `simulation/onboarding_automation.py` 환경 점검 19항목(Python·패키지·디렉토리·설정) + 아키텍처 투어 18 스톱(4계층+안전·인증·교육·국제·배포) + 온보딩 리포트·환경 구축 힌트, frozen dataclass, CLI --check/--tour/--tour-stop/--report/--setup-hint/--json, 52건 PASS (2026-06-25)
- [x] **Phase 386** 🎓 코드 고고학 가이드 — `simulation/code_archaeology.py` 200+ Phase 히스토리 내비게이션(커밋→Phase 매핑), git log 파싱·ROADMAP.md Phase 추출·인덱스 구축·키워드 검색·통계·타임라인, frozen dataclass, CLI --phases/--phase/--timeline/--stats/--search/--json, 50건 PASS (2026-06-25)
- [x] **Phase 387** 🎓 졸업 심사 발표 키트 — `docs/presentation/DEFENSE_KIT.md` (2026-06-12)
- [x] **Phase 389** 🎓 유지보수 최소 모드 — `docs/MAINTENANCE_MINIMAL_MODE.md` (2026-06-12)
- [x] **Phase 388** 🎓 기술 부채 대장 — `docs/TECH_DEBT_LEDGER.md` 자동 생성 (2026-06-12)
- [x] **Phase 383** 🎓 강의 슬라이드 패키지 — `simulation/curriculum_slide_package.py` 15주 '드론 관제 시스템 설계' 캡스톤 커리큘럼(기초 3주·핵심 4주·중간 1주·심화 4주·프로젝트 3주), 주차별 학습 목표·SDACS 모듈 매핑·실습·슬라이드 개요, frozen dataclass·MappingProxyType, CLI --weeks/--week/--category/--syllabus/--stats/--json, 50건 PASS (2026-06-25)
- [x] **Phase 390** 🎓 아카이브 전략 — `simulation/archive_strategy.py` Zenodo 메타데이터 검증(필수 7·권장 4 필드)·Software Heritage save-now 요청 정보·졸업 아카이브 체크리스트 12항목(7필수·5권장, 기존 파일 자동 감지)·전체 전략 보고서(readiness_pct), frozen dataclass, CLI --validate/--swh/--checklist/--report/--json, 45건 PASS (2026-06-25)
- [x] **Phase 391** 🎓 고교·일반인 체험판 — `simulation/demo_experience.py` 비전문가용 단순화 모드: 난이도 프리셋 3종(쉬움 5대·보통 20대·어려움 50대), 전문 용어 쉬운 사전 12개(APF·CPA·CBS·Geofence·Voronoi 등), 가이드 시나리오 5종(25단계), 단순화 결과 지표 6종, frozen dataclass·MappingProxyType, CLI --presets/--glossary/--search/--scenarios/--metrics/--explain/--package/--stats/--json, 74건 PASS (2026-06-25)
- [x] **Phase 392** 🎓 성과 요약 — `simulation/achievement_summary.py` 프로젝트 전체 성과 정량 집계: 트랙 10개 진척 현황(TrackProgress, progress_pct), 마일스톤 8개(Phase 1~755), ROADMAP.md 완료 Phase 자동 카운트(regex), 시뮬레이션 모듈·테스트 파일 수 glob 집계, frozen dataclass, CLI --summary/--tracks/--milestones/--json, 46건 PASS (2026-06-25)
- [x] **Phase 393** 🎓 성숙도 자가 평가 — `simulation/maturity_assessment.py` 7차원(문서화·테스트·CI/CD·보안·코드품질·커뮤니티·배포) 30개 체크항목 파일시스템 자동 판정, 가중 점수 산정(A~F 등급), frozen dataclass, CLI --assess/--dimension/--dimensions/--json, 42건 PASS (2026-06-25)
- [x] **Phase 394** 🎓 인수인계 체크리스트 — `simulation/handover_checklist.py` 5개 카테고리(환경·문서·계정·데이터·지식전수) 25개 항목 파일시스템 자동 판정, 준비도 산정(준비완료/거의완료/진행중/미준비), frozen dataclass, CLI --check/--category/--categories/--json, 39건 PASS (2026-06-25)
- [x] **Phase 395** 🎓 교육 자산 레지스트리 — `simulation/education_asset_registry.py` GENESIS 트랙 교육·인수인계 자산 16종 체계적 목록화, 3개 유형(module/document/data) 분류, 파일시스템 기반 존재 검증(verify_assets), 커버리지 보고서(RegistryReport), frozen dataclass, CLI --list/--asset/--by-type/--verify/--json, 45건 PASS (2026-06-25)
- [x] **Phase 396** 🎓 GENESIS 종합 보고서 — `simulation/genesis_report.py` Phase 393(성숙도)+394(인수인계)+395(교육자산) 3개 하위시스템 통합, 카테고리별(인증·생태계·실증·자율·교육·레거시) 진척 집계, 종합 등급(A~F) 산정, Legacy 준비 판정, frozen dataclass, CLI --report/--status/--json, 31건 PASS (2026-06-25)
- [x] **Phase 397** 🎓 생태계 자생력 평가 — `simulation/ecosystem_sustainability.py` 원저자 부재 시 프로젝트 독립 유지·발전 가능성 6차원(문서·테스트·의존성·빌드·커뮤니티·교육) 24개 체크 항목 파일시스템 자동 판정, 차원별 점수·종합 등급(A~F)·자생 가능 판정(SUSTAINABILITY_THRESHOLD 70%), frozen dataclass, CLI --assess/--dimension/--dimensions/--json, 42건 PASS (2026-06-25)
- [x] **Phase 398** 🎓 교육 자산 공개 준비 체크리스트 — `simulation/asset_publication_checklist.py` 외부 공개(오픈소스·교재 배포) 준비 5개 카테고리(라이선스·민감정보·문서화·재현성·접근성) 20개 항목 파일시스템 자동 판정, 종합 등급·공개 가능 판정(PUBLICATION_THRESHOLD 80%), frozen dataclass, CLI --check/--category/--categories/--json, 42건 PASS (2026-06-25)
- [x] **Phase 399** 🎓 최종 통합 게이트 — `simulation/integration_gate.py` Phase 393-398 6개 하위시스템(성숙도·인수인계·교육자산·종합보고·자생력·공개준비) 통합 점검, 전체 게이트 통과 판정(GATE_THRESHOLD 60%), frozen dataclass, CLI --gate/--summary/--json, 25건 PASS (2026-06-25)
- [x] **Phase 400** 🎓 **SDACS Legacy 선언** — `simulation/legacy_declaration.py` GENESIS 트랙(Phase 301-400) 정점: Phase 399 통합 게이트 결과 기반 Legacy 선언문 생성, 조건부/완전 Legacy 구분, 6개 하위시스템 요약(SubsystemSummary), 인증서(generate_certificate), 선언문 텍스트 렌더링(render_declaration), frozen dataclass, CLI --declare/--certificate/--json, 44건 PASS (2026-06-25)

### Track I — 시뮬레이터 ODYSSEY (Phase 401-500) · 2026-06-12 수립

> 상세: [`docs/SIMULATOR_ODYSSEY_PLAN.md`](docs/SIMULATOR_ODYSSEY_PLAN.md) — *"이것은 국경과 세대를 넘는가"*

- [x] **Phase 408** 🌏 ICAO 공역 클래스 A-G 매핑 — `docs/certification/AIRSPACE_CLASS_MAPPING.md` + `simulation/airspace_class.py` `classify_airspace()` API 격상 (결정적, 25건 PASS) (2026-06-12, API 2026-06-14)
- [x] **Phase 401·406** 🌏 다국 좌표계·시간대 자동 판정 — `simulation/geo_zones.py` UTM 그리드 존 결정적 판정 + EASA U-space 매핑, 22건 PASS (2026-06-15)
- [x] **Phase 402** 🌏 FAA UTM ConOps v2.0 정렬 + USS 역할 갭 분석 — `simulation/faa_uss_roles.py` USS 역할 17종↔SDACS 모듈 결정적 적합성 매트릭스(핵심 7/7·전체 15/17, 운영자 자격·공공안전 접근 갭 정직 표면화, 46건 PASS, 2026-06-18) + `simulation/faa_utm_gap.py` + `docs/certification/FAA_UTM_GAP_ANALYSIS.md`(21개 USS 요구사항 8 카테고리, 9 full·11 partial·1 gap = 69.05% 준수율, frozen dataclass + MappingProxyType, CLI --report/--gaps/--json/--category, 42건 PASS, 2026-06-20)
- [x] **Phase 403** 🌏 EASA EU 2019/947 운영 카테고리(Open/Specific/Certified) 판정 — `simulation/sora_category.py` + `docs/certification/EU_OPERATIONAL_CATEGORY.md`. GENESIS 302 `soraAssess`(SAIL) 위에 세 운영 카테고리 + Open 하위분류(A1/A2/A3) 결정적 산정. `SORA_IGRC`·`SORA_SAIL_TABLE` JS 동일 복제(수치 불일치 금지), 51건 PASS (2026-06-19)
- [x] **Phase 407** 🌏 ICAO UTM Framework Ed.4 적합성 자가 평가 — `simulation/icao_utm_conformance.py` 운영자 여정 10단계 축 + 3값 status(conformant/partial/gap)·정직성 결속(gap⟺module None) 강제, 가중 83%·핵심 12/14, 56건 PASS (2026-06-19)
- [x] **Phase 409** 🌏 다국 BVLOS 규제 비교 — `simulation/bvlos_regulation_compare.py` + `docs/standards/BVLOS_REGULATION_COMPARISON.md` 한·미·EU·일 4개 관할 6개 비교 축 대조(권위 출처 인용·`as_of` 스냅샷·지원 3/4 일본 갭), 40건 PASS (2026-06-19)
- [ ] **Phase 404·405·410-420** 🌏 Global Expansion 잔여 — EN 완역·국제 벤치마크 제출(BlueSky·U-TRAFMAN)·GUTMA 기고·해외 파일럿 제안서
- [x] **Phase 470** 🏛 표준화 기고 추적 대시보드 — `simulation/standardization_tracker.py` 표준화 기고 단일 SSoT(단조 상태 PLANNED→ADOPTED·`progress()` 22.5%·`validate_registry` PUBLISHED 산출물 디스크 실재 강제), 31건 PASS (2026-06-19)
- [x] **Phase 472** 🏛 국제 워킹그룹 의견서 적합성 게이트 — `simulation/intl_wg_opinion_gate.py` + `docs/standards/INTL_WG_OPINION_GATE.md`. 밴드 471-480("국내 KS 제안 1건 + 국제 워킹그룹 의견서 3건") 중 국제 의견서 칸. JARUS·EUROCAE WG-105·ISO/TC 20/SC 16 초안에 다는 개별 의견이 *채택 처리될* 형식·근거를 갖췄는지 결정적 게이트로 판정. 요건 6종(필수 4·권장 2)을 ISO/IEC Directives Part 1 comment template(대상 절/줄·제안 변경·유형 ge/te/ed)·JARUS/EUROCAE RoP(문서 버전·소속 공개)에서 도출하고 명문 근거 결속. `assess` 우선순위 CRITICAL UNMET→NOT_READY > CRITICAL PARTIAL→NEEDS_WORK > 잔여 미완→NEEDS_WORK > 전부 MET→READY_TO_SUBMIT, `POLICY_MATRIX` 5칸을 테스트가 정확 일치 강제(모순 조합 제외). Phase 470 기고 *상태* 추적·Phase 471 *국내* KS 제정과 평가 대상이 서로 다름(중복 0). 현 후보 JARUS SORA 군집 보완 의견을 격상 없이 `NEEDS_WORK (80.0%)` 정직 공시(WG-02 제안 변경 redline 미완·WG-06 NB 채널 미확인). 자문, 부수효과 0·무작위성 0·기존 모듈 무수정 순수 추가. 단위 29건 PASS (2026-06-21)
- [x] **Phase 421** 🛰 인스턴스 간 디스커버리 프로토콜 — `simulation/federation_discovery.py` + `docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md`, ASTM F3548 DSS 유사 결정적 모델, 13건 PASS (2026-06-18)
- [x] **Phase 422** 🛰 운영 의도(Operational Intent) 4D 교환 포맷 — `simulation/operational_intent.py` + `docs/certification/OPERATIONAL_INTENT_FORMAT.md`, ASTM F3548-21 정렬 frozen dataclass + 라운드트립 직렬화 + 보수적 4D 교차, 24건 PASS (2026-06-18)
- [x] **Phase 423** 🛰 지역 간 관제권 핸드오버 — `simulation/federation_handover.py` Phase 421 점 커버리지 기반 결정적 RETAINED/ACQUIRED/HANDOVER/CONTINGENT 결정 + 이력현상(hysteresis) + 감사 로그, 16건 PASS (2026-06-15)
- [x] **Phase 424** 🛰 연합 충돌 해소 — `simulation/federation_conflict_resolution.py` Phase 422 `intents_conflict` 충돌 탐지 + Phase 602 `VickreyAuction`(2위 가격제) 재사용한 우선순위 협상(낮은 priority=높은 입찰, 동률 `sha256(intent_id)` 안정 해시 분리) + 패자 CONTINGENT 불변 전환 + 불변 감사 로그, 11건 PASS (2026-06-15)
- [x] **Phase 425** 🛰 연합 NOTAM 전파 — `simulation/federation_notam.py` 동적 NFZ를 Phase 421 디스커버리로 발견한 겹치는 인접 인스턴스에만 결정적 브로드캐스트(DELIVERED/DUPLICATE/REVOKED) + NFZ 이동 시 stale 회수 + 멱등 재방송 + 철회 후 origin 소유권 영구 고정 + 불변 감사 로그, 19건 PASS (2026-06-15)
- [x] **Phase 429** 🛰 연합 감사 로그 — `simulation/federation_audit.py` 변조 탐지 SHA-256 해시 체인(append-only·길이 접두 직렬화로 주입·충돌 차단) + 인스턴스 경계 넘는 결정적 CRDT 류 병합(내용 키 사전식 전순서·중복 제거·교환·결합·흡수 멱등) + `verify()` 무결성 검증(변조·삭제 탐지) + 인스턴스/이벤트 쿼리, 29건 PASS (2026-06-15)
- [x] **Phase 430** 🛰 분할 뇌(split-brain) 안전 강하 — `simulation/federation_split_brain.py` 연결 요소 과반 분파 판정 + 4단계 안전 사다리(NOMINAL/HOLD/DESCEND/LAND) 결정적 에스컬레이션 + 이력현상 + 불변 감사 로그, 20건 PASS (2026-06-15)
- [x] **Phase 428** 🛰 인스턴스 간 신뢰 모델 — `simulation/federation_trust.py` Phase 608 Beta-Bernoulli 평판을 인스턴스 레벨로 재사용. 방향성 (관찰자→대상) Beta(α,β) 믿음, 핸드오버·충돌·NOTAM 협조 이벤트 관찰로 갱신, 사후 평균 신뢰 점수 + 불확실성, 임계값·최소 관찰 게이트 신뢰 판정, 불변 감사 로그, 30건 PASS (2026-06-15)
- [x] **Phase 431** 🛰 하이브리드 논리 시계(HLC) — `simulation/federation_hybrid_clock.py` Kulkarni et al. 2014 표준 HLC. `HLCTimestamp`(frozen·전순서) + `HybridLogicalClock` local/receive 이벤트 결정적 갱신. 물리 시각에 가까운 `wall_time` + 논리 `counter` 로 물리 시계 동기화 없이 3+ 메시 연합의 전역 인과 순서 보장(happened-before → 사전식 증가), 물리 시계 역행 견딤, cold-start sentinel(-1), `is_concurrent_with` 동시성 명시, 34건 PASS (2026-06-15)
- [x] **Phase 432** 🛰 메시 연합 토폴로지 + 멀티홉 전파 — `simulation/federation_mesh.py` Phase 421 디스커버리 등록 상태로 공역 경계 인접 그래프 구성(타일형 비중첩 공역도 수평 허용오차로 이웃 인식, 수직·시간은 엄격 교차). 연결 요소·연결성·결정적 BFS 최단 경로 + Phase 425 1홉 전파를 메시 전역 멀티홉으로 일반화한 TTL 한정 전파(`propagate`)·중계 포워딩 테이블(`relay_table`), 25건 PASS (2026-06-15)
- [x] **Phase 433** 🛰 신뢰 가중 메시 라우팅 — `simulation/federation_trust_routing.py` Phase 432 메시 토폴로지 위에서 Phase 428 신뢰 모델로 중계 후보 비용을 가중하는 결정적 최소 비용 라우터 `TrustWeightedRouter`. 간선 비용 `hop_cost + untrust_weight*(1 - trust(origin→node))`, origin 자신의 신뢰 믿음으로 결정(중앙 신뢰 권위 없음). `route`(사전식 동률 분리 Dijkstra)·`route_cost`·`avoid_untrusted_route`·`forwarding_table`·`relay_trust`, 37건 PASS (2026-06-16)
- [x] **Phase 434** 🛰 HLC 통합 인과-안정 배달 — `simulation/federation_causal_delivery.py` Phase 432 메시 전파 위에 Phase 431 HLC 결합. 워터마크(각 출처 FIFO 단조 HLC → 모든 출처 고점 최소 이하 안정, CockroachDB closed-timestamp 발상) 안정 배달로 멀티홉 중복·인스턴스별 사건 순서 불일치 해소. `FederationEvent`·`CausalDeliveryBuffer`(출처별 FIFO 멱등 중복 무시·예상/관측 워터마크·HLC 전순서 배달)·`FederationDeliveryCoordinator`(메시 propagate fan-out), 36건 PASS (2026-06-16)
- [x] **Phase 435** 🛰 메시 복원력 라우팅 — `simulation/federation_resilient_routing.py` Phase 432 메시 스냅샷 위 구조적 복원력 분석. Hopcroft-Tarjan 반복 DFS로 절단점(단일 장애점)·브리지(단일 링크) 식별 + 주 최단 경로와 내부 노드·간선 분리 백업 경로(`backup_path`)·생존 도달성(`surviving_reach`). 결정적·읽기 전용, 31건 PASS (2026-06-16)
- [x] **Phase 436** 🛰 분산 경로-벡터 라우팅 — `simulation/federation_path_vector.py` Phase 432 메시 인접만으로 동작하는 분산 경로-벡터 라우터(`PathVectorRouting`). 각 인스턴스가 직접 이웃만 알고 도달성을 광고·교환해 먼 목적지 경로를 학습 — 전역 스냅샷을 보는 Phase 432 BFS·Phase 433 Dijkstra의 *분산* 대응물. 경로에 자신이 들어 있으면 거부하는 path-vector 루프 방지(BGP AS-PATH 발상), Jacobi(동기) 라운드는 직전 스냅샷만 참조해 갱신 순서와 무관하게 결정적 수렴(라운드 수 = 메시 지름), 동률 경로는 사전식 분리. 수렴 홉 거리가 Phase 432 중앙 BFS와 일치함을 불변식으로 검증, 23건 PASS (2026-06-16)
- [x] **Phase 437** 🛰 신뢰 인지 분산 경로-벡터 라우팅 — `simulation/federation_trust_path_vector.py` Phase 436 분산 경로-벡터에 Phase 428 신뢰를 결합한 `TrustPathVectorRouting`. 각 노드가 광고된 경로 중 *자신이 직접 관찰한 다음 홉 이웃의 신뢰도*를 1순위 선호로 적용(BGP LOCAL_PREF 발상) — 전역 토폴로지를 보는 중앙식 Phase 433과 달리 신뢰 결정이 홉마다 분산되어 합성된다. 선호 키 `(untrust_penalty(node→next_hop), 홉 수, 경로)`, 신뢰 동률(관찰 0 → 균일 0.5)이면 정확히 Phase 436으로 환원, 신뢰는 재배열만 해 도달성은 메시와 동일. next-hop local-pref 라 BGP 류 진동 없이 결정적 수렴, code-reviewer 어드바이저 HIGH 2건 반영(수렴 라운드 상한을 방어적 종결 캡으로 정확 기술·float 동률 분리의 정수 prior 의존성 명시), 19건 PASS (2026-06-16)
- [x] **Phase 438** 🛰 분산 경로-벡터 장애 우회 수렴 — `simulation/federation_path_vector_failover.py` Phase 436/437(고정 메시 1회 수렴)·Phase 435(중앙 구조 분석)의 공백인 *인스턴스 장애 후 분산 재수렴*을 모사하는 `PathVectorFailover`. 살아남은 인접 위에서 Phase 436 수렴을 인접 어댑터로 무수정 재사용해 장애 전후 비교: `rerouted`·`lost_routes`·`is_reroutable`·`surviving_path`·`reconvergence_rounds`. 경로-벡터 전체 경로 광고라 재수렴 = 콜드스타트 고정점, Phase 435 백업 경로·절단점과 교차 검증, 무작위성 0·순수 추가, code-reviewer 어드바이저 HIGH 2건 반영, 22건 PASS (2026-06-16)
- [x] **Phase 439** 🛰 신뢰 한정 도달성 통합 토폴로지 — `simulation/federation_topology_view.py` Phase 432 메시 연결성 + Phase 428 신뢰를 합쳐, 한 origin 관점에서 연합 목적지를 도달성 품질로 분류하는 읽기 전용 관측 뷰 `FederationTopologyView`(SELF·DIRECT·RELAYED_TRUSTED·RELAYED_RISKY·UNREACHABLE). Phase 433이 *최소 비용 경로 하나*를 고른다면 본 모듈은 *신뢰 중계만 거치는 경로의 존재성*을 답한다(3+ 인스턴스 중계에서만 의미). `avoid_untrusted_route`(알려진 불신만 회피)보다 엄격히 각 중계가 적극 신뢰여야 하는 상보적 포스처. `reachability_class`·`classify`·`trusted_path`·`trusted_reach`·`risky_reach`·`summary`, 무작위성 0·순수 추가, code-reviewer 어드바이저 HIGH 3건 반영, 27건 PASS (2026-06-16)
- [x] **Phase 440** 🛰 신뢰 인지 분산 경로-벡터 장애 우회 수렴 — `simulation/federation_trust_path_vector_failover.py` 연합 라우팅 2×2 격자(홉만/신뢰 인지 × 고정 메시/장애 후 재수렴)의 마지막 빈 칸을 메우는 `TrustPathVectorFailover`. Phase 438(홉만 장애 우회)과 Phase 437(신뢰 인지 고정 메시)을 결합해, 장애 집합을 제거한 살아남은 인접 위에서 Phase 437 신뢰 인지 경로-벡터를 다시 수렴시켜 장애 전후 *신뢰 가중* 경로를 비교: `rerouted`·`lost_routes`·`is_reroutable`·`surviving_path`·`reconvergence_rounds`·`summary`. 핵심 불변식: 무관찰(균일 0.5)이면 Phase 438 장애 분석과 정확히 동일(2×2 격자 모서리), 도달성은 신뢰 무관·Phase 438 동일(신뢰는 *어느 우회로*만 가름). Phase 435 교차 검증·콜드스타트 등가성, 무작위성 0·순수 추가, code-reviewer 어드바이저 HIGH 1건 반영, 27건 PASS (2026-06-16) — **🛰 Federation Operations(421-440) 트랙 완료**
- [ ] **Phase 426-427** 🛰 Federation Operations 잔여 — 2-인스턴스 연합 E2E(Playwright 다중 페이지)·인접 공역 고스트 렌더링(HTML 시뮬레이터 의존, 사용자 환경) / HLC 통합 글로벌 순서 토폴로지는 차기 트랙 후보로 이월
- [x] **Phase 443** 🔬 APF 수렴성 수학 증명 — `simulation/apf_lyapunov.py` + `docs/APF_CONVERGENCE_PROOF.md`. APF 힘 법칙이 보존 포텐셜의 음의 기울기 `F = -∇U`(인력 piecewise 이차/원뿔 C¹ + FIRAS 척력)임을 명시하고, 양정치·radially unbounded Lyapunov 후보로 과감쇠 흐름 `dU/dt = −‖∇U‖² ≤ 0` + LaSalle 전역 수렴(국소 최소·속도 증폭 비보존항 한계 명시)을 형식 문서화. `apf.py` 무수정 순수 추가. code-reviewer 어드바이저 HIGH 2건 반영(속도 증폭 비보존성·데드밴드 정합). 16건 PASS (2026-06-16)
- [x] **Phase 447** 🔬 시나리오 fuzzing — `tests/e2e/test_simulator_fuzz.py` NFZ·ATC·SORA 140케이스 (2026-06-12)
- [x] **Phase 448** 🔬 속성 기반 테스트 — `tests/test_property_telemetry.py` Hypothesis 1,150+ 케이스 (2026-06-12) · **시뮬 코어 불변식 확장(2026-06-16)**: `tests/test_property_deconflict.py` 4D 경로 충돌 감지 코어 `PathDeconflict` 9개 불변식(결정성·삽입순서 무관·보간 볼록성/클램프·충돌 술어 일관·시각 정렬·수직 분리·단일/동일 경로, 1,170+케이스) + `tests/test_scenario_fuzzer_property.py` Phase 447 적대적 퍼저 6개 불변식(스키마 보존·입력 불변성·시드 결정성·분포 재정규화·route 순서·adversarial 단방향 편향, 1,350케이스). code-reviewer 어드바이저 반영, 15건 PASS
- [x] **Phase 449** 🔬 시뮬-실측 갭 모델 — `src/training/sim_real_gap.py` Domain Randomization 파라미터 자동 보정, 7건 PASS (2026-06-15)
- [x] **Phase 441** 🔬 5계층 안전망 TLA+ 명세 — `specs/SafetyNetPriority.tla` + `docs/SAFETY_NET_TLA_SPEC.md` + `simulation/safety_net_invariant.py`. 안전 계층 우선순위 단조성 불변식을 TLA+ 명세 + Python 유한 모델 검사기로 재현(위반 시 반례 최단 경로). 무작위성 0 (2026-06-17, PR #352 흡수)
- [x] **Phase 442** 🔬 ATC 핸드오프 데드락 부재 모델 체킹 — `simulation/handoff_model_checker.py`. 관제권 핸드오프 FSM 도달 상태 BFS 전수 탐색으로 단일 관제권 불변식 + 교착 부재 증명. code-reviewer 어드바이저 반영. 무작위성 0 (2026-06-17, PR #353 흡수)
- [x] **Phase 444** 🔬 CBS 완전성·최적성 조건 정리 — `simulation/cbs_optimality.py` + `docs/CBS_COMPLETENESS_OPTIMALITY.md`. 허용 휴리스틱·분기 건전성·A* 비용 최적성을 독립 BFS 기준해로 검증 + `cbs.py` 보장/완화 정직 공시. code-reviewer 어드바이저 HIGH 2건 반영(BFS forbidden 검사·타임아웃 한계 공시) + 회귀 1건. 무작위성 0 (2026-06-17, PR #351·#352 흡수)
- [x] **Phase 445** 🔬 불확실성 정량화 — `simulation/uncertainty.py` Monte Carlo 신뢰구간 자동 리포트. 코드·테스트 main 적재 완료, 추적 정정 시 16건 PASS 재검증 (2026-06-17)
- [x] **Phase 446** 🔬 충돌 해결률 검정력 분석 — `simulation/power_analysis.py` 충돌 해결률 차이 검정의 검정력·표본수 산출. 15건 PASS 재검증 (2026-06-17)
- [x] **Phase 450** 🔬 재현성 10년 보장 — `requirements.lock.txt`·`Dockerfile.reproducible`·`scripts/independent_reproduction.sh`·`docs/REPRODUCIBILITY.md` 의존성 핀 + 컨테이너 다이제스트 고정 인프라 완비 (2026-06-17)
- [~] **Phase 451-460** 🔬 Formal & Research Frontier — RL 일반화 연구·인증 가능 ML 조사 (451 ✅ EASA 신뢰 가능 AI 적합성 자가 평가 `simulation/easa_ai_conformance.py`, 33% 정직 공시; 452-460 잔여)
- [x] **Phase 466** 🏛 텔레메트리 JSON Schema 공개 + 검증기 — `docs/schemas/telemetry.schema.json` Draft-07 + ws_bridge 정합 회귀 (2026-06-12), **검증기** `simulation/telemetry_validator.py`(`validate_telemetry`, jsonschema 정본/순수 파이썬 폴백 이중 경로 동일 판정, CLI `--example`, 37건 PASS) 추가 완료 (2026-06-17)
- [x] **Phase 469** 🏛 정책 영향 시뮬레이션 — `simulation/policy_impact.py`. 규제 파라미터(이격·고도 상한) 변경의 공역 용량 영향을 결정적 해석 모델(육각 충전 × 고도층)로 정량화·자동 비교(`compare_policies`). 이격 50→70m = 용량 −49%. 정적 기하 용량 상한임 정직 공시. code-reviewer 어드바이저 HIGH 2·MEDIUM 3 반영. 33건 PASS (2026-06-17)
- [x] **Phase 465** 🏛 공역 통합 시뮬레이션 표준 시나리오 셋 (10종 공개) — `simulation/standard_scenarios.py` + `config/scenario_params/nominal_baseline.yaml` + `docs/standards/SDACS_BENCHMARK_SUITE.md`. 도구 간 교차 벤치마크용 공개 표준 스위트 `SDACS-SBS-10` 큐레이션(통제 축 10종 상호 배타, 정의는 기존 YAML SSoT 무복제). 10종 전부 `scenario_schema` 적합 결정적 재검증 + JSON 매니페스트(`primary_kpi_in_criteria` 괴리 플래그). code-reviewer 어드바이저 HIGH 3 반영. 18건 PASS (2026-06-17)
- [x] **Phase 463** 🏛 K-드론 시스템 고도화 정책 제안서 (국토부 제출 형식) — `simulation/k_drone_policy_proposal.py` + `docs/standards/K_DRONE_POLICY_PROPOSAL.md`. 국토교통부 「드론활용촉진법」 §6 드론산업기본계획 정렬 정책 제안서가 정부 제출 형식의 필수 섹션(8종)을 갖췄는가를 결정적으로 판정하는 자문 게이트. 핵심은 *준비도*(필수 섹션 작성·증거 디스크 실재)와 *제출 상태*(외부 절차 의존)를 **독립** 으로 분리 — 전 섹션 작성 완료여도 현 상태 `submission_status = NOT_SUBMITTED` 정직 공시(준비 완료 ≠ 제출). 정직성 결속: `DRAFTED` 섹션은 반드시 실재 증거 산출물 인용·`MISSING` 은 인용 금지(작성 주장만으로 부족, 증거 부재 시 가중 0). 현 리포 판정 `READY_FOR_REVIEW (100%)`·제출 `NOT_SUBMITTED`. 자매 462(외부 ISO 추적)·470(SDACS 발신 기고)와 경계 분리. 무작위성 0·부수효과 0·기존 모듈 무수정 순수 추가. CLI(`--matrix`·`--report`·`--gaps`·`--submission`). code-reviewer 어드바이저 HIGH 2(OUTLINED 증거 공허 참 점수 인플레 차단·빈 레지스트리 READY 오선언 차단)·MEDIUM 1 반영. 49건 PASS (2026-06-21)
- [x] **Phase 464** 🏛 군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구 — `simulation/swarm_safety_standard.py` + `docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md`. 군집 안전 기준 백서의 *기계 검증 골격*: 5계층 안전망(L1 APF→L5 UTM)의 각 계층 안전 주장이 선적된 산출물(형식 증명·모델 검사·ablation)로 입증되는가를 결정적으로 감사. 백서 산문이 유일 출처(SSoT)이고 모듈은 인용 산출물의 *디스크 실재* 만 감사(지표 재계산 0, 중복 없음). 정직성 결속: 인용 근거 전부 실재+실행/형식 근거 1개↑이면 SUBSTANTIATED, 일부만/문서만이면 PARTIAL, 부재면 UNSUBSTANTIATED(거짓 입증 차단). 임계는 모두 proposed·실 비행 안전 아닌 산출물 실재 입증임 정직 공시. 현 리포 5계층 전부 SUBSTANTIATED·횡단 근거 5/5. 자문, 부수효과 0·무작위성 0·기존 파일 무수정 순수 추가. code-reviewer 어드바이저 HIGH 2·MEDIUM 3·LOW 3 반영. 51건 PASS (2026-06-21)
- [x] **Phase 468** 🏛 대학 캡스톤 표준 커리큘럼 제안 (GENESIS 383 확장) — `simulation/capstone_curriculum_standard.py` + `docs/standards/CAPSTONE_CURRICULUM_STANDARD.md`. SDACS 를 워크드 예제로 삼는 15주 학부 캡스톤 표준 커리큘럼 제안서가 (1) 주차별 강의 자료 완비도 **와** (2) 한국공학교육인증원(ABEEK KEC2015) 프로그램 학습성과 커버리지를 동시 충족했는가를 결정적으로 판정하는 자문 게이트. 자매 463(단일 정책 제안서 섹션 완비도, 단일 차원)과 달리 *두 차원 교차 검증* — 모든 단원이 작성돼도 필수 학습성과(PO1·2·4·5·6) 하나가 어느 단원에도 매핑 안 되면 NOT_READY(교차 불변식, 463 에 없음). 정직성 결속: `DRAFTED` 단원은 실재 강의 자산 인용·`MISSING` 은 인용 금지, 거짓 커버 금지(증거 부재 DRAFTED 는 커버 불인정). *준비도*(표준 제안)와 *채택 상태*(외부 대학·ABEEK)는 **독립** — 전 단원 작성돼도 현 상태 `adoption_status = NOT_PROPOSED` 정직 공시. 현 리포 판정 `PARTIAL (95%)`(U09 논문 단원 OUTLINED — 실측 그래프 의존, 기존 P707 잔여와 정합)·15/15주 커버·필수 학습성과 5/5 커버. 자문, 부수효과 0·무작위성 0·기존 파일 무수정 순수 추가. CLI(`--matrix`·`--report`·`--gaps`·`--coverage`·`--adoption`). code-reviewer 어드바이저 반영. 59건 PASS (2026-06-21)
- [x] **Phase 471** 🏛 KS 국가표준 제안 적합성 게이트 — `simulation/ks_standard_proposal.py` + `docs/standards/KS_STANDARD_PROPOSAL_GATE.md`. KS 제안 1건이 KATS 접수에 필요한 제안 요건 6종(산업표준화법 시행령·WTO/TBT §2.4·KS 운영요령 근거) 충족을 결정적 게이트로 판정. 판정 우선순위(CRITICAL UNMET→NOT_READY)·`POLICY_MATRIX` 6칸 테스트 일치 강제·자문(부수효과 0)·무작위성 0. 현 후보 `NOT_READY (50.0%)` 정직 공시(KS-04 중복성 검토 결격). 27건 PASS (2026-06-21)
- [ ] **Phase 473-480** 🏛 Standards & Policy 잔여 — 국제 워킹그룹 의견서 잔여 2건 (461-472 ✅ 전부 완료)
- [x] **Phase 485** ♾️ 데이터 마이그레이션 도구 — `simulation/scenario_migration.py`. 시나리오 포맷의 역사적 변종(`*_min`/`*_s`·`total_drone_count`/`base_drone_count`/`base_traffic`)을 canonical v2.0(초·단일 `drone_count`·`schema_version` 스탬프)으로 정규화하는 결정적·멱등 버전 변환기. `multi_city` 의 러너 미인식 `total_drone_count` 를 `drone_count` 로 복원. 출력은 `scenario_schema` 계약 경고 없이 충족. code-reviewer 어드바이저 HIGH 3 반영. 33건 PASS (2026-06-17)
- [x] **Phase 486** ♾️ 연 1회 건전성 리허설 자동화 — `scripts/independent_reproduction.sh` (회귀·md5·JS·API 게이트 통합, 2026-06-12) + `simulation/rehearsal_cadence.py` + `docs/standards/HEALTH_REHEARSAL_CADENCE_POLICY.md` (2026-06-19). 신규 컨테이너 독립 재현 하니스가 *언제 다시 필요한가*(연 1회 365일 + 예고 30일 + 유예 30일 케이던스)와 *온전한가*(4개 하니스 자산 실재)를 결정적 정책으로 명문화(Phase 481/484/488/489 자매 패턴). `assess` 우선순위: 하니스 손상→REVIEW·기록 없음→RUN_NOW·미래 날짜→REVIEW·비-PASS→RUN_NOW·그 외 케이던스 등급. `LAST_REHEARSAL` 스냅샷(2026-06-19 일일 점검 = PASS)으로 현 상태 `WITHIN_CADENCE` 정직 공시(일일 점검이 연 1회보다 잦음 반영). 자문, 부수효과 0·무작위성 0. `POLICY_MATRIX` 8칸 일치 강제. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영. 41건 PASS
- [x] **Phase 481** ♾️ 의존성 자동 갱신 회귀 게이트 정책 — `simulation/dependency_gate.py`. 적체 Dependabot 갱신 PR 을 회귀 통과 시 자동 머지/리뷰/차단으로 가르는 결정적 정책(자문, 부수효과 0). 44건 PASS (2026-06-19)
- [x] **Phase 488** ♾️ 보안 장기 지원 — `simulation/cve_response_policy.py` + `docs/standards/CVE_RESPONSE_SLA_POLICY.md`. CVE 한 건의 대응 긴급도·SLA·핀 갱신 필요를 결정적 정책으로 명문화(Phase 481 자매편). CVSS v3.1 정성 등급·SECURITY.md 기준선(HIGH ack 3/해결 14일) 준수·dev 노출 1단계 강등·`pin_refresh_required` 정직성 결속. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 3 반영. 45건 PASS (2026-06-19)
- [x] **Phase 489** ♾️ 아카이브 이중화 — `simulation/archive_redundancy.py` + `docs/standards/ARCHIVE_REDUNDANCY_POLICY.md`. "단일 실패점 없이 충분한가"를 결정적 정책으로 명문화. 보관처별 식별자 형식 검증·위치자 없는 예치 주장 VERIFIED 불인정·독립성 custodian 단위 집계(독립 ≥2곳+양차원→REDUNDANT). `shipped_registry()` 는 DOI 미발급 현 상태를 `AT_RISK` 로 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 1 반영(+일원화 검토 DOI 핸들 오인 정밀화). 50건 PASS (2026-06-19)
- [x] **Phase 484** ♾️ Electron LTS 추적 정책 — `simulation/electron_lts_policy.py` + `docs/standards/ELECTRON_LTS_TRACKING_POLICY.md`. 데스크탑 Electron 런타임이 보안 지원 창(최신 3 major)을 언제 벗어나는가를 결정적 정책으로 명문화(Phase 481 자매편). `package.json` 실측 핀(`^39.8.5`=39)과 상류 최신 스냅샷(42, Dependabot #277 증거) 비교로 현 상태 `UPGRADE_NOW (EOL, lag=3)` 정직 공시 — 현 빌드 타깃이 보안 백포트 끊긴 EOL 임을 표면화. 32→39 표류 교훈 결속. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 4·LOW 4 반영. 56건 PASS (2026-06-19)
- [x] **Phase 487** ♾️ 유지보수자 승계 규약(거버넌스 BDFL→위원회) — `simulation/governance_succession.py` + `docs/standards/MAINTAINER_SUCCESSION_PROTOCOL.md`. "원저자를 넘어 위원회로 승계될 준비가 됐는가"를 결정적 정책으로 명문화. 연속성 보유자=활성+머지권한+관리자접근 *동시* 보유자만 집계(bus factor)·emeritus 권한 잔존해도 미집계·문서 완비가 1인 구조를 대체 못함(BUS_FACTOR_RISK 고정)·위원회 정족 ≥3인+문서완비→COMMITTEE_READY. `shipped_maintainers()` 는 캡스톤 원저자 1인 현 상태를 `BUS_FACTOR_RISK` 로 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 1 반영. 48건 PASS (2026-06-19)
- [x] **Phase 490** ♾️ 디지털 유산 선언 — 10년 후 재현 가능성 체크리스트 — `simulation/legacy_readiness.py` + `docs/standards/DIGITAL_LEGACY_CHECKLIST.md`. 8기준×7차원 결정적 준비도 판정(CRITICAL 미충족→NOT_READY), 아카이브 차원은 Phase 489 게이트 위임. 현 리포 `NOT_READY (58.8%)` 정직 공시(LICENSE 전문 부재·DOI 미발급). 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영. 30건 PASS (2026-06-19)
- [x] **Phase 482** ♾️ 브라우저 API 폐기 감시 — `simulation/browser_api_watch.py` + `docs/standards/BROWSER_API_DEPRECATION_WATCH.md`. HTML 시뮬레이터 의존 브라우저 API 의 폐기 위험을 (표준화 상태 × 의존 방식) 2차원 결정적 카나리로 판정(Phase 481/484/488/489 자매). 카나리는 실험/폐기 API 의 *필수 의존*(FRAGILE·BREAKING)만 발화 — feature-detect 폴백이면 안전. 실측 8 API 스냅샷 판정 결과 현 리포 `RESILIENT`(필수 의존 전부 baseline-wide·실험 API WebGPU/WebXR 는 전부 폴백) 정직 공시. 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 3·LOW 3 반영. 41건 PASS (2026-06-19)
- [x] **Phase 483** ♾️ Three.js 메이저 업그레이드 리허설 — `simulation/threejs_upgrade_audit.py` + `tests/test_threejs_upgrade_audit.py`. 웹 시뮬레이터가 의존하는 벤더 Three.js(현 `vendor/three/three.module.js` REVISION 162)를 다음 메이저로 올릴 때 사라질 심볼을 결정적 감사로 표면화. 시뮬레이터 사용 `THREE.*` 심볼을 `three.module.js` 의 `export { ... }` 블록과 직접 대조(추측 0) → `BREAK`(export 부재) > `REVIEW`(워치리스트 사용) > `GREEN`. 워치리스트 정직성 게이트가 추측성 항목을 차단(권위 근거: 공식 `MIGRATION.md`). 현 리포 판정 GREEN(사용 47 심볼 전부 r162 export + OrbitControls addon 검증). 자문, 부수효과 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 4·LOW 3 반영. 25건 PASS (2026-06-20)
- [x] **Phase 491** ♾️ 세대 이양 검토 게이트 — `simulation/track_handover_policy.py` + `docs/standards/GENERATIONAL_HANDOVER_POLICY.md`. ODYSSEY 거버넌스 게이트 #4("491+ 신규 트랙은 차세대 주도, 현 세대는 리뷰만")를 결정적 정책으로 명문화. 차세대(2027+ 기수) 제출 신규 트랙 제안의 이양 수용 여부를 `assess_handover`(서로소 4단계 우선순위: 차세대 소유자 부재→REJECT 구조적 결격·현 세대 리뷰 미완→DEFER·보완형 결함(헌장·범위 중복·sandbox)→REVISE·그 외→ACCEPT)로 판정. **소유자가 사람을 대체 못함**(헌장·리뷰 충족여도 소유자 없으면 우선 REJECT). `POLICY_MATRIX`(소유자×리뷰×결함없음 8칸) 테스트 전수 일치 강제. `shipped_proposals()` 는 차세대 기수 미형성·제안 0 현 상태를 `AWAITING_PROPOSALS` 로 정직 공시. 자문, 부수효과 0·무작위성 0. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영. 34건 PASS (2026-06-20, 미머지 적체 draft PR #394 일원화)
- [x] **Phase 492** ♾️ 차세대 트랙 공모·선정 정책 — `simulation/track_handoff_readiness.py` + `docs/standards/NEXTGEN_TRACK_HANDOFF_POLICY.md`. Phase 491 이양 게이트의 다음 단계. *공모 전체에서 적격 제안을 가려 하나를 선정* 하는 문제를 결정적 정책으로 명문화(491 = 개별 제안 이양 수용 가능성, 492 = 적격 제안 간 우선순위 — 독립 기준). `assess_proposal`(주체 지정 × 범위 버킷(≥10 Phase 트랙 케이던스) × 필수 기준(트랙 헌장·검증 가능한 성공 기준·**원저자 독립성**(Phase 487 bus factor 정합)·선행 의존성) → ELIGIBLE/NEEDS_WORK/REJECTED) + `select_track`(적격 제안을 부가 강점 점수 → `sha256(proposal_id)` 안정 해시 동률 분리로 결정적 선정 → HANDOFF_READY/NO_ELIGIBLE/AWAITING_PROPOSALS). `POLICY_MATRIX` 12칸 일치 강제. `shipped_proposals()` 는 제안 0 현 상태를 `AWAITING_PROPOSALS` 로 정직 공시. 자문, 부수효과 0·무작위성 0. code-reviewer 어드바이저 HIGH 1·MEDIUM 2·LOW 1 반영(score 단일 산출·이유 문자열 공백·`dataclasses.replace`·ELIGIBLE 이유 검증). 48건 PASS (2026-06-20)
- [x] **Phase 500** ♾️ Centennial 선언 — `simulation/centennial_declaration.py` + `docs/standards/CENTENNIAL_DECLARATION_POLICY.md`. Continuum 트랙(481-500)·전체 500-Phase 프로그램의 *종착 선언*. "원저자·현 세대를 넘어 100년 단위로 살아남을 준비가 됐는가"를 결정적 종합 게이트로 명문화. 새 기준을 발명하지 않고 **네 기둥**(Phase 490 유산 준비도 READY · 489 아카이브 이중화 REDUNDANT · 487 거버넌스 승계 COMMITTEE_READY · 492 세대 이양 집행 HANDOFF_READY)을 *호출만* 함(DRY — 판정 로직 복제 0). all-or-nothing: 한 기둥이라도 미충족이면 **NOT_DECLARED**(`progress` 는 정직 공시용일 뿐 선언 불앞당김). `shipped` 실측 → 네 기둥 전부 미충족(LICENSE 전문·DOI·위원회·2027+ 기수 미형성)으로 현 상태 `NOT_DECLARED (0.0%)` 정직 공시 — 잔여 100년 조건을 그대로 표면화. 자문, 부수효과 0·무작위성 0·기존 파일 무수정 순수 추가. code-reviewer 어드바이저 HIGH 2(override 시 실제 게이트 건너뜀·핸드오버 기둥 위임 Phase 정합)·MEDIUM 1·LOW 1 반영. 27건 PASS (2026-06-21)
- [ ] **Phase 493-499** ♾️ Continuum 잔여 — 차세대 트랙 실 공모·선정·이양 실행 *(2027+ 차세대 기수 의존)*

---

*2026-06-21 (일일 점검 + 적체 드래프트 일원화) — **ODYSSEY Continuum 종착(491·492·500) + Standards 트랙(461·463·464) 6 Phase 일원화**: 신규 세션 컨테이너에서 의존성 신규 설치 후 독립 재현 GREEN. 금일 병행 세션이 작업 브랜치(`a4510ef`)와 동일 베이스로 만든 미머지 적체 draft PR #410·411·412·413·414 를 발견 — #413(Phase 491·492·500 Continuum 종착 + 461 ASTM F38 + 464 안전 백서)은 작업 브랜치의 클린 fast-forward 상위집합이라 충돌 없이 일원화하고, #414(Phase 463 K-드론 정책 제안서 게이트)를 그 위에 병합(문서 충돌만 수동 정합). 6 Phase 전부 결정적 정책·자문·부수효과 0·무작위성 0·기존 파일 무수정 순수 추가, 각 code-reviewer 어드바이저 반영. **이로써 ODYSSEY Continuum(481-500) 코드화 가능 칸 전부 종착**(493-499 는 2027+ 차세대 기수 의존). **점검 발견(사용자 결정 필요)**: ① 일원화 완료된 draft PR #410·411·412·413·414 는 본 통합 후 close 권고. ② **Dependabot 14건 적체**(#267-279·#367) — Phase 484 가 현 electron 핀을 EOL 공시(#277 우선). ③ **GitHub 보고 취약점 4건**(2 high·2 low) 미해소 — 전부 사용자 승인 필요.*

*2026-06-20 (일일 점검 51차 + 적체 드래프트 일원화) — **Continuum 트랙 미머지 적체 6칸 전면 일원화 (Phase 481-490 완결)**: 45차(PR #385, `40d8673`) 머지 후 작업 브랜치 클린 베이스 확인. 신규 세션 컨테이너에서 적체 draft PR **#386(490)·#387(487)·#388(484·487·490)·#389(486)·#390(482·484·486·487·490)·#391(483)** 의 코드/테스트/표준문서를 단일 작업 브랜치로 통합. PR #390 이 482·484·486·487·490 을 누적 스택으로 보유했고 #391 이 483 을 별도 보유 — 둘을 합쳐 Continuum 비-이양 잔여 6칸(482·483·484·486·487·490)을 전부 확정 → **Phase 481-490 완결**(491-500 = 차세대 이양·Centennial 만 잔여). 통합 6개 신규 모듈 단위 **241건 PASS**(browser_api_watch 41 + electron_lts_policy 56 + governance_succession 48 + legacy_readiness 30 + rehearsal_cadence 41 + threejs_upgrade_audit 25). 전부 결정적 정책·자문·부수효과 0·기존 파일 무수정 순수 추가. **점검 발견(사용자 검토 필요)**: 열린 PR 22건 적체(Dependabot 13건 #267-279 + #283 perf + #280 draft Phase 207 + 본 일원화로 흡수된 #386-391 6건) · GitHub 보고 취약점 4건(2 high·2 low) 미해소 — 머지·triage·취약점 패치는 사용자 승인 필요. 흡수된 #386-391 은 본 PR 머지 후 close 권고.*

*2026-06-19 (일일 점검 49차 + 적체 드래프트 일원화) — **신규 컨테이너 독립 재현 GREEN + Continuum Phase 486 신규**: 신규 세션 컨테이너에서 의존성 신규 설치 후 적체 드래프트 #388(Phase 484·487·490 일원화, #386·#387 흡수)을 작업 브랜치에 통합하고 전체 회귀 **5,840 pass / 280 skip / 0 fail**(177.83s, 84.98% cov) 독립 재현 GREEN. 이어 Continuum 트랙의 비브라우저 잔여 칸 **Phase 486(연 1회 건전성 리허설 자동화)** 를 신규 구현 — 독립 재현 하니스의 케이던스(연 1회+예고/유예)와 무결성을 결정적으로 판정하는 자문 정책(`simulation/rehearsal_cadence.py`, 부수효과 0). 통합 시 발견한 문서 불일치(ODYSSEY 플랜에서 487·490 미표시) 정정. code-reviewer 어드바이저 HIGH 2·MEDIUM 2·LOW 2 반영, 신규 41건 PASS. **점검 발견(보고)**: 열린 PR 18건 적체 지속(Dependabot 13 + #283 perf + #280 draft Phase 207 + 일원화 대상 #386·#387·#388) · GitHub 보고 취약점 4건(2 high·2 low) 미해소 — 머지·triage 는 사용자 승인 필요.*

*2026-06-19 (일일 점검 48차 + 적체 드래프트 일원화) — **신규 컨테이너 독립 재현 GREEN + Continuum 3칸 일괄 구현·일원화**: 신규 세션 컨테이너에서 의존성 신규 설치 후 baseline(main `40d8673` + 적체 드래프트 #386·#387 통합) 전체 회귀 **5,747 pass / 280 skip / 0 fail**(232.78s, 84.92% cov) 독립 재현 GREEN. 미머지 적체 드래프트 **#386(Phase 490)·#387(Phase 487)** 의 코드/테스트/문서(서로소 파일)를 본 작업 브랜치에 통합하고, 로드맵 Continuum 트랙에서 코드 작업거리가 남은 비브라우저 칸 **Phase 484(Electron LTS 추적 정책)** 를 Phase 481/488/489 자매 패턴(결정적 정책·부수효과 0·자문)으로 신규 구현. 484 는 현 핀 Electron 39 가 상류 최신 42 대비 EOL(보안 백포트 종료)임을 정직 공시. 신규 56건 포함 통합 후 전체 GREEN. **점검 발견(보고)**: 열린 PR 18건 적체 지속(Dependabot 13 + #283 perf + #280 draft + 일원화 대상 #386·#387) · GitHub 보고 취약점 4건(2 high·2 low) 미해소 — 머지·triage 는 사용자 승인 필요. Phase 481 `dependency_gate`·488 `cve_response_policy`·484 `electron_lts_policy` 게이트 기준 일괄 검토 권장.*

*2026-06-14 (일일 점검 + 머지 병목 해소) — **신규 컨테이너 독립 재현 GREEN + 적체 PR 정리**: 신규 세션 컨테이너에서 의존성 설치 후 main(`32cdfd2`) baseline 회귀 **4,089 pass / 280 skip / 0 fail**(83.97%) 재현. 점검 시점 열린 PR **30건**(머지 병목 — Phase 307×5·304×2·445×3·207×2 등 중복 누적)을 정밀 triage. clean·CI green·중복 아닌 Phase 3건을 머지: **#310 ODYSSEY Phase 421**(인스턴스 간 디스커버리, ASTM F3548-21 DSS 결정적 모델)을 main 직접 머지(`8be9a3c`, main CI·Canonical Hash·Security 전부 success), **#309 GENESIS Phase 307**(ARAIB 사고 보고 양식)·**#308 ODYSSEY Phase 467**(ICAO Annex 13 사고 조사 변환기)은 README/CHANGELOG append 충돌만 있어 본 작업 브랜치에 통합·해소. 통합 후 전체 회귀 **4,147 pass / 280 skip / 0 fail**(84.06%, +58 신규). 잔여 적체 PR(중복·dirty·dependabot)은 후속 정리 대상으로 보고.*

*2026-06-12 (종합 감사) — **전체 문서·소스 정합성 감사 + Track G 신설**: 라이브 페이지 실측으로 `_sdacs` API **407 항목** 확정(기존 문서 391 과소 표기 정정 — 분류 404 = 93/98/110/103 + 헬퍼 3), `docs/SDACS_API.md` maturity 컬럼 포함 재생성, `docs/sdacs.d.ts` 407 멤버 재생성, README·VERSION.md 수치 동기화(시뮬레이터 11,836 line). 분석 뷰 Q2 동적 NFZ overlay + NFZ 레이어 토글 연동 + sub-km 비행거리 표시(PR #265). TRANSCENDENCE Phase 201-300을 Track G로 로드맵 공식 편입, 2026 H2 마스터플랜(`docs/MASTER_PLAN_2026H2.md`) 수립.*

## Contributing / 기여

이 프로젝트는 목포대학교 캡스톤 디자인 프로젝트입니다.
기여를 원하시면 Issue를 통해 제안해 주세요.

*2026-06-13 (일일 점검 + Phase 207 배지 드리프트 해소) — **신규 컨테이너 독립 재현 GREEN**: 의존성 신규 설치 후 전체 회귀 **4,065 pass / 267 skip / 0 fail** (545.46s) 독립 재현 — 본 세션 +7 배지 테스트 포함, 커버리지 게이트(≥80%) 통과. **발견·수정**: Phase 207은 "완료"로 표기됐으나 `docs/badges/maturity.svg`가 수작업 유지라 `prod 89`로 드리프트(라이브 실측·`SDACS_API.md`는 production **90**). `scripts/extract_sdacs_api.py`에 `render_badge_svg()` 결정적 생성기 추가 → 재생성·CI `--check` 게이트에 배지 정합성 편입, 배지 `prod 90` 정정. 잔여 미체크는 사용자 환경 의존(P755 창업·실기 검증·IROS 투고·실측 그래프).*

*2026-06-12 (18차 재현) — **일일 점검 (신규 컨테이너 독립 재현, main `843aec9` 기준)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (388.13s, 커버리지 83.93%) 독립 재현 GREEN — 8~17차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `843aec9` — 17차 기준 `c2649ad`에서 PR #261 머지로 전진), main 최신 커밋 CI·Security·Canonical Hash·Pages 전 워크플로우 success(actions API 재조회). `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈·PR 0건, 보조 로드맵(`MASTER_TODO_ATC.md`) 미체크 0건. `ROADMAP.md`·`ULTRA_PLAN.md`·`presentation_remaining_tasks.md` 잔여 미체크는 전부 사용자 환경 의존(P755 창업·슬라이드 실물·브라우저 검증·실 하드웨어 비교). 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-12 (17차 재현) — **일일 점검 (신규 컨테이너 독립 재현, main `c2649ad` 기준)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (309.64s, 커버리지 83.93%) 독립 재현 GREEN — 8~16차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `c2649ad` — 15차 기준 `91a4fcc`에서 PR #259 머지로 전진), main 최신 커밋 CI·Security·Canonical Hash 전 워크플로우 success(actions API 재조회). `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈 0건, 보조 로드맵 미체크 코드 작업거리 0건. 같은 날 동일 main HEAD `c2649ad` 기준 16차를 기록한 미머지 드래프트 PR #260을 본 점검(17차)으로 superseded 정리. 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-12 (15차 재현) — **일일 점검 (신규 컨테이너 독립 재현, main `91a4fcc` 기준)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (503.23s, 커버리지 83.93%) 독립 재현 GREEN — 8~14차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `91a4fcc` — 14차 기준 `e1aa87c`에서 PR #258 머지로 전진), main 최신 커밋 CI·Security·Hash·Pages 전 워크플로우 success. `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈·PR 0건, 보조 로드맵 미체크 코드 작업거리 0건(`SIMULATOR_HYPER_PLAN` 데모 영상은 MediaRecorder 녹화 기능이 CIN-4에 이미 구현 → 영상 산출만 브라우저 세션 의존). 환경 함정: `dash`·`pandas` 미설치 시 16건 ModuleNotFound → `requirements.txt` 전체 설치 + `pytest<9` 정렬 필요(CHANGELOG 참조). 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-12 (14차 재현) — **일일 점검 (신규 컨테이너 독립 재현 + 중복 점검 PR #257 정리)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (407.63s, 커버리지 CI 기준 83.93%) 독립 재현 GREEN — 8~13차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `e1aa87c`), main 최신 커밋 CI·Security·Hash·Pages 전 워크플로우 success. `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈 0건, 보조 로드맵 미체크 코드 작업거리 0건. 같은 날 동일 4,057 검증을 기록한 미머지 드래프트 PR #257(13차)을 본 점검(14차)으로 superseded 정리. 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-11 (8차 재현) — **일일 점검 (신규 컨테이너 독립 재현 + 중복 점검 PR 정리)**: 신규 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (531s, 커버리지 83.93%) 독립 재현 GREEN — 직전 재현들과 동일 수치. 환경 함정(PATH의 uv 격리 `pytest 9.0.2`가 conftest import 실패 유발 → `python -m pytest` 8.4.2로 우회)은 CHANGELOG 참조. 같은 날 동일 검증을 기록한 미머지 중복 점검 PR #250(6차)·#251(7차)을 본 점검으로 superseded 정리. main 최신(`bba6815`) CI·Security·Hash·Pages 전 워크플로우 success. 코드 실 TODO·열린 이슈·보조 로드맵 미체크 0건. 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-11 (재점검) — **일일 점검 (신규 컨테이너 독립 재현)**: 신규 클론 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (커버리지 83.93%) 독립 재현 GREEN. main CI 전 워크플로우 success. 코드 내 실 TODO 0건. 로드맵 99.5% 유지 — 잔여 4항목(P755 창업·Track A 실기·P707 실측 그래프·P709 IROS 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.*

*Last updated: 2026-06-11 — **일일 점검 + 백로그 통합(#240 + #232)**: 의존성 신규 설치 후 전체 회귀 독립 재현 **GREEN**. 잔여 코드 작업 2건을 단일 브랜치로 통합. (1) **P741 Raft quorum 정정**(#240) — `airspace_controller_ha.py` `replicate()` 를 quorum 인식으로 정정(피어 없는 단일 노드만 즉시 커밋, 피어 존재 시 조기 커밋 방지하고 `RaftCluster.propose` 에 과반 복제 위임) + `start()` TODO를 결정론적 드라이버(`RaftCluster.tick`) 위임 명시로 대체, 회귀 테스트 2건 추가. (2) **STELLAR Phase 51 시드 완성**(#232) — 유일 잔여 시뮬레이터 gap이던 Phase 51을 상태 기반 결정적 권고 사이클(`stellar51Recommend`/`Tick`/`Revoke`/`Groups`)로 완성, 4개 군집 사본 md5 동기화 + E2E 1건. 시뮬레이터 STELLAR Phase 52-100은 canonical 이름으로 main에 이미 구현됨을 확인 → PR #124(AR)·#128(stellar52~55)·#239(raft 주석 only) **superseded**. 잔여(사용자 환경 의존): Track A 실기 검증, P707 실측 그래프, P709 IROS 투고, P755 창업.*

*2026-06-09 — **일일 점검 + PR 백로그 정리**: 전체 회귀 3,970 pass / 254 skip / 0 fail (GREEN). 코드 내 마지막 실 TODO 4건을 머지로 해소 — #205(P707 논문 §2-§7) main 직접 머지 + #204(onboard yaw)·#206(P736 RL env 실동작)·#207(P741 Raft §5.3 catch-up)을 본 브랜치로 통합(README changelog 충돌만 수동 해소). obsolete PR 17건(CLI `--output` 중복 13 + 빈 diff 3 + P711 구버전 #138) close. 잔여 (사용자 환경 의존): Track A 실기 검증, P707 실측 실험 그래프, P709 IROS 2026 실제 투고, P755 창업. 코드 로드맵 **99.5%** · conflict 마커 0.*
