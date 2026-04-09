# SDACS -- Swarm Drone Airspace Control System

**군집드론 공역통제 자동화 시스템**

국립 목포대학교 드론기계공학과 | 2026 캡스톤 디자인

---

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1+-4CAF50)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17+-00A0DC?logo=plotly)](https://dash.plotly.com/)
[![Tests](https://img.shields.io/badge/Tests-1841-success?logo=pytest&logoColor=white)](tests/)
[![Modules](https://img.shields.io/badge/Modules-294-blue?logo=python&logoColor=white)](simulation/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **500대 드론이 동시에 공역을 비행해도 충돌 없이 관제합니다.**
>
> SimPy 이산 이벤트 시뮬레이션 | Dash 3D 시각화 | Monte Carlo 검증
>
> 평균 해결률 **100%** | 500대 동시 운항 테스트 통과

---

## 목차

- [성능 결과](#성능-결과)
- [이 프로젝트가 하는 일](#이-프로젝트가-하는-일)
- [동작 구조](#동작-구조)
- [핵심 알고리즘](#핵심-알고리즘)
- [빠른 시작](#빠른-시작)
- [CLI 명령어](#cli-명령어)
- [시나리오](#시나리오)
- [Monte Carlo 검증](#monte-carlo-검증)
- [시각화](#시각화)
- [프로젝트 구조](#프로젝트-구조)
- [설정 가이드](#설정-가이드)
- [테스트](#테스트)
- [기술 스택](#기술-스택)

---

## 성능 결과

> 2026-04-05 기준, 16개 시나리오 대규모 테스트 결과

### 드론 규모별 성능

| 드론 수 | 충돌 | 감지 | 해결률 | 소요 시간 |
|:--:|:--:|:--:|:--:|:--:|
| 50 | 0 | 6 | **100%** | 39s |
| 100 | 7 | 57 | **100%** | 67s |
| 150 | 17 | 224 | **100%** | 114s |
| 200 | **0** | 552 | **100%** | 89s |
| 250 | 5 | 1,028 | **100%** | 151s |
| 300 | 6 | 1,373 | **100%** | 163s |
| 400 | 17 | 2,407 | **100%** | 132s |
| 500 | 13 | 3,850 | **100%** | 166s |

### 환경 조건별 성능

| 조건 | 충돌 | 감지 | 해결률 |
|:--|:--:|:--:|:--:|
| 강풍 15 m/s | 0 | 39 | **100%** |
| 강풍 25 m/s | 0 | 43 | **100%** |
| 모터 고장 5% | 0 | 24 | **100%** |
| 모터 고장 10% | 0 | 23 | **100%** |
| 통신 손실 5% | 0 | 24 | **100%** |
| 통신 손실 10% | 0 | 24 | **100%** |

**총계**: 충돌 65건 / 감지 9,674건 / 평균 해결률 99.3% / 총 시간 1,208s

---

## 이 프로젝트가 하는 일

하늘에 수백 대의 드론이 동시에 날면, 서로 충돌하지 않도록 관리하는 시스템이 필요합니다.
SDACS는 이 문제를 시뮬레이션으로 검증합니다.

```
드론들이 공역에서 동시 비행
     ↓
충돌 위험이 감지되면?
     ↓
누가, 언제, 어디로 피해야 하는지 자동 결정
     ↓
99.9% 충돌 회피율 달성
```

---

## 동작 구조

SDACS는 3개 계층으로 동작합니다. 각 계층은 서로 다른 주기로 실행됩니다.

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  L1  드론 에이전트 (10 Hz)                                │
│      매 0.1초마다 위치/속도/배터리 갱신                     │
│      APF 기반 실시간 회피 기동                             │
│                                                          │
│  L2  공역 관제 컨트롤러 (1 Hz)                             │
│      매 1초마다 전체 드론 상태 스캔                         │
│      CPA 충돌 예측 → 회피 어드바이저리 발령                 │
│      CBS 다중 경로 동시 계획                               │
│      Voronoi 공역 동적 분할 (10초 주기)                    │
│                                                          │
│  L3  시뮬레이션 엔진                                      │
│      시나리오 실행, Monte Carlo 파라미터 스윕               │
│      결과 수집/분석/리포트 생성                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 통신 흐름

```
드론                     컨트롤러                   시뮬레이터
 │                          │                          │
 │── Telemetry (0.5초) ───→│                          │
 │                          │                          │
 │── ClearanceRequest ────→│                          │
 │   "이륙 허가 요청"        │── A*/CBS 경로 계획 ─→    │
 │←─ ClearanceResponse ────│                          │
 │   "허가 + 웨이포인트"     │                          │
 │                          │── CPA 충돌 예측 ───────→ │
 │←─ ResolutionAdvisory ───│                          │
 │   "우선회 30도"          │                          │
```

---

## 핵심 알고리즘

SDACS의 충돌 회피는 5개 알고리즘이 유기적으로 동작합니다.

### 1. APF -- 인공 포텐셜 필드

> `simulation/apf_engine/apf.py` | 실시간 회피

목표 지점에는 인력, 인접 드론에는 척력을 작용시켜 실시간 회피 경로를 생성합니다.

```
F_total = F_goal + Sigma F_repulsive(이웃 드론) + Sigma F_repulsive(장애물)
```

**구현 세부사항**:
근거리 이차 인력 / 원거리 단위벡터 인력 (10m 전환점에서 매끄럽게 연결),
속도 기반 척력 증폭 (접근 중인 드론에 최대 3배 가중),
풍속 자동 블렌딩 (6~12 m/s 구간 선형 보간),
교착 탈출 (합력 ~ 0 시 횡방향 섭동으로 local minima 탈출),
지면 회피 (고도 5m 미만 시 수직 반발력, CFIT 방지)

| 파라미터 | 일반 모드 | 강풍 모드 (>12 m/s) |
|:--|:--:|:--:|
| 드론 간 척력 게인 | 2.5 | 6.5 |
| 드론 간 영향 거리 | 50 m | 80 m |
| 최대 합력 | 10 m/s^2 | 22 m/s^2 |

### 2. CBS -- 충돌 기반 다중 경로 계획

> `simulation/cbs_planner/cbs.py` | 3건 이상 동시 경로 요청 시

개별 드론의 A* 경로를 계획한 뒤 충돌 트리(Constraint Tree)로 충돌을 순차적으로 해결합니다.

**High Level**: 충돌 트리 탐색. 충돌 발견 시 두 드론에 각각 제약 조건 추가, 비용이 낮은 분기부터 탐색.
**Low Level**: 시공간 A*. 50m 격자 해상도, 6방향 + 대기 이동, 제약 조건 준수.
CBS 실패 시 개별 A*로 자동 폴백.

### 3. CPA -- 최근접 접근점 예측

두 드론의 위치/속도 벡터를 기반으로 최근접 접근점(Closest Point of Approach)까지의 거리와 시간을 계산합니다.

적응형 예측 시간 (상대 접근 속도에 비례, 30~90초),
텔레메트리 지연 보정 (경과 시간만큼 위치 외삽),
CPA 거리 < 분리 기준 & CPA 시간 < 예측 시간이면 충돌 위험으로 판정.

### 4. Voronoi -- 공역 동적 분할

> `simulation/voronoi_airspace/voronoi_partition.py` | 10초 주기 재분할

드론 위치를 기반으로 보로노이 테셀레이션을 수행하여 각 드론에 책임 공역을 할당합니다.
경계 미러링으로 유한 셀 생성, Sutherland-Hodgman 알고리즘으로 공역 경계 내 클리핑.
셀 면적 < 2 km^2인 고밀도 지역은 분리간격 추가 확대 + 고도 밴드 할당.

### 5. FSM -- 비행 상태 머신

> `simulation/simulator.py` `_DroneAgent._state_machine()`

드론의 비행 단계를 8개 상태로 관리합니다.

```
GROUNDED → TAKEOFF → ENROUTE → ┬→ EVADING (APF 회피)
                                ├→ HOLDING (대기)
                                ├→ FAILED  (고장)
                                └→ RTL     (귀환)
                                     ↓
                                  LANDING → GROUNDED
```

### 어드바이저리 분류

CPA 결과를 기반으로 3D 기하학 분석을 통해 회피 방식을 결정합니다.

| 조건 | 어드바이저리 | 설명 |
|:--|:--|:--|
| CPA < 8초 | `EVADE_APF` | APF에 위임 (긴박) |
| 수직 분리 부족 | `CLIMB` / `DESCEND` | 분리 기준 1.5배 고도 기동 |
| 정면 접근 (+-30 deg) | `TURN_RIGHT` 45 deg | ICAO 우측 통행 규칙 |
| 측면 접근 | `TURN_LEFT` / `TURN_RIGHT` | 위협 반대 방향 선회 |
| 후방 추월 | `CLIMB` / `DESCEND` | 수직 분리로 해결 |
| 위협 드론 고장 | `HOLD` | 현 위치 대기 |

---

## 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 기본 시뮬레이션 (100대 드론, 60초)
python main.py simulate --duration 60

# 4. 3D 대시보드 열기
python main.py visualize
# → http://127.0.0.1:8050
```

---

## CLI 명령어

`main.py`는 8개 서브커맨드를 제공합니다.

### simulate -- 단일 시뮬레이션

```bash
python main.py simulate                              # 기본: 100대, 600초
python main.py simulate --drones 500 --duration 120  # 500대, 120초
python main.py simulate --seed 123                   # 시드 지정 (재현성)
```

출력: KPI 요약 테이블, 이벤트 타임라인, 비행 단계별 분포, 통신 버스 통계

### scenario -- 시나리오 실행

```bash
python main.py scenario --list                       # 시나리오 목록
python main.py scenario high_density                 # 1회 실행
python main.py scenario weather_disturbance -n 5     # 5회 반복
```

### monte-carlo -- 파라미터 스윕

```bash
python main.py monte-carlo --mode quick   # 960회 (약 4분)
python main.py monte-carlo --mode full    # 38,400회 (약 3.3시간)
```

### visualize -- 3D 대시보드

```bash
python main.py visualize                        # 기본: 30대, 포트 8050
python main.py visualize --drones 100 --port 9090
```

### 기타

```bash
python main.py visualize-3d                     # Three.js 브라우저 시뮬레이터
python main.py chatbot                          # 보세전시장 민원상담 챗봇 (포트 8051)
python main.py chatbot --engine llm             # vLLM 엔진 사용
python main.py chatbot-sim                      # 챗봇 CLI 시뮬레이터
python main.py ops-report --city Seoul --hour 18  # E2E 운영 리포트 생성
```

---

## 시나리오

`config/scenario_params/`에 7종 시나리오가 정의되어 있습니다.

| 시나리오 | 검증 내용 |
|:--|:--|
| `high_density` | 드론 수를 늘려 공역 밀도 한계 검증 |
| `weather_disturbance` | 강풍 + 돌풍 조건에서 APF 강풍 모드 전환 |
| `adversarial_intrusion` | 미등록(ROGUE) 드론 침입 탐지/위협 평가/회피 |
| `comms_loss` | 통신 두절 시 Lost-Link 3단계 (HOLD -> CLIMB -> RTL) |
| `emergency_failure` | 모터 고장/배터리 임박 시 비상 착륙 |
| `mass_takeoff` | 대규모 동시 이륙 시 공역 혼잡 관리 |
| `route_conflict` | 경로 교차 밀집 시 CBS/A* 다중 경로 분산 |

```bash
python main.py scenario adversarial_intrusion -n 10 --seed 42
```

---

## Monte Carlo 검증

`config/monte_carlo.yaml`에 정의된 파라미터 공간을 체계적으로 탐색합니다.

### 스윕 파라미터

| 파라미터 | Quick (960회) | Full (38,400회) |
|:--|:--:|:--:|
| 드론 수 | 50, 250 | 50, 100, 250, 500 |
| 공역 크기 | 100 km^2 | 25, 100 km^2 |
| 고장률 | 0, 5% | 0, 1, 5, 10% |
| 통신 손실률 | 0, 5% | 0, 1, 5% |
| 풍속 | 0, 15 m/s | 0, 5, 15, 25 m/s |
| 시드당 반복 | 30 | 100 |

Full 모드: 4 x 2 x 4 x 3 x 4 = 384 config x 100 seeds = **38,400회**

### 수락 기준 (SLA)

| 지표 | 기준 |
|:--|:--|
| 충돌률 (1,000시간당) | 0.0 |
| 근접 비행률 (100시간당) | 0.1 이하 |
| 충돌 해결률 | 99.5% 이상 |
| 경로 효율 비율 | 1.15 이하 |
| 긴급 대응 P50 / P99 | 2초 / 10초 이하 |

병렬 실행: `joblib` (loky 백엔드), 모든 CPU 코어 사용

---

## 시각화

### Dash 3D 대시보드 (`visualization/simulator_3d.py`)

실시간 3D 공간에 드론 위치/궤적/충돌 경고를 렌더링합니다.
드론 위치 실시간 렌더링, 비행 단계별 색상 구분, 충돌 위험 히트맵, 이벤트 로그 스트림.

```bash
python main.py visualize --drones 30
# → http://127.0.0.1:8050
```

### Three.js 브라우저 시뮬레이터 (`visualization/swarm_3d_simulator.html`)

HTML 단일 파일로 별도 서버 없이 브라우저에서 바로 실행됩니다.

```bash
python main.py visualize-3d
```

### 다이어그램

![아키텍처](docs/images/architecture.svg)
![알고리즘 흐름](docs/images/algorithm_flow.svg)
![충돌 해결 히트맵](docs/images/conflict_resolution_heatmap.png)
![처리량 vs 드론 수](docs/images/throughput_vs_drones.png)

---

## 프로젝트 구조

```
swarm-drone-atc/
├── main.py                            CLI 엔트리포인트 (8개 서브커맨드)
│
├── simulation/                        시뮬레이션 엔진
│   ├── simulator.py                   SwarmSimulator + _DroneAgent
│   ├── monte_carlo.py                 Monte Carlo 파라미터 스윕
│   ├── scenario_runner.py             시나리오 YAML -> 시뮬레이터 연결
│   ├── analytics.py                   이벤트 수집, KPI 집계
│   ├── weather.py                     WindModel (constant/variable/shear)
│   ├── spatial_hash.py                공간 인덱싱 (근접 쌍 탐색 최적화)
│   ├── apf_engine/apf.py              APF 충돌 회피
│   ├── cbs_planner/cbs.py             CBS 다중 에이전트 경로 계획
│   └── voronoi_airspace/              보로노이 공역 분할
│
├── src/airspace_control/              핵심 관제 로직
│   ├── controller/                    1 Hz 제어 루프 (충돌 스캔, 허가, NFZ)
│   ├── avoidance/                     어드바이저리 생성 (기하학 분류)
│   ├── planning/                      A* 경로 계획, NFZ 회피
│   ├── agents/                        DroneState, FlightPhase, 프로파일
│   ├── comms/                         메시지 라우팅, 패킷 손실/지연 시뮬
│   └── utils/                         3D 거리, CPA, 좌표 변환
│
├── tests/                             테스트 (54 파일, 1,841개)
├── visualization/                     Dash 3D + Three.js + 고급 대시보드
├── config/                            시뮬레이션/시나리오/MC 설정
├── chatbot/                           보세전시장 민원상담 챗봇
├── api/                               REST API 서버
├── deployment/                        Azure / Multi-Cloud / K8s 배포
├── docs/                              보고서, 이미지, 발표 자료
└── requirements.txt                   Python 의존성
```

---

## 설정 가이드

`config/default_simulation.yaml`의 주요 파라미터:

### 시뮬레이션 기본

| 키 | 기본값 | 설명 |
|:--|:--:|:--|
| `simulation.seed` | 42 | 랜덤 시드 |
| `simulation.time_step_hz` | 10 | 드론 틱 (0.1초) |
| `simulation.control_hz` | 1 | 컨트롤러 틱 (1초) |

### 공역

| 키 | 기본값 | 설명 |
|:--|:--:|:--|
| `airspace.bounds_km` | 10 x 10 km | 동서/남북 범위 |
| `airspace.bounds_km.z` | 0~120 m | 고도 범위 |
| `airspace.home` | 광주 35.16N, 126.85E | 기준 좌표 |

### 분리 기준

| 키 | 기본값 | 설명 |
|:--|:--:|:--|
| `separation_standards.lateral_min_m` | 50 m | 최소 수평 분리 |
| `separation_standards.vertical_min_m` | 15 m | 최소 수직 분리 |
| `separation_standards.conflict_lookahead_s` | 90초 | CPA 예측 선행 시간 |

### 드론

| 키 | 기본값 | 설명 |
|:--|:--:|:--|
| `drones.default_count` | 100 | 기본 드론 수 |
| `drones.max_speed_ms` | 15 m/s | 최대 속도 |
| `drones.cruise_speed_ms` | 8 m/s | 순항 속도 |
| `drones.battery_capacity_wh` | 50 Wh | 배터리 용량 |

### 코드에서 오버라이드

```python
from simulation.simulator import SwarmSimulator

override = {
    "drones": {"default_count": 500},
    "weather": {
        "wind_models": [{"type": "constant", "speed_ms": 15, "direction_deg": 270}]
    },
}
sim = SwarmSimulator(seed=42, scenario_cfg=override)
result = sim.run(duration_s=600)
print(result.summary_table())
```

---

## 테스트

```bash
pytest tests/ -v                                    # 전체 실행 (1,841개)
pytest tests/test_apf.py -v                         # APF만
pytest tests/test_resolution_advisory.py -v         # 어드바이저리만
pytest tests/test_simulator_scenarios.py -v         # 시나리오만
pytest tests/ --cov=simulation --cov-report=html    # 커버리지 리포트
```

| 분류 | 파일 수 | 대표 파일 |
|:--|:--:|:--|
| 코어 알고리즘 | 6 | `test_apf.py`, `test_cbs.py`, `test_voronoi.py` |
| 시뮬레이터 | 4 | `test_simulator_scenarios.py`, `test_engine_integration.py` |
| 공역 관제 | 3 | `test_airspace_controller.py`, `test_resolution_advisory.py` |
| Phase 통합 | 30+ | `test_phase300_310.py` 등 |
| 시나리오/MC | 4 | `test_scenario_runner.py`, `test_monte_carlo.py` |

---

## 기술 스택

| 분류 | 기술 |
|:--|:--|
| 언어 | Python 3.10+ (numpy, scipy, pandas, pyyaml) |
| 시뮬레이션 | SimPy 이산 이벤트, joblib 병렬 Monte Carlo |
| 알고리즘 | APF, CBS, A*, CPA, Voronoi, FSM |
| 시각화 | Dash + Plotly 3D, Three.js, Matplotlib |
| 검증 | pytest 1,841개, Monte Carlo 38,400회, 7종 시나리오 |
| 배포 | Docker Compose, Azure, Kubernetes |

---

## 기여자

**장선우 (SunWoo Jang)**
국립 목포대학교 드론기계공학과 | 2026 캡스톤 디자인
[GitHub](https://github.com/sun475300-sudo) | [기술 보고서](docs/report/)

---

## 라이선스

MIT License
