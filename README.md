# 🚁 군집드론 공역통제 자동화 시스템

**Swarm Drone Airspace Control System (SDACS)**

<div align="center">

![Hero Banner](docs/images/hero_banner.svg)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-green)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17-00A0DC?logo=plotly)](https://dash.plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-63%20passing-brightgreen)](tests/)
[![Monte Carlo](https://img.shields.io/badge/Monte%20Carlo-38%2C400%20runs-blueviolet)]()

</div>

---

## 📖 프로젝트 개요

군집드론을 이동형 가상 레이더 돔으로 활용하여, 고정형 인프라 없이도
도심 저고도 공역을 실시간으로 감시하고 위협에 **자동 대응**하는
**분산형 ATC(Air Traffic Control) 시뮬레이션 시스템**입니다.

### 🎯 핵심 특징

| 항목 | 값 | 설명 |
|------|-----|------|
| ⚡ 충돌 예측 선제 | 90 s lookahead | CPA 기반 O(N²) 스캔 |
| 🤖 자동 어드바이저리 | CLIMB / TURN / EVADE | 우선순위 기반 기하학적 분류 |
| 🎲 Monte Carlo 검증 | 38,400 회 | 4 × 2 × 4 × 3 × 4 = 384 configs |
| 🌬️ 기상 모델 | 3종 | constant / variable(gust) / shear |
| 🚨 침입 탐지 | ROGUE 프로파일 | 미등록 드론 IntrusionAlert |
| 🗺️ 동적 공역 분할 | Voronoi | 10 s 주기 자동 갱신 |

---

## 🏗️ 시스템 아키텍처

![System Architecture](docs/images/architecture.svg)

### 4계층 구조

```
Layer 4 · 사용자     → 3D Dash 시각화 · CLI · pytest 테스트
Layer 3 · 시뮬레이션 → SwarmSimulator · 기상 · Monte Carlo · 시나리오
Layer 2 · 제어       → AirspaceController · 경로 계획 · Voronoi
Layer 1 · 드론       → _DroneAgent · APF 회피 · 텔레메트리
```

---

## 🧠 핵심 알고리즘

### 알고리즘 처리 흐름

![Algorithm Flow](docs/images/algorithm_flow.svg)

### 드론 비행 상태 기계 (FlightPhase FSM)

![Flight Phase FSM](docs/images/flight_phase_fsm.svg)

| 상태 | 설명 | 전이 조건 |
|------|------|-----------|
| `GROUNDED` | 지상 대기 | 허가(Clearance) 수신 → TAKEOFF |
| `TAKEOFF` | 이륙 중 | 순항고도 도달 → ENROUTE |
| `ENROUTE` | 순항 | 목적지 도달 → LANDING, 충돌위협 → EVADING |
| `HOLDING` | 대기 선회 | 대기 지시 → HOLDING, 재개 → ENROUTE |
| `EVADING` | APF 회피 | 어드바이저리 수신, 완료 → ENROUTE |
| `LANDING` | 착륙 중 | 완료 → GROUNDED |
| `RTL` | 귀환 | 배터리 임계치 초과 |
| `FAILED` | 장애 발생 | 모터/배터리/GPS 장애 주입 |

---

## 🎯 탐지 → 퇴각 자동 대응 파이프라인

![Detection Pipeline](docs/images/detection_pipeline.svg)

---

## 📡 센서 퓨전 프로세스

![Sensor Fusion](docs/images/sensor_fusion.svg)

---

## 📈 성능 비교: 기존 방식 vs SDACS

![Performance Comparison](docs/images/performance_comparison.svg)

---

## 🎬 시나리오

```bash
python main.py scenario --list
```

| 시나리오 | 설명 | 주요 검증 항목 |
|----------|------|----------------|
| `high_density` | 100대 고밀도 교통 | 처리량 한계 · 충돌률 |
| `emergency_failure` | 비행 중 드론 장애 | 비상착륙 우선순위 |
| `mass_takeoff` | 100대 동시 이착륙 | 출발/도착 시퀀싱 |
| `route_conflict` | HEAD_ON · CROSSING · OVERTAKE | 어드바이저리 정확성 |
| `comms_loss` | 통신 두절 | Lost-link RTL 프로토콜 |
| `weather_disturbance` | 강풍 + 돌풍 + Wind Shear | 경로 추적 강건성 |
| `adversarial_intrusion` | 침입 드론 3기 | 탐지 지연시간 |

---

## 🚀 빠른 시작

### 설치

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
pip install -r requirements.txt
```

### 기본 실행

```bash
# 1. 시나리오 목록 확인
python main.py scenario --list

# 2. 시나리오 실행
python main.py scenario weather_disturbance --runs 3

# 3. 단일 시뮬레이션 (600초)
python main.py simulate --duration 600 --seed 42

# 4. Monte Carlo quick sweep
python main.py monte-carlo --mode quick

# 5. 3D 실시간 대시보드
python main.py visualize
# → http://127.0.0.1:8050
```

---

## 📊 Monte Carlo SLA 기준

| 지표 | 목표 | 비고 |
|------|------|------|
| 충돌률 | **0건 / 1,000 h** | 하드 요구사항 |
| Near-miss | ≤ 0.1건 / 100 h | 소프트 경고 |
| 충돌 해결률 | **≥ 99.5 %** | 어드바이저리 발령률 |
| 경로 효율 | ≤ 1.15 (actual/planned) | 우회 비용 |
| 어드바이저리 P50 | ≤ 2.0 s | 응답 지연 |
| 어드바이저리 P99 | ≤ 10.0 s | 최악 케이스 |
| 침입 탐지 P90 | ≤ 5.0 s | ROGUE 탐지 지연 |

```bash
# Full sweep (38,400 runs, ~3h on 16 cores)
python main.py monte-carlo --mode full

# Quick sweep (960 runs, ~4min)
python main.py monte-carlo --mode quick
```

---

## 📂 프로젝트 구조

```
swarm-drone-atc/
├── main.py                          # 통합 CLI 진입점
├── config/
│   ├── default_simulation.yaml      # 기본 시뮬레이션 설정
│   ├── monte_carlo.yaml             # Monte Carlo 파라미터 스윕
│   └── scenario_params/             # 7개 시나리오 YAML
├── simulation/
│   ├── simulator.py                 # SwarmSimulator (SimPy)
│   ├── analytics.py                 # SimulationAnalytics + SimulationResult
│   ├── weather.py                   # 기상 모델 (3종)
│   ├── scenario_runner.py           # 시나리오 실행기
│   ├── monte_carlo_runner.py        # Monte Carlo 병렬 스윕
│   ├── apf_engine/apf.py            # APF 인공 포텐셜 장
│   ├── cbs_planner/cbs.py           # CBS 다중에이전트 경로
│   └── voronoi_airspace/            # Voronoi 공역 분할
├── src/airspace_control/
│   ├── agents/drone_state.py        # DroneState · FlightPhase FSM
│   ├── agents/drone_profiles.py     # 드론 프로파일 (ROGUE 포함)
│   ├── controller/airspace_controller.py  # 1 Hz 제어 루프
│   ├── avoidance/resolution_advisory.py   # AdvisoryGenerator
│   ├── planning/flight_path_planner.py    # A* NFZ 회피 경로 계획
│   ├── comms/communication_bus.py         # SimPy 비동기 통신
│   └── utils/geo_math.py                  # CPA · 거리 계산
├── visualization/
│   └── simulator_3d.py              # Dash + Plotly 3D 대시보드
├── tests/                           # pytest 63개 테스트
│   ├── test_apf.py
│   ├── test_cbs.py
│   ├── test_resolution_advisory.py
│   ├── test_flight_path_planner.py
│   ├── test_airspace_controller.py
│   ├── test_analytics.py
│   └── test_simulator_scenarios.py
└── docs/images/                     # SVG 아키텍처 다이어그램
```

---

## 🧪 테스트

```bash
# 전체 테스트 (63개)
pytest tests/

# 단위 테스트만 (빠름, ~1s)
pytest tests/ --ignore=tests/test_simulator_scenarios.py

# 특정 모듈
pytest tests/test_apf.py tests/test_resolution_advisory.py -v
```

| 테스트 파일 | 수 | 대상 |
|------------|-----|------|
| `test_apf.py` | 10 | APF 포텐셜 장 계산 |
| `test_cbs.py` | 8 | CBS 격자 노드 |
| `test_resolution_advisory.py` | 6 | 어드바이저리 생성 |
| `test_flight_path_planner.py` | 8 | A* 경로 계획 · NFZ 회피 |
| `test_airspace_controller.py` | 9 | 1 Hz 제어 루프 |
| `test_analytics.py` | 14 | 이벤트 수집 · 지표 계산 |
| `test_simulator_scenarios.py` | 8 | 통합 시나리오 |

---

## 🔧 의존성

```
simpy>=4.1          # 이산 이벤트 시뮬레이션
numpy>=1.24         # 수치 계산
scipy>=1.11         # Voronoi, 공간 계산
dash>=2.17          # 3D 대시보드
plotly>=5.20        # 3D 시각화
joblib>=1.3         # Monte Carlo 병렬 실행
pandas>=2.1         # 결과 DataFrame
pyarrow>=14.0       # Parquet 저장
pyyaml>=6.0         # 설정 파일
```

---

## 📜 라이선스

MIT License — [LICENSE](LICENSE) 참조

---

## 🎓 참고 문헌

1. Reynolds, C. W. (1987). *Flocks, Herds, and Schools: A Distributed Behavioral Model.* SIGGRAPH.
2. Khatib, O. (1986). *Real-Time Obstacle Avoidance for Manipulators and Mobile Robots.* IJRR.
3. Sharon et al. (2015). *Conflict-Based Search for Optimal Multi-Agent Pathfinding.* AAAI.
4. NASA UTM Project Documentation (2023). *UTM Research Transition Team.* NASA.

---

<div align="center">

**Made with ❤️ by 장선우**
국립 목포대학교 드론기계공학과

</div>
