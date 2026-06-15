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
| **GENESIS** (시뮬 Phase 301-400) | 9% | █░░░░░░░░░░░ | 301·302·304·306·309·381·387·388·389 완료 — 인증 가이드 4종·교육·레거시 |
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
- [ ] **Phase 209-220** — Deprecation Policy·SemVer·production 격상 (12 → 30 API)
- [ ] **Phase 221-240** — Real Validation (WebGPU 실 WGSL·CRDT Yjs·MAVLink SITL·KMA 풍속장)
- [ ] **Phase 241-260** — Multi-User Reality (WS 관제 서버·다중 관제사·TimescaleDB·부하 100명)
- [ ] **Phase 261-280** — Hardware Loop (Pixhawk HITL·Jetson 엣지·RTK·실 비행 데이터셋) *(사용자 HW 의존)*
- [ ] **Phase 281-300** — Academic Impact (IROS 투고·Zenodo DOI·Ablation 자동화·K-UTM 표준 제안)

### Track H — 시뮬레이터 GENESIS (Phase 301-400) · 2026-06-12 수립

> 상세: [`docs/SIMULATOR_GENESIS_PLAN.md`](docs/SIMULATOR_GENESIS_PLAN.md) — *"이것은 세상에 남는가"*

- [x] **Phase 301** 🏭 항공안전법·드론활용촉진법 적합성 매트릭스 — `docs/certification/AIR_SAFETY_ACT_MATRIX.md` (2026-06-12)
- [x] **Phase 302** 🏭 SORA 자동 계산기 — `_sdacs.soraAssess()` JARUS 2.0 결정적 구현, E2E 6건 (2026-06-12)
- [x] **Phase 304** 🏭 KC 전파인증 체크리스트 — `docs/certification/KC_RADIO_CERTIFICATION.md` (2026-06-12)
- [x] **Phase 306** 🏭 RTM 5계층 커버리지 — `docs/certification/RTM_5LAYER_COVERAGE.md` 21건 추적 (2026-06-12)
- [x] **Phase 309** 🏭 조종자 자격증명 매핑 — `docs/certification/PILOT_LICENSE_MAPPING.md` (2026-06-12)
- [ ] **Phase 301·303-320** 🏭 Certification & Compliance — 항공안전법 매트릭스·DO-178C 갭 분석·CSAP 자동화
- [x] **Phase 322** 🌍 `.sdacs-scenario` 스키마 + 검증기 — `simulation/scenario_schema.py` + `docs/schemas/sdacs-scenario.schema.json`, 20건 PASS (2026-06-15)
- [ ] **Phase 321-340** 🌍 Ecosystem & Open Source — 플러그인 SDK·`@sdacs/core` npm·`sdacs-sim` PyPI·v2.0 API 안정화
- [x] **Phase 341** 🏙 목포 해역 실 좌표계 임포트 — `src/applications/mokpo_harbor.py` 해도 기반 NFZ 4종(부두·대교·지형·정박지)·회랑 3종 결정적 배치 + 레이 캐스팅 NFZ 판정·회랑 충돌 검사, 8건 PASS (2026-06-15)
- [x] **Phase 342** 🏙 전남 도서(신안·완도) 의료 배송 거점 DB — `src/applications/jeonnam_island_sites.py` 실 좌표·거점·Haversine ETA, 7건 PASS (2026-06-15)
- [ ] **Phase 341-360** 🏙 Real Deployment — 목포 해역 실 좌표·전남 도서 의료 배송·90일 파일럿 백서
- [x] **Phase 367** 🤖 스웜 자가 치유 — `src/autonomy/swarm_self_healing.py` 결손 드론 임무 자동 재분배, 12건 PASS (2026-06-15)
- [ ] **Phase 361-380** 🤖 Next-Gen Autonomy — 온보드 RL 추론·APF+RL 하이브리드·양방향 디지털 트윈
- [x] **Phase 381** 🎓 교육 모드 — 시뮬레이터 `tutorialStart/Next/Status()` 5단계 (2026-06-12)
- [x] **Phase 387** 🎓 졸업 심사 발표 키트 — `docs/presentation/DEFENSE_KIT.md` (2026-06-12)
- [x] **Phase 389** 🎓 유지보수 최소 모드 — `docs/MAINTENANCE_MINIMAL_MODE.md` (2026-06-12)
- [x] **Phase 388** 🎓 기술 부채 대장 — `docs/TECH_DEBT_LEDGER.md` 자동 생성 (2026-06-12)
- [ ] **Phase 381-387·389-400** 🎓 Education & Legacy — 15주 커리큘럼·졸업 심사 키트·**Phase 400 = Legacy 선언**

### Track I — 시뮬레이터 ODYSSEY (Phase 401-500) · 2026-06-12 수립

> 상세: [`docs/SIMULATOR_ODYSSEY_PLAN.md`](docs/SIMULATOR_ODYSSEY_PLAN.md) — *"이것은 국경과 세대를 넘는가"*

- [x] **Phase 408** 🌏 ICAO 공역 클래스 A-G 매핑 — `docs/certification/AIRSPACE_CLASS_MAPPING.md` + `simulation/airspace_class.py` `classify_airspace()` API 격상 (결정적, 25건 PASS) (2026-06-12, API 2026-06-14)
- [x] **Phase 401·406** 🌏 다국 좌표계·시간대 자동 판정 — `simulation/geo_zones.py` UTM 그리드 존 결정적 판정 + EASA U-space 매핑, 22건 PASS (2026-06-15)
- [ ] **Phase 401-407·409-420** 🌏 Global Expansion — EASA U-space·FAA UTM 정렬·EN 완역
- [x] **Phase 421** 🛰 인스턴스 간 디스커버리 프로토콜 — `simulation/federation_discovery.py` ASTM F3548 DSS 유사 결정적 모델(4D 볼륨 등록·그리드 셀 인덱스·정밀 교차 디스커버리·동기화 대상), 13건 PASS (2026-06-14)
- [ ] **Phase 422-440** 🛰 Federation Operations — 운영 의도 4D 교환·관제권 핸드오버·연합 충돌 해소
- [x] **Phase 447** 🔬 시나리오 fuzzing — `tests/e2e/test_simulator_fuzz.py` NFZ·ATC·SORA 140케이스 (2026-06-12)
- [x] **Phase 448** 🔬 속성 기반 테스트 — `tests/test_property_telemetry.py` Hypothesis 1,150+ 케이스 (2026-06-12)
- [x] **Phase 449** 🔬 시뮬-실측 갭 모델 — `src/training/sim_real_gap.py` Domain Randomization 파라미터 자동 보정, 7건 PASS (2026-06-15)
- [ ] **Phase 441-446·449-460** 🔬 Formal & Research Frontier — TLA+ 안전망 명세·모델 체킹
- [x] **Phase 466** 🏛 텔레메트리 JSON Schema 공개 — `docs/schemas/telemetry.schema.json` Draft-07 + ws_bridge 정합 회귀 (2026-06-12)
- [ ] **Phase 461-465·467-480** 🏛 Standards & Policy — ASTM/ISO 기고·정책 영향 시뮬
- [x] **Phase 486** ♾️ 독립 재현 자동화 — `scripts/independent_reproduction.sh` (회귀·md5·JS·API 게이트 통합) (2026-06-12)
- [ ] **Phase 481-485·487-500** ♾️ Continuum — 의존성 장기 추적·승계 규약·**Phase 500 = Centennial 선언**

---

*2026-06-14 (일일 점검 + 머지 병목 해소) — **신규 컨테이너 독립 재현 GREEN + 적체 PR 정리**: 신규 세션 컨테이너에서 의존성 설치 후 main(`32cdfd2`) baseline 회귀 **4,089 pass / 280 skip / 0 fail**(83.97%) 재현. 점검 시점 열린 PR **30건**(머지 병목 — Phase 307×5·304×2·445×3·207×2 등 중복 누적)을 정밀 triage. clean·CI green·중복 아닌 Phase 3건을 머지: **#310 ODYSSEY Phase 421**(인스턴스 간 디스커버리, ASTM F3548-21 DSS 결정적 모델)을 main 직접 머지(`8be9a3c`, main CI·Canonical Hash·Security 전부 success), **#309 GENESIS Phase 307**(ARAIB 사고 보고 양식)·**#308 ODYSSEY Phase 467**(ICAO Annex 13 사고 조사 변환기)은 README/CHANGELOG append 충돌만 있어 본 작업 브랜치에 통합·해소. 통합 후 전체 회귀 **4,147 pass / 280 skip / 0 fail**(84.06%, +58 신규). 잔여 적체 PR(중복·dirty·dependabot)은 후속 정리 대상으로 보고.*

*2026-06-12 (종합 감사) — **전체 문서·소스 정합성 감사 + Track G 신설**: 라이브 페이지 실측으로 `_sdacs` API **407 항목** 확정(기존 문서 391 과소 표기 정정 — 분류 404 = 93/98/110/103 + 헬퍼 3), `docs/SDACS_API.md` maturity 컬럼 포함 재생성, `docs/sdacs.d.ts` 407 멤버 재생성, README·VERSION.md 수치 동기화(시뮬레이터 11,836 line). 분석 뷰 Q2 동적 NFZ overlay + NFZ 레이어 토글 연동 + sub-km 비행거리 표시(PR #265). TRANSCENDENCE Phase 201-300을 Track G로 로드맵 공식 편입, 2026 H2 마스터플랜(`docs/MASTER_PLAN_2026H2.md`) 수립.*

## Contributing / 기여

이 프로젝트는 목포대학교 캡스톤 디자인 프로젝트입니다.
기여를 원하시면 Issue를 통해 제안해 주세요.

*2026-06-12 (18차 재현) — **일일 점검 (신규 컨테이너 독립 재현, main `843aec9` 기준)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (388.13s, 커버리지 83.93%) 독립 재현 GREEN — 8~17차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `843aec9` — 17차 기준 `c2649ad`에서 PR #261 머지로 전진), main 최신 커밋 CI·Security·Canonical Hash·Pages 전 워크플로우 success(actions API 재조회). `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈·PR 0건, 보조 로드맵(`MASTER_TODO_ATC.md`) 미체크 0건. `ROADMAP.md`·`ULTRA_PLAN.md`·`presentation_remaining_tasks.md` 잔여 미체크는 전부 사용자 환경 의존(P755 창업·슬라이드 실물·브라우저 검증·실 하드웨어 비교). 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-12 (17차 재현) — **일일 점검 (신규 컨테이너 독립 재현, main `c2649ad` 기준)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (309.64s, 커버리지 83.93%) 독립 재현 GREEN — 8~16차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `c2649ad` — 15차 기준 `91a4fcc`에서 PR #259 머지로 전진), main 최신 커밋 CI·Security·Canonical Hash 전 워크플로우 success(actions API 재조회). `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈 0건, 보조 로드맵 미체크 코드 작업거리 0건. 같은 날 동일 main HEAD `c2649ad` 기준 16차를 기록한 미머지 드래프트 PR #260을 본 점검(17차)으로 superseded 정리. 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-12 (15차 재현) — **일일 점검 (신규 컨테이너 독립 재현, main `91a4fcc` 기준)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (503.23s, 커버리지 83.93%) 독립 재현 GREEN — 8~14차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `91a4fcc` — 14차 기준 `e1aa87c`에서 PR #258 머지로 전진), main 최신 커밋 CI·Security·Hash·Pages 전 워크플로우 success. `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈·PR 0건, 보조 로드맵 미체크 코드 작업거리 0건(`SIMULATOR_HYPER_PLAN` 데모 영상은 MediaRecorder 녹화 기능이 CIN-4에 이미 구현 → 영상 산출만 브라우저 세션 의존). 환경 함정: `dash`·`pandas` 미설치 시 16건 ModuleNotFound → `requirements.txt` 전체 설치 + `pytest<9` 정렬 필요(CHANGELOG 참조). 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-12 (14차 재현) — **일일 점검 (신규 컨테이너 독립 재현 + 중복 점검 PR #257 정리)**: 신규 세션 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (407.63s, 커버리지 CI 기준 83.93%) 독립 재현 GREEN — 8~13차와 동일 수치. 브랜치 `main` 완전 동기(0/0, HEAD `e1aa87c`), main 최신 커밋 CI·Security·Hash·Pages 전 워크플로우 success. `src/`·`api/` 실 TODO 0건(`onboard_bridge.py` `NotImplementedError`는 추상 인터페이스·가드로 오탐), 열린 이슈 0건, 보조 로드맵 미체크 코드 작업거리 0건. 같은 날 동일 4,057 검증을 기록한 미머지 드래프트 PR #257(13차)을 본 점검(14차)으로 superseded 정리. 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-11 (8차 재현) — **일일 점검 (신규 컨테이너 독립 재현 + 중복 점검 PR 정리)**: 신규 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (531s, 커버리지 83.93%) 독립 재현 GREEN — 직전 재현들과 동일 수치. 환경 함정(PATH의 uv 격리 `pytest 9.0.2`가 conftest import 실패 유발 → `python -m pytest` 8.4.2로 우회)은 CHANGELOG 참조. 같은 날 동일 검증을 기록한 미머지 중복 점검 PR #250(6차)·#251(7차)을 본 점검으로 superseded 정리. main 최신(`bba6815`) CI·Security·Hash·Pages 전 워크플로우 success. 코드 실 TODO·열린 이슈·보조 로드맵 미체크 0건. 로드맵 99.5% 유지 — 잔여 4항목 전부 사용자 환경 의존.*

*2026-06-11 (재점검) — **일일 점검 (신규 컨테이너 독립 재현)**: 신규 클론 컨테이너에서 의존성 신규 설치 후 전체 회귀 **4,057 pass / 252 skip / 0 fail** (커버리지 83.93%) 독립 재현 GREEN. main CI 전 워크플로우 success. 코드 내 실 TODO 0건. 로드맵 99.5% 유지 — 잔여 4항목(P755 창업·Track A 실기·P707 실측 그래프·P709 IROS 투고) 전부 사용자 환경 의존이라 코드 작업거리 없음.*

*Last updated: 2026-06-11 — **일일 점검 + 백로그 통합(#240 + #232)**: 의존성 신규 설치 후 전체 회귀 독립 재현 **GREEN**. 잔여 코드 작업 2건을 단일 브랜치로 통합. (1) **P741 Raft quorum 정정**(#240) — `airspace_controller_ha.py` `replicate()` 를 quorum 인식으로 정정(피어 없는 단일 노드만 즉시 커밋, 피어 존재 시 조기 커밋 방지하고 `RaftCluster.propose` 에 과반 복제 위임) + `start()` TODO를 결정론적 드라이버(`RaftCluster.tick`) 위임 명시로 대체, 회귀 테스트 2건 추가. (2) **STELLAR Phase 51 시드 완성**(#232) — 유일 잔여 시뮬레이터 gap이던 Phase 51을 상태 기반 결정적 권고 사이클(`stellar51Recommend`/`Tick`/`Revoke`/`Groups`)로 완성, 4개 군집 사본 md5 동기화 + E2E 1건. 시뮬레이터 STELLAR Phase 52-100은 canonical 이름으로 main에 이미 구현됨을 확인 → PR #124(AR)·#128(stellar52~55)·#239(raft 주석 only) **superseded**. 잔여(사용자 환경 의존): Track A 실기 검증, P707 실측 그래프, P709 IROS 투고, P755 창업.*

*2026-06-09 — **일일 점검 + PR 백로그 정리**: 전체 회귀 3,970 pass / 254 skip / 0 fail (GREEN). 코드 내 마지막 실 TODO 4건을 머지로 해소 — #205(P707 논문 §2-§7) main 직접 머지 + #204(onboard yaw)·#206(P736 RL env 실동작)·#207(P741 Raft §5.3 catch-up)을 본 브랜치로 통합(README changelog 충돌만 수동 해소). obsolete PR 17건(CLI `--output` 중복 13 + 빈 diff 3 + P711 구버전 #138) close. 잔여 (사용자 환경 의존): Track A 실기 검증, P707 실측 실험 그래프, P709 IROS 2026 실제 투고, P755 창업. 코드 로드맵 **99.5%** · conflict 마커 0.*
