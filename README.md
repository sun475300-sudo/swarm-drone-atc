<div align="center">

# SDACS — Swarm Drone Airspace Control System
### 군집드론 공역통제 자동화 시스템

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-4CAF50?style=for-the-badge)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17-00A0DC?style=for-the-badge&logo=plotly)](https://dash.plotly.com/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)
[![SciPy](https://img.shields.io/badge/SciPy-1.12-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)](https://scipy.org/)

[![Phase](https://img.shields.io/badge/Phase-660-gold?style=for-the-badge&logo=rocket)](simulation/)
[![Tests](https://img.shields.io/badge/Tests-2%2C668%2B%20Passed-success?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Algorithms](https://img.shields.io/badge/Algorithms-600+-FF6F00?style=for-the-badge&logo=databricks&logoColor=white)](#core-algorithms)
[![Modules](https://img.shields.io/badge/Modules-590+-9C27B0?style=for-the-badge&logo=python&logoColor=white)](simulation/)
[![Languages](https://img.shields.io/badge/Languages-50+-FF5722?style=for-the-badge&logo=github&logoColor=white)](#multi-language-architecture)
[![LOC](https://img.shields.io/badge/Total-120K%2B%20LOC-blue?style=for-the-badge&logo=visualstudiocode&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Mokpo National University, Dept. of Drone Mechanical Engineering — Capstone Design (2026)**

**국립 목포대학교 드론기계공학과 캡스톤 디자인**

[3D Simulator](https://sun475300-sudo.github.io/swarm-drone-atc/swarm_3d_simulator.html) | [Technical Report](docs/report/SDACS_Technical_Report.docx) | [Performance Charts](docs/images/)

</div>
<div align="center">
<img src="https://i.imgur.com/fP5lw8Y.png" alt="SDACS Hero Banner" width="800"/>
</div>

---
## What is SDACS? / SDACS란?
SDACS는 **군집드론을 이동형 가상 레이더 돔(Dome)으로 활용**하여, 도심 저고도 공역을 자율적으로 감시하고 충돌을 사전에 방지하는 **분산형 공역통제 시뮬레이션 시스템**입니다.
SDACS is a **distributed Air Traffic Control (ATC) simulation** that uses swarm drones as **mobile virtual radar domes**. Instead of relying on expensive fixed infrastructure, drones themselves form the surveillance network — detecting, predicting, and autonomously resolving airspace conflicts in real time.

### The Problem / 해결하려는 문제
| 기존 방식 | 한계 |
|----------|------|
| 고정형 레이더 | 설치 비용 수억원, 소형 드론 탐지 불가, 6개월 설치 기간 |
| 중앙 집중식 관제 (K-UTM) | 단일 장애점(SPOF), 실시간성 부족 |
| 수동 관제 | 평균 5분 지연, 24/7 인력 비용 과다 |
> **국내 등록 드론 90만대 돌파, 연간 30% 증가** — 택배 배송, 농업 방제, UAM이 동시 운용되며 저고도 공역 충돌 위험이 급증하고 있습니다.

### Our Approach / SDACS의 접근
1. **레이더를 드론으로 대체** — 고정 인프라 없이 30분 내 긴급 배치
2. **탐지부터 회피까지 완전 자동화** — 90초 전 선제 충돌 예측, 6종 자동 어드바이저리 발행
3. **드론 추가만으로 관제 반경 선형 확장** — 분산형 아키텍처로 단일 장애점 제거
<div align="center">
<img src="https://i.imgur.com/Xm6G9Dt.png" alt="분산형 APF 충돌 회피 3D 시각화" width="700"/>
<br/><sub>분산형 APF 충돌 회피 — 드론별 인력/척력장이 실시간으로 안전 궤적을 생성</sub>
</div>

---
## Key Results / 핵심 성과
| Metric | Value | Description |
|--------|-------|-------------|
| **Collision Resolution** | **100% (20대)** | 20대 600s: 충돌 0건, 50대: 97.9%, 100대: 98.9% |
| **Route Efficiency** | **≤1.12** | 전 규모 SLA(≤1.15) PASS (600s 실측) |
| **Prediction Lookahead** | **90 seconds** | CPA-based preemptive conflict detection at 1 Hz |
| **Advisory Latency** | **< 1 second** | 6 types: CLIMB/DESCEND/TURN_LEFT/TURN_RIGHT/EVADE_APF/HOLD |
| **Monte Carlo Validation** | **38,400 runs** | 384 configurations x 100 seeds |
| **Scenario Coverage** | **42 scenarios** | Extreme weather, intrusion, GPS jamming, mass delivery, etc. |
| **Concurrent Drones** | **100+** | 20대: 충돌 0, 50대: avg 15, 100대: avg 29 |
| **Deployment Time** | **30 min** | No fixed infrastructure required |
| **Test Coverage** | **2,668+ tests** | Automated pytest suite across 590+ modules |
<div align="center">
<img src="https://i.imgur.com/wHuMIfM.png" alt="기존 방식 대비 SDACS 성능 비교" width="750"/>
<br/><sub>기존 Rule-based Static ATC vs SDACS Swarm Autonomous — 주요 KPI 비교</sub>
</div>

---
## System Architecture / 시스템 아키텍처
SDACS는 4개의 독립적 계층으로 구성됩니다. 각 계층은 명확한 역할과 인터페이스를 가지며, 독립적으로 테스트 가능합니다.
<div align="center">
<img src="https://i.imgur.com/Oz6LB2I.png" alt="SDACS 4계층 시스템 아키텍처" width="750"/>
<br/><sub>SDACS 4계층 아키텍처 — 드론 에이전트 / 공역 관제 / 시뮬레이션 엔진 / 사용자 인터페이스</sub>
</div>
```
┌─────────────────────────────────────────────────────────────────┐
│                     Layer 4: User Interface                     │
│                CLI (main.py) + Dash 3D Visualizer               │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 3: Simulation Engine                    │
│          SwarmSimulator + WindModel + Monte Carlo Engine         │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 2: Control System                      │
│     AirspaceController (1Hz) + Priority Queue + Advisory Gen    │
├─────────────────────────────────────────────────────────────────┤
│                     Layer 1: Drone Agents                       │
│            _DroneAgent (10Hz SimPy process per drone)            │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1 — Drone Agent (드론 에이전트)
각 드론은 SimPy 이산 이벤트 프로세스로 모델링됩니다. 10Hz 주기로 위치/속도/배터리 상태를 갱신하며, 비행 상태 머신(FSM)에 따라 `Idle → Takeoff → Cruise → Avoid → Landing` 전이를 수행합니다.
- **파일**: `simulation/simulator.py` — `_DroneAgent` 클래스
<div align="center">
<img src="https://i.imgur.com/bBRoCn6.png" alt="센서 퓨전 프로세스" width="700"/>
<br/><sub>센서 퓨전 — Camera(YOLO) + LiDAR + RF Scanner → Kalman Filter → 위치/식별/위협 판정</sub>
</div>

### Layer 2 — Airspace Controller (공역 관제)
1Hz 주기로 모든 활성 드론의 위치를 수집하고, 충돌 위험을 평가하여 자동 어드바이저리를 발행합니다.
- **CPA (Closest Point of Approach)**: O(N^2) 쌍별 스캔, 90초 선제 예측
- **Voronoi 공역 분할**: 10초 주기 동적 갱신, 밀도 기반 셀 분리
- **Resolution Advisory**: 기하학적 분류에 따른 6종 회피 명령 자동 생성
- **동적 분리간격**: 풍속 연동 자동 조정 (1.0x ~ 1.6x, 5/10/15 m/s 구간)
- **파일**: `src/airspace_control/controller/airspace_controller.py`

### Layer 3 — Simulation Engine (시뮬레이션 엔진)
SimPy 기반 이산 이벤트 시뮬레이션 엔진으로, 다양한 환경 조건과 장애 시나리오를 주입할 수 있습니다.
- **SwarmSimulator**: 정식 시뮬레이터 (engine_legacy 삭제 완료)
- **WindModel**: 3종 기상 모델 (constant / variable-gust / shear)
- **Monte Carlo**: 384 config x 100 seeds = 38,400 검증 실행
- **장애 주입**: MOTOR/BATTERY/GPS 고장, 통신 두절, 미등록 드론 침입
- **파일**: `simulation/simulator.py`, `simulation/wind_model.py`, `simulation/monte_carlo.py`

### Layer 4 — User Interface (사용자 인터페이스)
- **CLI**: `main.py` — simulate, scenario, monte-carlo, visualize, ops-report 명령
- **3D Dashboard**: Dash + Plotly 실시간 3D 시각화, 드론 궤적/충돌 경고/편대 표시
- **파일**: `main.py`, `visualization/simulator_3d.py`
```mermaid
sequenceDiagram
    participant D as Drone (10Hz)
    participant AC as AirspaceController (1Hz)
    participant RA as Resolution Advisory
    D->>AC: Position/velocity report
    AC->>AC: CPA scan (O(N^2), 90s lookahead)
    alt Conflict detected
        AC->>RA: Request avoidance maneuver
        RA-->>AC: Advisory (CLIMB/DESCEND/TURN/EVADE/HOLD)
        AC->>D: Issue advisory
    end
    D-->>AC: Acknowledge
```

---
## Core Algorithms / 핵심 알고리즘
SDACS의 충돌 회피 파이프라인은 **탐지 → 판단 → 실행** 3단계로 구성됩니다.
<div align="center">
<img src="https://i.imgur.com/8IPIDWR.png" alt="탐지 → 회피 자동 대응 파이프라인" width="750"/>
<br/><sub>탐지 → 회피 자동 대응 파이프라인 — DETECT → IDENTIFY → TIMER → WARN → RETREAT (Target Latency < 1s)</sub>
</div>

### 1. Collision Detection / 충돌 탐지
| Algorithm | Purpose | Complexity |
|-----------|---------|------------|
| **CPA (Closest Point of Approach)** | 두 드론의 최근접점 시각/거리 계산 | O(N^2) per tick |
| **Voronoi Tessellation** | 공역을 드론별 셀로 분할, 침범 감지 | O(N log N) |
| **Geofence Monitor** | 공역 경계(90%) 이탈 시 자동 RTL | O(N) |
| **Intrusion Detection** | ROGUE 프로파일 미등록 드론 탐지 | O(N) |

### 2. Conflict Resolution / 충돌 해결
| Algorithm | Purpose | Description |
|-----------|---------|-------------|
| **APF (Artificial Potential Field)** | 실시간 충돌 회피 | 인력장(목표) + 척력장(장애물), 강풍 시 `APF_PARAMS_WINDY` 자동 전환 |
| **CBS (Conflict-Based Search)** | 다중 에이전트 경로 계획 | 충돌 트리 탐색으로 최적 비충돌 경로 계산 |
| **Resolution Advisory Generator** | 회피 명령 자동 분류 | 기하학적 관계(상대 위치/속도)에 따라 6종 어드바이저리 결정 |
| **A\* Path Replanning** | 동적 경로 재계획 | 에너지 비용 함수 + 충전소 경유 + 풍향/고도 반영 |

### 3. Formation Control / 편대 제어
| Algorithm | Purpose | Description |
|-----------|---------|-------------|
| **Graph Laplacian Consensus** | 대형 유지/전환 | 리더-팔로워 합의 기반, V/Line/Circle/Grid 4패턴 |
| **Reynolds Boids** | 군집 행동 | 분리/정렬/응집 3규칙 + 장애물 회피 확장 |
| **ORCA (Optimal Reciprocal Collision Avoidance)** | 속도 공간 최적화 | 반속도 장애물 기반 안전 속도 선택 |

### 4. Advanced Modules (Phase 1-610)
560+개의 알고리즘 모듈이 6개 계층에 걸쳐 구현되어 있습니다:
| Category | Examples | Count |
|----------|----------|-------|
| **Physics & Dynamics** | Wind model, battery model, energy optimization | 40+ |
| **AI & ML** | DRL, MARL, NAS, meta-learning, GAN, XAI | 60+ |
| **Optimization** | PSO, ACO, NSGA-II, genetic algorithm, quantum annealing | 30+ |
| **Communication** | Mesh network, V2X, 5G/6G, acoustic, encryption | 25+ |
| **Autonomy** | Formation control, task allocation, mission planning | 35+ |
| **Security** | Zero-trust, blockchain, intrusion detection, adversarial defense | 20+ |
| **Bio-inspired** | Morphogenesis, optogenetics, electrostatics, ecosystem dynamics | 25+ |
| **Mathematical** | Topology control, information theory, CSP, causal inference | 30+ |

### Project Structure / 프로젝트 구조
```
swarm-drone-atc/
├── simulation/                      # Layer 1 & 3: Drone Agents + Sim Engine
│   ├── simulator.py                 # SwarmSimulator + _DroneAgent
│   ├── apf_engine/                  # Artificial Potential Field
│   ├── cbs_planner/                 # Conflict-Based Search
│   ├── voronoi_airspace/            # Voronoi tessellation
│   ├── monte_carlo.py               # Monte Carlo engine
│   ├── weather.py                   # WindModel
│   └── ... (240+ modules)
│
├── src/airspace_control/            # Layer 2: Control System
│   ├── controller/                  # AirspaceController, PriorityQueue
│   ├── avoidance/                   # Resolution Advisory
│   ├── agents/                      # DroneState, DroneProfiles
│   ├── comms/                       # CommunicationBus
│   ├── planning/                    # FlightPathPlanner
│   └── utils/                       # GeoMath, CoordinateSystems
│
├── visualization/                   # Layer 4: UI
│   ├── simulator_3d.py              # Dash 3D real-time dashboard
│   └── advanced_dashboard.py        # Supplementary charts
│
├── tests/                           # 2,668+ automated tests
│   ├── test_simulator_scenarios.py
│   ├── test_phase*.py
│   └── ...
│
├── config/                          # Configuration
│   ├── default_simulation.yaml
│   ├── monte_carlo.yaml
│   └── scenario_params/             # 7 scenario definitions
│
├── docs/                            # Documentation & assets
│   ├── images/                      # SVG diagrams, charts
│   └── report/                      # Technical report (DOCX)
│
├── main.py                          # CLI entry point
└── scripts/                         # Utility scripts
```

---
## How It Works / 작동 원리
<div align="center">
<img src="https://i.imgur.com/o6kmDrU.png" alt="핵심 알고리즘 워크 흐름" width="750"/>
<br/><sub>핵심 알고리즘 워크 흐름 — Monte Carlo 검증부터 CBS/APF 경로 계획까지</sub>
</div>
**비행 상태 머신 (Flight State Machine):**
<div align="center">
<img src="https://i.imgur.com/TFJG4zF.png" alt="드론 비행 상태 기계 (Flight Phase FSM)" width="650"/>
<br/><sub>드론 비행 상태 기계 — GROUNDED → TAKEOFF → ENROUTE → EVADING/HOLDING → LANDING</sub>
</div>
```
                    ┌──────────────┐
                    │   GROUNDED   │ ◄──────────────────────┐
                    └──────┬───────┘                        │
                           │ takeoff()                      │ landed
                    ┌──────▼───────┐                 ┌──────┴───────┐
                    │   TAKEOFF    │                 │   LANDING    │
                    └──────┬───────┘                 └──────▲───────┘
                           │ alt >= CRUISE_ALT              │ mission complete
                    ┌──────▼───────┐                        │ / battery low
              ┌────►│   ENROUTE    ├────────────────────────┘
              │     └──┬───────┬───┘
              │        │       │
    advisory  │        │       │ conflict detected
    expired   │        │       │
              │   ┌────▼──┐  ┌─▼────────┐
              └───┤HOLDING│  │  EVADING  │ ◄── APF forces active
                  └───────┘  └──────────┘
                                  │
                           ┌──────▼───────┐
                           │  EMERGENCY   │ ← RTL / forced landing
                           └──────────────┘
```
<div align="center">
<table>
<tr>
<td align="center"><img src="https://i.imgur.com/oVr0lt8.png" alt="시나리오별 KPI 레이더" width="380"/><br/><sub>시나리오별 KPI 레이더 차트</sub></td>
<td align="center"><img src="https://i.imgur.com/I2iejhf.png" alt="어드바이저리 지연 시간" width="380"/><br/><sub>시나리오별 어드바이저리 지연 (P50/P99)</sub></td>
</tr>
</table>
</div>

### 17. CI/CD Pipeline / 지속적 통합 파이프라인
`.github/workflows/ci.yml` 단일 워크플로우로 통합 운영합니다.
**Test Job (Python 3.10 / 3.11 / 3.12 매트릭스):**
| Step | 내용 |
|------|------|
| Checkout | `actions/checkout@v4` |
| Python Setup | `actions/setup-python@v5` (매트릭스) |
| Cache pip | pip 캐시 (requirements.txt 해시 기반) |
| Install | `pip install -r requirements.txt` + flake8 |
| Lint | `flake8 --select=E9,F63,F7,F82` (구문 오류만) |
| Test | `pytest tests/ -v --tb=short --timeout=60` |
| Import Check | 핵심 3개 모듈 임포트 검증 |
| Smoke Report | PR 시 JSON 리포트 생성 + 아티팩트 업로드 |
| Perf Summary | PR 시 성능 요약 JSON 생성 |
**Ops Report Job (main 푸시 시):**
| Step | 내용 |
|------|------|
| Trigger | `push` to `main` (test 통과 후) |
| Bundle | `ops_report_bundle.json` (manifest + artifact references) |
| Upload | 아티팩트 보존 90일 |
**시나리오 파라미터 오버라이드 체계:**
```
config/default_simulation.yaml  (기본값)
    ↓ 머지
config/scenario_params/{name}.yaml  (시나리오 오버라이드)
    ↓ 머지
CLI arguments  (실행 시 오버라이드)
    ↓
SwarmSimulator._deep_merge()  → 최종 설정
```

---
## Multi-Language Architecture / 다중 언어 아키텍처
SDACS는 핵심 시뮬레이션(Python) 외에 50개 이상의 프로그래밍 언어로 구현된 220+ 보조 모듈을 포함합니다.

### Integration Approach / 연동 방식
각 언어 모듈은 **독립적 마이크로모듈** 패턴으로 설계되었습니다:
- **Python Core ↔ Native 모듈**: `subprocess` 호출 또는 `ctypes`/`cffi` FFI(Foreign Function Interface)를 통해 고성능 연산(C++/Rust/Fortran)을 Python에서 호출
- **REST API 모듈** (TypeScript/PHP/Ruby): Express/Flask 스타일 HTTP 엔드포인트로 대시보드/포털 기능 제공
- **Protocol 모듈** (Prolog/Haskell/Ada): 독립 실행형 검증기/추론 엔진으로, 결과를 JSON/stdout으로 Python에 전달
- **Reference Implementation** (COBOL/Assembly/VHDL): 레거시 시스템 호환성 검증 및 하드웨어 시뮬레이션 참조 구현
> 핵심 원칙: **Python이 오케스트레이터**, 각 언어가 특정 도메인의 **전문가 모듈** 역할. 시뮬레이션 실행에는 Python만 필요하며, 다국어 모듈은 특수 목적(성능 최적화, 형식 검증, 하드웨어 연동 등)에 활용됩니다.

### Language Portfolio / 언어별 역할
| Language | Modules | Use Case | Integration |
|----------|---------|----------|-------------|
| **Python** | 580+ | Core simulation, ML/AI, analytics, production hardening | Main engine |
| **Rust** | 15 | Safety-critical: satellite comm, NEAT evolution, safety verifier | FFI / subprocess |
| **Go** | 14 | Concurrent: edge AI, mission validation, realtime monitor | subprocess / gRPC |
| **C++** | 14 | Performance: SLAM, morphogenesis, physics, particle filter | ctypes / FFI |
| **Zig** | 15 | Low-level: PBFT consensus, ring buffer v2, telemetry | subprocess |
| **Fortran** | 9 | Numerical: wind field FDM, CFD wind tunnel | f2py / subprocess |
| **Ada** | 7 | Safety: TMR v2 (Byzantine fault tolerance) | Reference impl |
| **VHDL** | 7 | Hardware: PWM controller, FIR filter, signal processing | Simulation only |
| **Assembly** | 7 | Bare-metal: CRC32, sensor readout, Kalman filter | ctypes |
| **Prolog** | 8 | Logic: airspace rules v2, constraint satisfaction | subprocess |
| **Nim** | 1 | Async: event dispatcher, telemetry routing | standalone |
| **OCaml** | 1 | Formal: flight plan type checker, ADT verification | standalone |
| **Haskell** | 1 | Formal verification: type-safe safety proofs | standalone |
| **TypeScript** | 2 | Dashboard REST API, physics engine | HTTP API |
| **Swift/Kotlin** | 3 | Mobile monitoring (iOS/Android) | REST client |
| **Julia** | 1 | High-performance ODE solver | standalone |
| **Elixir/Erlang** | 3 | OTP fault supervision, distributed consensus | message passing |
| **Others** | 30+ | PHP, COBOL, R, Perl, Scheme, Octave, Lua, Ruby, Dart, Scala, etc. | Various |
```mermaid
pie title Module Distribution by Language (Phase 660)
    "Python" : 580
    "Zig" : 15
    "Rust" : 15
    "Go" : 14
    "C++" : 14
    "Fortran" : 9
    "Prolog" : 8
    "Assembly" : 7
    "Ada" : 7
    "VHDL" : 7
    "Others (40+)" : 75
```

---
## Development Phases / 개발 단계
SDACS는 660개 Phase를 거치며 점진적으로 확장되었습니다.
| Phase Range | Focus | Highlights |
|-------------|-------|------------|
| **1-50** | Core ATC | SimPy engine, CPA, APF, Voronoi, wind model |
| **51-100** | Operations | Geofence, fleet management, noise model, health monitor |
| **101-170** | AI & Security | DRL, NAS, zero-trust, blockchain, digital twin |
| **171-200** | Production | E2E reporting, compliance engine, SLA monitor |
| **201-260** | Scale | Multi-cloud, K8s, 5G/6G, edge computing |
| **261-300** | Autonomy | SLAM, formation control, V2X, mesh network |
| **301-350** | Advanced CPS | Quantum-inspired, WASM, neuromorphic SNN, game theory |
| **351-400** | Optimization | NSGA-II, RTOS, MARL, energy harvesting |
| **401-470** | Intelligence | Knowledge graph, causal inference, video analytics |
| **471-500** | Integration | Grand Unified Controller, 25-language multi-lang |
| **501-520** | Next-Gen | Quantum comms, blockchain v2, GAN, edge ML |
| **521-560** | Mega Expansion | Swarm intelligence, visual rendering, DSP |
| **561-600** | Deep Theory | Reaction-diffusion, QEC, IIT consciousness, Neural ODE, Phase 600 Grand Unified |
| **601-610** | Advanced Models | Topology control, Vickrey auction, Fisher info, PRM, Laplacian consensus, optogenetics, multi-fidelity sim, Bayesian reputation, Coulomb electrostatics, CSP solver |
| **611-620** | Multi-Lang V | TypeScript, Swift, Kotlin, PHP, Haskell, COBOL, R, Perl, Scheme, Octave |
| **621-630** | Deep Math | Crystallography, pheromone trail, hyperbolic embedding, Navier-Stokes, HTM cortical column, NEAT evolution, knot theory, market maker, persistent homology, plasma physics |
| **631-640** | Multi-Lang VI + Benchmark | Julia, Scala, Elixir, Dart, Lua, Ruby, Clojure v2, Erlang Raft, Fortran CFD, System Benchmark |
| **641-650** | Production Hardening | KDTree spatial index, telemetry compression, health predictor, adaptive sampling, Raft consensus, anomaly detection, mission scheduler, energy optimizer, formation GA, integration runner |
| **651-660** | Multi-Lang VII | Go realtime monitor, Rust safety verifier, C++ particle filter, Zig ring buffer v2, Ada TMR v2, VHDL FIR filter, Prolog rules v2, Assembly Kalman filter, Nim async dispatcher, OCaml type checker |

---
## Testing / 테스트
```bash
# 전체 테스트 실행
pytest tests/ -v
# 특정 Phase 테스트
pytest tests/test_phase641_660.py -v    # Phase 641-660 (55 tests)
pytest tests/test_phase631_640.py -v    # Phase 631-640 (15 tests)
pytest tests/test_phase601_610.py -v    # Phase 601-610 (50 tests)
pytest tests/test_phase571_600.py -v    # Phase 571-600 (111 tests)
```

### Test Categories
| Category | Count | Scope |
|----------|-------|-------|
| Unit tests (simulation modules) | 1,600+ | Individual algorithm correctness |
| Integration tests (controller) | 250+ | Multi-component interaction |
| Scenario tests | 150+ | End-to-end scenario validation |
| Multi-language file tests | 350+ | File existence + syntax verification |
| Performance benchmarks | 50+ | Throughput, latency, scalability |
| Regression tests | 250+ | Previously fixed bugs |

---
## Performance Analysis / 성능 분석
<div align="center">
<table>
<tr>
<td align="center"><img src="https://i.imgur.com/yQSdBKo.png" alt="충돌 스캔 처리량 비교" width="400"/><br/><sub>O(N^2) vs KDTree 충돌 스캔 처리량</sub></td>
<td align="center"><img src="https://i.imgur.com/1nvqvmm.png" alt="충돌 해결률 히트맵" width="400"/><br/><sub>드론 수 x 시뮬레이션 시간별 해결률(%)</sub></td>
</tr>
</table>
</div>

### Throughput vs Drone Count
```
Drones │ Tick Time │ Real-time Ratio │ Status
───────┼───────────┼─────────────────┼─────────
   20  │   0.8 ms  │     1250x       │ Excellent
   50  │   4.2 ms  │      238x       │ Excellent
  100  │  16.1 ms  │       62x       │ Good
  200  │  63.5 ms  │       16x       │ Acceptable
  500  │ 398.0 ms  │      2.5x       │ Near real-time
```

### Collision Resolution Formula
```
Resolution Rate = 1 - collisions / (conflicts + collisions)
600s 시뮬레이션 실측 결과 (12회, 2026-04-06):
  20대:  충돌 0건, 해결률 100.0%, 경로효율 1.035
  50대:  충돌 avg 15건, 해결률 97.9%, 경로효율 1.003
  100대: 충돌 avg 29건, 해결률 98.9%, 경로효율 1.029
```

---
## Team / 팀
| Name | Role | Affiliation |
|------|------|-------------|
| **Sunwoo Jang (장선우)** | Lead Developer | Mokpo National University, Drone Mechanical Engineering |

---
## References / 참고 문헌
1. **SimPy** — Discrete Event Simulation for Python (simpy.readthedocs.io)
2. **Artificial Potential Field** — Khatib, O. (1986). Real-time obstacle avoidance for manipulators and mobile robots.
3. **Conflict-Based Search** — Sharon, G. et al. (2015). CBS for optimal multi-agent pathfinding.
4. **CPA Algorithm** — Kuchar, J.K. & Yang, L.C. (2000). A review of conflict detection and resolution modeling methods.
5. **Voronoi Tessellation** — Aurenhammer, F. (1991). Voronoi diagrams — a survey of a fundamental geometric data structure.
6. **Reynolds Boids** — Reynolds, C.W. (1987). Flocks, herds and schools: A distributed behavioral model.
7. **ORCA** — van den Berg, J. et al. (2011). Reciprocal n-body collision avoidance.

---
## Roadmap / 향후 계획
Phase 660까지 완료되었습니다. 향후 확장 계획은 [ROADMAP.md](ROADMAP.md)에서 확인할 수 있습니다.

---
## License
MIT License — Developed for academic and educational purposes.

---
<div align="center">
**Made with dedication by Sunwoo Jang**
**장선우 · 국립 목포대학교 드론기계공학과**
**Phase 660 · 590+ Modules · 2,668+ Tests Passed · 50+ Languages · 120K+ LOC**
</div>

## 변경 이력 (Changelog)
| 날짜/시간 (KST) | 커밋 | 작업 내용 | 수정 파일 |
| --- | --- | --- | --- |
| 2026-04-06 16:46 | `0c9dcea` | fix: CLAUDE.md 테스트 수 동기화 + CI ops-report 동적 수집 | .github/workflows/ci.yml, CLAUDE.md |
| 2026-04-02 17:28 | `3bddf7c` | docs: README 시나리오 결과 테이블 + CI/CD 파이프라인 사양 추가 | README.md |
| 2026-04-02 12:15 | `a99203a` | docs: README 전체 시스템 정밀 기술 사양 5개 섹션 추가 | README.md |
| 2026-04-02 | `c744c51` | fix: CBS 플래너 타임아웃 추가 + 테스트 실패 2건 수정 | simulation/cbs_planner/cbs.py, simulation/config_schema.py, tests/test_phase16_17.py |
| 2026-04-02 | `bc02fef` | docs: README 전체 시스템 정밀 기술 사양 11개 섹션 추가 | README.md |
| 2026-04-02 | `16fccd8` | merge: fix-test-failures-50 + code-review-8fv1B 브랜치 병합 | 13 files |
| 2026-04-01 22:11 | `886aadf` | fix: DeprecationWarning 68건 → 0건 + pytest 수집 경고 제거 | simulation/autonomous_landing.py, simulation/integration_test_framework.py, tests/test_phase300_310.py |
| 2026-04-01 12:20 | `9c18568` | fix: 대규모 테스트 실패 50건 → 0건 수정 | config/monte_carlo.yaml, simulation/apf_engine/apf.py, simulation/multi_agent_coordination.py, src/airspace_control/agents/drone_profiles.py, src/airspace_control/agents/drone_state.py, tests/test_apf.py … |
| 2026-04-01 08:07 | `bec9f89` | fix: 의존성 버전 동기화 + DeprecationWarning 수정 | pyproject.toml, simulation/waypoint_optimizer.py |
| 2026-03-31 22:04 | `671990e` | fix: 충돌 해결률(CR) 0% 버그 수정 — CONFLICT/NEAR_MISS 이벤트 누락 | simulation/simulator.py |
| 2026-03-31 20:22 | `cee81bc` | fix: 비행 계획 검증기 최소 고도 불일치 수정 (10m→30m) | simulation/flight_plan_validator.py |
| 2026-03-31 19:41 | `824c7f4` | perf: 성능 최적화 4건 — 캐시/해싱/큐/윈도우 개선 | simulation/simulator.py, simulation/spatial_hash.py, src/airspace_control/controller/airspace_controller.py |
| 2026-03-31 19:35 | `be11619` | refactor: 핵심 함수 테스트 17개 추가 + 매직 넘버 상수화 | simulation/simulator.py, tests/test_core_functions.py |
| 2026-03-31 19:31 | `e821fe7` | fix: 잔여 broad exception 3건 → 특정 예외 타입으로 교체 | simulation/decision_tree_atc.py, simulation/event_architecture.py, simulation/regulation_updater.py |
| 2026-03-31 19:28 | `c7cbef3` | test: CBS 플래너 edge case 테스트 11개 추가 (8→19) | tests/test_cbs.py |
| 2026-03-31 19:24 | `edadaff` | ci: CI/CD 통합 및 pytest-timeout 설정 | .github/workflows/ci.yml, .github/workflows/python-app.yml, pyproject.toml, requirements.txt |
| 2026-03-31 19:21 | `fd8c5c1` | deps: pydantic>=2.0 추가 — config_schema.py YAML 검증에 필수 | requirements.txt |
| 2026-03-31 19:20 | `e0703ae` | fix: 테스트 실패 20건 → 0건 수정 + 잔여 코드 품질 개선 | chatbot/app.py, main.py, simulation/batch_simulator.py, simulation/cbs_planner/cbs.py, simulation/simulator.py, simulation/voronoi_airspace/voronoi_partition.py … |
| 2026-03-31 18:33 | `b32e122` | docs: README 대규모 편집 — 품질 개선 및 일관성 확보 | README.md |