# 군집드론 공역통제 자동화 시스템 (SDACS)

**Swarm Drone Airspace Control System**

## 변경 이력 (Changelog)

| 날짜/시간 (KST) | 커밋 | 작업 내용 | 수정 파일 |
| --- | --- | --- | --- |
| 2026-03-26 08:19 | `b1a8b2f` | fix: ROGUE advisory guard, clearance NFZ validation, dead import removal | simulation/simulator.py, src/airspace_control/controller/airspace_controller.py |

---

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-4CAF50?style=for-the-badge)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17-00A0DC?style=for-the-badge&logo=plotly)](https://dash.plotly.com/)
[![Tests](https://img.shields.io/badge/Tests-74%20passed-brightgreen?style=for-the-badge)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**국립 목포대학교 드론기계공학과 캡스톤 디자인 (2026)**

[📖 기술 보고서](docs/report/SDACS_Technical_Report.docx) · [📊 성능 차트](docs/images/) · [🎥 시연 영상](#)

</div>

---

## 목차

1. [프로젝트 배경](#프로젝트-배경)
2. [시스템 개요](#시스템-개요)
3. [4계층 아키텍처](#4계층-아키텍처)
4. [핵심 알고리즘](#핵심-알고리즘)
5. [시나리오 검증 결과](#시나리오-검증-결과)
6. [Monte Carlo SLA](#monte-carlo-sla)
7. [빠른 시작](#빠른-시작)
8. [프로젝트 구조](#프로젝트-구조)
9. [테스트](#테스트)
10. [SC2 테스트베드](#sc2-테스트베드)
11. [개발 일정](#개발-일정)
12. [팀 정보](#팀-정보)
13. [참고 문헌](#참고-문헌)

---

## 프로젝트 배경

### 문제 인식

국내 등록 드론 수 **90만 대 돌파**, 연간 30% 이상 증가. 저고도 공역에서 택배 배송·농업 방제·UAM이 동시 운용되며 충돌 위험이 급증합니다.

| 기존 방식 | 문제점 |
|----------|--------|
| 고정형 레이더 | 설치 비용 수억원 + 6개월 공사, 소형 드론 탐지 한계 |
| K-UTM 중앙 집중식 | 단일 장애점(SPOF) 취약, 실시간성 부족 |
| 수동 관제 | 평균 5분 지연, 24시간 인력 비용 과다 |

### 우리의 해결책

> **"레이더 자체를 드론으로 대체"** — 이동형 가상 레이더 돔(Dome)

- 30분 내 긴급 배치 가능
- 탐지부터 회피 유도까지 End-to-End 자동화, 관제 인력 80% 절감
- 드론 추가만으로 관제 반경 선형 확장

---

## 시스템 개요

군집드론을 **이동형 가상 레이더 돔**으로 활용하여, 고정형 인프라 없이도 도심 저고도 공역을 실시간 감시하고 위협에 **자동 대응**하는 분산형 ATC 시뮬레이션 시스템입니다.

### 핵심 지표

| 항목 | 값 | 설명 |
|------|----|------|
| 충돌 예측 선제 | 90 s lookahead | CPA 기반 O(N²) 스캔, 1 Hz |
| 자동 어드바이저리 | 6종 | CLIMB / DESCEND / TURN_LEFT / TURN_RIGHT / EVADE_APF / HOLD |
| Monte Carlo 검증 | 38,400 회 | 384 configs × 100 seeds |
| 기상 모델 | 3종 | constant / variable(gust) / shear |
| 침입 탐지 | ROGUE 프로파일 | 미등록 드론 IntrusionAlert |
| 동적 공역 분할 | Voronoi | 10 s 주기 자동 갱신 |
| SC2 알고리즘 검증 | 14,200 회 | 게임 AI 환경 사전 검증 |

---

## 4계층 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — 사용자 인터페이스                                   │
│  CLI (main.py)  ·  3D Dash 대시보드  ·  pytest 74개           │
└───────────────────────────┬──────────────────────────────────┘
                            │ 명령 / 결과
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 3 — 시뮬레이션 엔진 (SimPy)                            │
│  SwarmSimulator  ·  WindModel(3종)  ·  Monte Carlo  ·  시나리오 │
└───────────────────────────┬──────────────────────────────────┘
                            │ 이벤트 / 상태
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 2 — 공역 제어 (ATC, 1 Hz)                              │
│  AirspaceController  ·  FlightPathPlanner(A*)  ·  Voronoi    │
└───────────────────────────┬──────────────────────────────────┘
                            │ 어드바이저리 / 허가
┌───────────────────────────▼──────────────────────────────────┐
│  Layer 1 — 드론 에이전트 (10 Hz)                               │
│  _DroneAgent  ·  APF 충돌 회피  ·  텔레메트리  ·  상태머신     │
└──────────────────────────────────────────────────────────────┘
```

### 핵심 데이터 흐름

```
_DroneAgent (10 Hz)
    │  TelemetryMessage (0.5 s 주기)
    ▼
CommunicationBus  (지연 20±5ms, 패킷손실 모델)
    │
    ▼
AirspaceController (1 Hz)
    ├── ClearanceRequest → A* 경로계획 → ClearanceResponse
    ├── O(N²) CPA 스캔 (90 s lookahead) → ResolutionAdvisory
    ├── ROGUE 감지 → IntrusionAlert (BROADCAST)
    └── 10 s 주기 Voronoi 공역 갱신
```

### 드론 비행 상태 기계

```
GROUNDED ──[허가 수신]──► TAKEOFF ──[순항고도]──► ENROUTE
    ▲                                               │    │
    │                                         [목적지] [충돌위협]
LANDING ◄──────────────────────────────────────────┘    ▼
    ▲                                             EVADING (APF)
RTL ◄──[배터리 임계]                                    │
FAILED ◄──[장애 주입]                           [회피 완료]──► ENROUTE
```

---

## 핵심 알고리즘

### 1. APF (인공 포텐셜 장)

충돌 회피 1차 방어선 — 드론 주변에 척력 필드를 생성하여 충돌을 회피합니다.

```
F_total = F_attractive(목표) + ΣF_repulsive(드론) + ΣF_repulsive(NFZ)

파라미터:
  인력:   k_att  = 1.0   (목표 방향)
  드론 척력: k_rep = 2.5,  d0 = 50 m
  장애물:  k_rep  = 5.0,  d0 = 30 m
  속도 보정: 접근 속도 비례 척력 2배 증폭
  포화:   max_force = 10 m/s²
```

### 2. CPA 기반 충돌 예측

```
rel_pos = pos_A - pos_B
rel_vel = vel_A - vel_B
t_cpa   = -dot(rel_pos, rel_vel) / ||rel_vel||²  (clamp 0~90 s)
CPA_dist = ||rel_pos + rel_vel × t_cpa||

CPA_dist < 50 m  →  충돌 예측  →  ResolutionAdvisory 발령
```

### 3. Resolution Advisory 분류 체계

```
입력: CPA 거리, CPA 시간, 상대 위치/속도, FlightPhase

분류 우선순위:
  1. threat.phase == FAILED      → HOLD        (상대 장애)
  2. cpa_t < 10 s               → EVADE_APF   (긴급 APF 회피)
  3. 수직 여유 > 30 m            → CLIMB / DESCEND
  4. 정면 충돌 (방위 ±30°)       → TURN_RIGHT  (항공 규칙)
  5. 그 외                       → TURN_LEFT / TURN_RIGHT

Lost-Link 3단계:
  Phase 1: HOLD    (loiter 30 s)
  Phase 2: CLIMB   (목표 고도 80 m)
  Phase 3: RTL     (자동 귀환)
```

### 4. Voronoi 동적 공역 분할

```
10 s 주기:
  1. 활성 드론 2D 위치 추출
  2. scipy.spatial.Voronoi 분할
  3. Sutherland-Hodgman 경계 클리핑
  4. Ray-casting 점-폴리곤 판정 (허가 처리 시 셀 침범 감지)
```

### 5. CBS (Conflict-Based Search)

```
High Level: 충돌 트리(CT) 탐색
  충돌 감지 → 제약 추가 → 재탐색 (최대 1,000 노드)

Low Level: 시공간 A* (개별 드론)
  격자 해상도: 50 m  |  시간스텝: 1 s  |  최대 시간: 200 스텝
```

### 드론 프로파일

| 타입 | 최대속도 | 순항속도 | 배터리 | 우선순위 |
|------|---------|---------|--------|---------|
| EMERGENCY | 25 m/s | 20 m/s | 60 Wh | **P1 최우선** |
| COMMERCIAL_DELIVERY | 15 m/s | 10 m/s | 80 Wh | P2 |
| SURVEILLANCE | 20 m/s | 12 m/s | 100 Wh | P2 |
| RECREATIONAL | 10 m/s | 5 m/s | 30 Wh | P3 |
| ROGUE (미등록) | 15 m/s | 8 m/s | 50 Wh | — |

---

## 시나리오 검증 결과

7개 시나리오 전량 실행 완료 (seed=42, 2026-03-25).

### 결과 요약표

| 시나리오 | 드론수 | 충돌 | 근접경고 | 해결률 | 경로효율 | 실행시간 |
|---------|------|------|---------|-------|---------|---------|
| high_density | 100 | 98 | 2,450 | **100.0 %** | 0.862 | 600 s |
| emergency_failure | 100 | 43 | 61 | 96.5 % | 1.051 | 600 s |
| comms_loss | 100 | 43 | 61 | 96.5 % | 1.051 | 600 s |
| mass_takeoff | 100 | 43 | 61 | 96.5 % | 1.051 | 600 s |
| adversarial_intrusion | 100 | 110 | 68 | 95.2 % | 1.650 | 900 s |
| route_conflict | 100 | 15 | 1 | 93.2 % | 0.215 | 120 s |
| weather_disturbance | 100 | 3,014 | 1,372 | 14.8 % | 2.664 | 600 s |

> `weather_disturbance` 해결률 14.8% — 강풍(shear) 조건에서 APF 파라미터 재조정 필요. 개선 항목으로 등록.

---

### 시나리오별 상세

```bash
# 고밀도 교통 관제 (100대, 600초)
python main.py scenario high_density --runs 1

# 기상 교란 (바람 3종: constant / gust / shear)
python main.py scenario weather_disturbance --runs 1

# 비상 장애 (5% 드론 모터/배터리 장애 주입)
python main.py scenario emergency_failure --runs 1

# 통신 두절 (Lost-link RTL 프로토콜)
python main.py scenario comms_loss --runs 1

# 침입 드론 탐지 (ROGUE 3기 + 정규 50기)
python main.py scenario adversarial_intrusion --runs 1

# 대규모 동시 이착륙 (이착륙 시퀀싱 스트레스)
python main.py scenario mass_takeoff --runs 1

# 경로 충돌 해소 (HEAD_ON / CROSSING / OVERTAKE)
python main.py scenario route_conflict --runs 1
```

---

## Monte Carlo SLA

### SLA 기준

| 지표 | 목표 | 비고 |
|------|------|------|
| 충돌률 | **0건 / 1,000 h** | 하드 요구사항 |
| Near-miss | ≤ 0.1건 / 100 h | 소프트 경고 |
| 충돌 해결률 | **≥ 99.5 %** | 어드바이저리 발령률 |
| 경로 효율 | ≤ 1.15 (actual/planned) | 우회 비용 |
| 어드바이저리 P50 | ≤ 2.0 s | 응답 지연 |
| 어드바이저리 P99 | ≤ 10.0 s | 최악 케이스 |
| 침입 탐지 P90 | ≤ 5.0 s | ROGUE 탐지 지연 |

### 파라미터 스윕 구성

```
Full sweep  (38,400 runs, ~3h on 16 cores)
  드론 수:   50 / 100 / 250 / 500
  면적:      25 / 100 km²
  장애율:    0 / 1 / 5 / 10 %
  통신 손실: 0 / 0.01 / 0.05
  바람:      0 / 5 / 15 / 25 m/s
  seeds:     100 per config

Quick sweep (960 runs, ~4 min)
  드론 수:   50 / 250
  장애율:    0 / 5 %
  바람:      0 / 15 m/s
  seeds:     30 per config
```

```bash
python main.py monte-carlo --mode quick   # ~4분
python main.py monte-carlo --mode full    # ~3시간 (16코어)
```

---

## 성능 분석

### O(N²) 처리량

| 드론 수 | 스캔 계산/초 (현재) | KDTree 최적화 후 |
|---------|------------------|----------------|
| 100대 | 4,950 | ~1,000 |
| 300대 | 44,850 | ~7,000 |
| 500대 | 124,750 | ~15,000 |

> 300대+ 운용 시 KDTree 공간 인덱스 도입 예정 (로드맵)

### 성능 차트 생성

```bash
python scripts/generate_charts.py --output-dir docs/images
```

| 파일 | 내용 |
|------|------|
| `throughput_vs_drones.png` | O(N²) vs KDTree 처리량 비교 |
| `advisory_latency.png` | 시나리오별 P50/P99 지연 |
| `scenario_kpi_radar.png` | KPI 레이더 차트 |
| `conflict_resolution_heatmap.png` | 드론 수 × 시간 해결률 히트맵 |

---

## 빠른 시작

### 설치

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
pip install -r requirements.txt
```

### 실행

```bash
# 시나리오 목록
python main.py scenario --list

# 시나리오 실행
python main.py scenario high_density --runs 1

# 기본 시뮬레이션 (600초, 100대)
python main.py simulate --duration 600 --seed 42

# Monte Carlo quick sweep (~4분)
python main.py monte-carlo --mode quick

# 3D 실시간 대시보드 → http://127.0.0.1:8050
python main.py visualize
```

### 3D 대시보드

- 실시간 3D 드론 위치 추적 (Plotly.js)
- 8개 시나리오 즉시 전환 드롭다운
- 하단 실시간 경보 로그 (충돌 / 근접경고 / 회피기동 / 어드바이저리)

---

## 프로젝트 구조

```
swarm-drone-atc/
├── main.py                          # CLI 진입점 (5개 서브커맨드)
├── config/
│   ├── default_simulation.yaml      # 기본 설정
│   ├── monte_carlo.yaml             # MC 파라미터 스윕 정의
│   └── scenario_params/             # 7개 시나리오 YAML
│
├── simulation/
│   ├── simulator.py                 # SwarmSimulator + _DroneAgent (SimPy)
│   ├── analytics.py                 # SimulationAnalytics + SimulationResult
│   ├── weather.py                   # WindModel 3종 (constant/gust/shear)
│   ├── scenario_runner.py           # YAML 시나리오 로더 + 실행기
│   ├── monte_carlo.py               # 파라미터 스윕 (Joblib 병렬)
│   ├── apf_engine/apf.py            # APF 배치 벡터 계산
│   ├── cbs_planner/cbs.py           # CBS 다중 드론 경로 계획
│   └── voronoi_airspace/            # Voronoi 2D 공역 분할
│
├── src/airspace_control/
│   ├── agents/drone_state.py        # DroneState + FlightPhase FSM
│   ├── agents/drone_profiles.py     # 5가지 드론 타입 정의
│   ├── controller/
│   │   ├── airspace_controller.py   # 1 Hz ATC 제어 루프
│   │   └── priority_queue.py        # 우선순위 허가 큐
│   ├── planning/
│   │   ├── flight_path_planner.py   # A* + replan_avoiding()
│   │   └── waypoint.py              # Route / Waypoint
│   ├── avoidance/
│   │   └── resolution_advisory.py   # AdvisoryGenerator (6종 분류)
│   ├── comms/
│   │   ├── communication_bus.py     # MAVLink 추상화 (지연/손실 모델)
│   │   └── message_types.py         # 메시지 타입 6종
│   └── utils/geo_math.py            # CPA / 거리 / 방위각
│
├── visualization/
│   └── simulator_3d.py              # Dash 3D 실시간 대시보드
│
├── scripts/
│   └── generate_charts.py           # 성능 차트 생성 (matplotlib 4종)
│
├── docs/
│   ├── report/SDACS_Technical_Report.docx  # A4 한국어 기술 보고서
│   └── images/                             # 성능 차트 + SVG 다이어그램
│
└── tests/                           # pytest 74개
    ├── test_apf.py                  # APF 포텐셜 장 (10)
    ├── test_cbs.py                  # CBS 격자 노드 (8)
    ├── test_resolution_advisory.py  # 어드바이저리 분류 (6)
    ├── test_flight_path_planner.py  # A* + replan (8)
    ├── test_airspace_controller.py  # 1 Hz 제어 루프 (9)
    ├── test_analytics.py            # KPI 수집 (14)
    ├── test_simulator_scenarios.py  # 통합 시나리오 (8)
    └── test_engine_integration.py   # SwarmSimulator E2E + Voronoi (11)
```

---

## 테스트

```bash
pytest tests/ -v              # 전체 실행
pytest tests/test_apf.py -v   # 특정 파일
```

### 커버리지

| 파일 | 수 | 대상 |
|------|---|------|
| `test_apf.py` | 10 | APF 포텐셜 장 계산 |
| `test_cbs.py` | 8 | CBS 격자 노드·해시 |
| `test_resolution_advisory.py` | 6 | 어드바이저리 분류 |
| `test_flight_path_planner.py` | 8 | A*·NFZ 회피·replan |
| `test_airspace_controller.py` | 9 | 1 Hz 제어 루프 |
| `test_analytics.py` | 14 | 이벤트 수집·KPI |
| `test_simulator_scenarios.py` | 8 | 통합 시나리오 |
| `test_engine_integration.py` | 11 | SwarmSimulator E2E·Voronoi |
| **합계** | **74** | |

---

## SC2 테스트베드

실제 드론 하드웨어 테스트 전, StarCraft II 환경에서 군집 알고리즘을 먼저 검증합니다.

| 장점 | 설명 |
|------|------|
| 내장 물리 엔진 | 충돌/회피 테스트 즉시 확인 |
| 빠른 반복 | 하드웨어 없이 10,000+ 시뮬레이션 |
| 1:1 매핑 | 저글링 유닛 → 드론 에이전트 직접 대응 |

**검증 결과:**
- 14,200회 SC2 시뮬레이션 완료
- 충돌 85% 감소 (12.3 → 1.8회/분)
- Boids 3규칙 + Authority FSM 통합 검증

별도 레포: [swarm-control-in-sc2bot](https://github.com/sun475300-sudo/swarm-control-in-sc2bot)

---

## 개발 일정

| 단계 | 기간 | 주요 산출물 | 상태 |
|------|------|------------|------|
| Phase 1: 설계 | 2026.01~03 | 아키텍처 설계, 알고리즘 설계 | 완료 |
| Phase 2: 구현 | 2026.04~05 | SimPy 시뮬레이터, 74개 pytest, SC2 검증 | 완료 |
| Phase 3: 검증 | 2026.05~06 | Monte Carlo, 3D 대시보드, 7개 시나리오 전량 실행 | 완료 |
| Phase 4: 문서화 | 2026.06 | 기술 보고서(DOCX), 성능 차트, README | 완료 |

---

## 팀 정보

**개발자:** 장선우
**소속:** 국립 목포대학교 드론기계공학과 (2025 입학)
**프로젝트 기간:** 2026.01.04 ~ 2026.06

### 자격증

- 초경량비행장치 지도조종자
- 초경량비행장치 조종자
- 드론축구지도자 3급
- 드론 정비 1급

### 수상 이력

| 연도 | 대회 | 결과 |
|------|------|------|
| 2022 | 제6회 공군참모총장배 드론 종합경연대회 3부리그 | **우승** |
| 2022 | 제2회 북구청장배 전국드론축구대회 3부리그 | **우승** |
| 2022 | 제1회 국토교통부장관배 드론축구 챔피언십 대학리그 | **준우승** |
| 2022 | 한국대학드론스포츠협회 드론 클래쉬 캠퍼스 리그 | **우승** |
| 2022 | 한국대학드론축구대회 | **준우승** |
| 2021 | 전주시장배 전국드론축구대회 | 장려상 |

---

## 기대 효과

| 항목 | 기존 방식 | SDACS | 개선율 |
|------|----------|-------|--------|
| 배치 시간 | 6개월 | 30분 | 99.7% 단축 |
| 관제 인력 | 24시간 5명 | 1명 | 80% 절감 |
| 탐지 지연 | 5분 | 1초 | 99.7% 단축 |
| 초기 비용 | 수억원 | 드론 10대 | 90%+ 절감 |

**시장 규모:** 글로벌 도심 드론 시장 2035년 $99B

---

## 의존성

```
simpy>=4.1    numpy>=1.24    scipy>=1.11
dash>=2.17    plotly>=5.20   joblib>=1.3
pyyaml>=6.0   matplotlib>=3.8  pytest>=7.4
```

Python 3.10+

---

## 참고 문헌

1. Reynolds, C. W. (1987). *Flocks, Herds, and Schools.* SIGGRAPH, 21(4), 25–34.
2. Khatib, O. (1986). *Real-Time Obstacle Avoidance.* IJRR, 5(1), 90–98.
3. Sharon, G. et al. (2015). *Conflict-Based Search.* Artificial Intelligence, 219, 40–66.
4. NASA UTM Project. (2023). *UAS Traffic Management Documentation.*
5. 국토교통부. (2023). *드론 교통관리체계(K-UTM) 구축 및 운영 계획.*
6. 장선우. (2026). *군집드론 공역통제 자동화 시스템.* 국립 목포대학교 캡스톤 디자인.

---

## 라이선스

MIT License — 학술 및 교육 목적으로 개발되었습니다.

---

## 변경 이력 (Changelog)

| 날짜/시간 (KST) | 커밋 | 작업 내용 | 수정 파일 |
| --- | --- | --- | --- |
| 2026-03-26 08:19 | `b1a8b2f` | fix: ROGUE advisory guard, clearance NFZ validation, dead import removal | simulation/simulator.py, src/airspace_control/controller/airspace_controller.py |

---

<div align="center">

**Made with heart by 장선우 · 국립 목포대학교 드론기계공학과**

[📖 기술 보고서](docs/report/SDACS_Technical_Report.docx) · [📊 성능 차트](docs/images/)

</div>
