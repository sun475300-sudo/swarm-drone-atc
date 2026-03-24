# SDACS — 군집드론 공역통제 자동화 시스템

> **Swarm Drone Air Traffic Control System**
> SimPy 기반 이산 사건 시뮬레이션으로 최대 500기 드론의 공역을 자동 관제합니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [디렉터리 구조](#2-디렉터리-구조)
3. [아키텍처](#3-아키텍처)
4. [핵심 모듈](#4-핵심-모듈)
5. [실행 방법](#5-실행-방법)
6. [시나리오](#6-시나리오)
7. [설정 파일](#7-설정-파일)
8. [테스트](#8-테스트)
9. [시각화 대시보드](#9-시각화-대시보드)
10. [Docker 환경](#10-docker-환경)
11. [현재 상태 및 기술 부채](#11-현재-상태-및-기술-부채)

---

## 1. 프로젝트 개요

SDACS(Swarm Drone Air Traffic Control System)는 군집드론 운용 환경에서 자동화된 공역 통제를 수행하는 Python 시뮬레이션 프레임워크입니다.

| 항목 | 내용 |
|---|---|
| 시뮬레이션 엔진 | SimPy 이산 사건(Discrete-Event) |
| 제어 루프 | 1 Hz (공역 컨트롤러), 10 Hz (개별 드론) |
| 최대 드론 수 | 500기 (Monte Carlo 스윕 기준) |
| 충돌 회피 | APF (인공 포텐셜 장) + CBS (Conflict-Based Search) |
| 공역 분할 | Voronoi 기반 동적 구역 재할당 (10초 주기) |
| 경로 계획 | 격자 A* + 실시간 재계획 |
| 기상 모델 | 상수풍 / 변동풍(돌풍) / 풍단(Wind Shear) |

---

## 2. 디렉터리 구조

```
swarm-drone-atc/
├── main.py                        # CLI 진입점 (simulate / scenario / monte-carlo / visualize)
├── pyproject.toml                 # 패키지 메타데이터 및 pytest 설정
├── requirements.txt               # 핵심 의존성
├── requirements/
│   ├── base.txt                   # 공통 런타임 의존성
│   ├── dev.txt                    # 개발/테스트 도구
│   ├── simulation.txt             # 시뮬레이션 전용 (joblib, pyarrow)
│   ├── visualization.txt          # 시각화 전용 (Plotly, Dash)
│   └── physics.txt                # 물리 계층 (mavsdk, pymavlink — 선택)
├── src/airspace_control/          # 핵심 도메인 라이브러리
│   ├── agents/                    # DroneState, DroneProfile
│   ├── avoidance/                 # AdvisoryGenerator (충돌 회피 어드바이저리)
│   ├── comms/                     # CommunicationBus, 메시지 타입
│   ├── controller/                # AirspaceController (1 Hz 제어 루프)
│   ├── planning/                  # FlightPathPlanner (A*), Waypoint / Route
│   └── utils/                     # 좌표 변환, 기하 연산
├── simulation/
│   ├── engine.py                  # SimulationEngine (고수준 런처)
│   ├── simulator.py               # SwarmSimulator + _DroneAgent (SimPy 프로세스)
│   ├── metrics.py                 # SimulationMetrics (결과 집계)
│   ├── analytics.py               # SimulationAnalytics (이벤트 로깅)
│   ├── scenario_runner.py         # 시나리오 YAML 로드 및 반복 실행
│   ├── monte_carlo.py             # Monte Carlo 파라미터 스윕
│   ├── monte_carlo_runner.py      # MC 러너 래퍼
│   ├── weather.py                 # WindModel (상수/변동/풍단)
│   ├── apf_engine/apf.py          # APF 충돌 회피 엔진
│   ├── cbs_planner/cbs.py         # CBS 다중 에이전트 경로 계획
│   └── voronoi_airspace/          # Voronoi 공역 분할
├── visualization/
│   ├── dashboard.py               # Plotly Dash 3D 대시보드
│   └── simulator_3d.py            # 3D 시각화 유틸리티
├── config/
│   ├── default_simulation.yaml    # 기본 시뮬레이션 설정
│   ├── airspace_zones.yaml        # 공역 구역 / NFZ / 비행 회랑 / 착륙 패드
│   ├── drone_profiles.yaml        # 드론 기체 프로파일 (배달/감시/응급/레저)
│   ├── monte_carlo.yaml           # MC 스윕 파라미터 및 SLA 수락 기준
│   └── scenario_params/           # 7개 시나리오 YAML
├── tests/                         # pytest 단위·통합 테스트 (63개, 전체 통과)
├── data/seeds/validated_seeds.json # 회귀 테스트용 검증 시드 목록
├── docker-compose.yml             # Redis / vLLM / Backend / Dashboard / SITL
└── run_vllm.sh                    # 관제 AI용 vLLM 서버 기동 스크립트
```

---

## 3. 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    SimulationEngine                     │
│  seed / duration_s / drone_count / scenario_overrides  │
└────────────────────────┬────────────────────────────────┘
                         │ 생성·구동
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  _DroneAgent(×N)  AirspaceController  SimulationAnalytics
  (10 Hz SimPy)     (1 Hz SimPy)        (이벤트 로깅)
         │               │
         │  TelemetryMsg │ ClearanceRequest
         ▼               ▼
      CommunicationBus (지연/손실 모델링)
         │
         ├── FlightPathPlanner  (A* 경로 + 재계획)
         ├── AdvisoryGenerator  (충돌 회피 어드바이저리)
         ├── FlightPriorityQueue(우선순위 허가 큐)
         └── APF Engine         (실시간 포텐셜 장 계산)
```

**데이터 흐름**

1. 드론 에이전트가 10 Hz 루프에서 APF 힘을 계산해 이동
2. 매 틱마다 `TelemetryMessage` 를 `CommunicationBus` 로 발행
3. `AirspaceController` 가 1 Hz 로 텔레메트리 수신 → CPA(최근접점) 예측
4. 충돌 예측 시 `AdvisoryGenerator` 가 `ResolutionAdvisory` 를 생성·발행
5. 드론은 어드바이저리를 수신해 CLIMB / DESCEND / EVADE_APF / HOLD 기동 수행
6. Voronoi 분할이 10초마다 갱신되어 구역별 우선순위 재조정

---

## 4. 핵심 모듈

### 4-1. 드론 상태 (`src/airspace_control/agents/drone_state.py`)

| 항목 | 설명 |
|---|---|
| `FlightPhase` | GROUNDED / TAKEOFF / ENROUTE / HOLDING / LANDING / FAILED / RTL / EVADING |
| `CommsStatus` | NOMINAL / DEGRADED / LOST |
| `FailureType` | NONE / MOTOR_FAILURE / BATTERY_CRITICAL / GPS_LOSS / COMMS_LOSS / SENSOR_FAILURE |

### 4-2. 드론 프로파일 (`src/airspace_control/agents/drone_profiles.py`)

| 프로파일 | 최대속도 | 순항속도 | 지속시간 | 통신거리 | 우선순위 |
|---|---|---|---|---|---|
| COMMERCIAL_DELIVERY | 15 m/s | 10 m/s | 30분 | 2 km | 2 |
| SURVEILLANCE | 20 m/s | 12 m/s | 45분 | 3 km | 2 |
| EMERGENCY | 25 m/s | 20 m/s | 20분 | 2 km | 1 (최고) |
| RECREATIONAL | 10 m/s | 5 m/s | 15분 | 500 m | 3 |

### 4-3. 충돌 회피 (`src/airspace_control/avoidance/resolution_advisory.py`)

`AdvisoryGenerator.generate()` 우선순위 결정 규칙:

| 조건 | 어드바이저리 타입 |
|---|---|
| 위협 드론 FAILED | `HOLD` |
| CPA 시간 < 10초 | `EVADE_APF` |
| 자기 고도 ≤ 위협 고도 | `DESCEND` |
| 자기 고도 > 위협 고도 | `CLIMB` |

### 4-4. APF 엔진 (`simulation/apf_engine/apf.py`)

```
F_total = F_goal + Σ F_repulsive(obstacle) + F_wind
```

- `batch_compute_forces()` : 모든 드론에 대한 힘 벡터 일괄 계산 (NumPy 벡터화)
- `force_to_velocity()` : 힘 벡터 → 제한 속도 변환

### 4-5. CBS 계획기 (`simulation/cbs_planner/cbs.py`)

Sharon et al. (2015) 알고리즘 구현.

- **High Level**: 충돌 트리(CT) 탐색 — 제약 조건 추가하며 최적 경로 집합 탐색
- **Low Level**: 개별 드론 시공간 A* (제약 조건 적용)

---

## 5. 실행 방법

### 설치

```bash
pip install -r requirements.txt
```

### 단일 시뮬레이션

```bash
python main.py simulate --drones 100 --duration 600 --seed 42
```

### 시나리오 목록 확인

```bash
python main.py scenario --list
```

### 특정 시나리오 실행

```bash
python main.py scenario weather_disturbance --runs 3 --seed 42
```

### Monte Carlo 파라미터 스윕

```bash
# 빠른 스윕 (960회, ~4분 / 16코어)
python main.py monte-carlo --mode quick

# 전체 스윕 (38,400회, ~3.3시간 / 16코어)
python main.py monte-carlo --mode full
```

### 3D 대시보드 실행

```bash
python main.py visualize --drones 30 --duration 120 --port 8050
# → http://127.0.0.1:8050
```

---

## 6. 시나리오

`config/scenario_params/` 에 7개 시나리오가 정의되어 있습니다.

| 파일 | 시나리오 ID | 설명 |
|---|---|---|
| `high_density.yaml` | s01_normal_high_density | 정상 고밀도 교통 — 처리량 한계 및 기준선 충돌률 검증 |
| `emergency_failure.yaml` | s02_emergency_drone_failure | 비행 중 드론 장애 — 비상착륙 우선순위 및 장애 처리 검증 |
| `route_conflict.yaml` | — | 교차 경로 충돌 해소 검증 |
| `mass_takeoff.yaml` | — | 대규모 동시 이륙 처리 검증 |
| `weather_disturbance.yaml` | s06_weather_disturbance | 기상 교란(바람) 하 경로 추적 강건성 검증 |
| `comms_loss.yaml` | — | 통신 두절 Lost-link 프로토콜 검증 |
| `adversarial_intrusion.yaml` | — | 침입 드론 탐지 및 경보 발령 검증 |

---

## 7. 설정 파일

### `config/default_simulation.yaml` — 주요 파라미터

| 키 | 기본값 | 설명 |
|---|---|---|
| `simulation.duration_minutes` | 10 | 시뮬레이션 시간 |
| `simulation.time_step_hz` | 10 | 드론 에이전트 틱 |
| `simulation.control_hz` | 1 | 공역 컨트롤러 틱 |
| `airspace.bounds_km` | ±5 km × 120 m | 공역 범위 |
| `separation_standards.lateral_min_m` | 50 m | 횡방향 최소 이격 |
| `separation_standards.vertical_min_m` | 15 m | 수직 최소 이격 |
| `separation_standards.conflict_lookahead_s` | 90 s | 충돌 예측 전망 시간 |
| `drones.default_count` | 100 | 기본 드론 수 |

### `config/airspace_zones.yaml` — 공역 구조

- **구역**: A(서북), B(동북), C(서남), D(동남) — 일반 공역
- **NFZ**: NFZ_CENTER — 중심 1 km² 비행 금지 구역
- **비행 회랑**: COR_EW(동서, 60 m), COR_NS(남북, 80 m)
- **착륙 패드**: PAD_NW / NE / SW / SE (수용 5기) + PAD_CENTER (수용 10기)

### `config/monte_carlo.yaml` — SLA 수락 기준

| 지표 | 목표치 |
|---|---|
| 충돌률 | 0 건 / 1,000비행시간 |
| 근접 위반율 | < 0.1 건 / 100비행시간 |
| 분쟁 해소율 | ≥ 99.5 % |
| 경로 효율 (실제/계획) | ≤ 1.15 |
| 비상 대응 p50 | ≤ 2 s |
| 비상 대응 p99 | ≤ 10 s |
| 침입 탐지 p90 | ≤ 5 s |

---

## 8. 테스트

```bash
pip install -r requirements/dev.txt
pytest                          # 전체 (63개 테스트, 전체 통과)
pytest tests/test_apf.py -v     # 특정 모듈
pytest --cov=src --cov=simulation --cov-report=term-missing
```

| 테스트 파일 | 내용 |
|---|---|
| `test_airspace_controller.py` | AirspaceController 단위 테스트 |
| `test_analytics.py` | SimulationAnalytics 이벤트 로깅 |
| `test_apf.py` | APF 힘 계산 및 회피 동작 |
| `test_cbs.py` | CBS 다중 에이전트 경로 계획 |
| `test_flight_path_planner.py` | A* 경로 계획 및 장애물 회피 |
| `test_resolution_advisory.py` | AdvisoryGenerator 어드바이저리 생성 |
| `test_simulator_scenarios.py` | 통합 시나리오 시뮬레이션 |

---

## 9. 시각화 대시보드

Plotly Dash 기반 3D 인터랙티브 대시보드를 제공합니다.

- 드론 궤적 3D 시각화 (최대 20기 개별 표시)
- 배터리 잔량 컬러맵 (최종 위치)
- NFZ 경계 및 비행 회랑 표시
- 시간 슬라이더로 재생 컨트롤
- 다크 테마 (`plotly_dark`)

---

## 10. Docker 환경

```bash
# 기본 (Redis + Backend + Dashboard)
docker-compose up

# GPU + vLLM 포함 (관제 AI)
docker-compose --profile full up

# Gazebo SITL 포함 (Hardware-in-the-Loop)
docker-compose --profile simulation up
```

| 서비스 | 포트 | 설명 |
|---|---|---|
| redis | 6379 | 이벤트 버스 / 상태 캐시 |
| vllm | 8000 | 관제 AI (Qwen2.5-7B, GPU 필요) |
| backend | 8080 | FastAPI 백엔드 |
| dashboard | 3000 | 프론트엔드 대시보드 |
| sitl | host | PX4 Gazebo SITL (광주, 35.1595°N 126.8526°E) |

### vLLM 서버 단독 실행

```bash
# 기본 (Qwen/Qwen2.5-7B-Instruct, 포트 8000)
bash run_vllm.sh

# 커스텀 모델 / 포트
bash run_vllm.sh LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct 8001
```

---

## 11. 현재 상태 및 기술 부채

### ✅ 구현 완료

- SimPy 기반 이산 사건 시뮬레이션 엔진
- APF 충돌 회피 엔진 (NumPy 벡터화)
- CBS 다중 에이전트 경로 계획
- Voronoi 동적 공역 분할
- AirspaceController (1 Hz 제어 루프)
- 통신 버스 (지연/손실 모델링)
- 7종 시나리오 파라미터 정의
- Monte Carlo 파라미터 스윕 (joblib 병렬)
- 기상 모델 (상수풍 / 변동풍 / 풍단)
- Plotly Dash 3D 대시보드
- pytest 단위·통합 테스트 63개 (전체 통과)

### 🔧 미완성 / 개선 필요

- **백엔드 서비스** (`docker-compose.yml` 의 `backend`, `dashboard` 서비스용 `Dockerfile` 및 소스 미포함)
- **검증 시드 목록** (`data/seeds/validated_seeds.json`) — 현재 빈 배열, 회귀 테스트 시드 채워야 함
- **`simulation/monte_carlo_runner.py`** — `monte_carlo.py` 와 역할 중복, 통합 필요
- **물리 계층** (`requirements/physics.txt`) — mavsdk / pymavlink 실제 드론 연동 미구현
- **LLM 관제 AI 통합** — vLLM 서버 기동 스크립트만 존재, 컨트롤러와의 실제 연동 미구현
- **`config/drone_profiles.yaml`** — YAML 정의가 있으나 코드에서 직접 파이썬 `DRONE_PROFILES` dict 사용 (YAML 로딩 연동 누락)

---

## 라이선스

MIT License — © jangsunwoo
