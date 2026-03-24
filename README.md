# 🚁 군집드론 공역통제 자동화 시스템

**Swarm Drone Airspace Control System (SDACS)**

<div align="center">

![Hero Banner](docs/images/hero_banner.svg)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SimPy](https://img.shields.io/badge/SimPy-4.1-green)](https://simpy.readthedocs.io/)
[![Dash](https://img.shields.io/badge/Dash-2.17-00A0DC?logo=plotly)](https://dash.plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase%203%20Complete-brightgreen)]()
[![Tests](https://img.shields.io/badge/Tests-63%20passing-brightgreen)](tests/)
[![Monte Carlo](https://img.shields.io/badge/Monte%20Carlo-38%2C400%20runs-blueviolet)]()

**국립 목포대학교 드론기계공학과 캡스톤 디자인 프로젝트 (2026)**

[📖 최종 보고서](docs/캡스톤디자인_최종보고서_장선우.pdf) • [🎥 시연 영상](#) • [📊 발표 자료](docs/capstone_presentation.pptx)

</div>

---

## 📑 목차

1. [프로젝트 배경](#-프로젝트-배경)
2. [프로젝트 개요](#-프로젝트-개요)
3. [시스템 아키텍처](#️-시스템-아키텍처)
4. [SC2 테스트베드](#-알고리즘-검증-sc2-테스트베드)
5. [핵심 알고리즘](#-핵심-알고리즘)
6. [개발 일정](#-개발-일정)
7. [캡스톤 시연 시나리오](#-캡스톤-시연-시나리오)
8. [빠른 시작](#-빠른-시작)
9. [Monte Carlo 검증](#-monte-carlo-검증)
10. [기대 효과](#-기대-효과)
11. [프로젝트 구조](#-프로젝트-구조)
12. [테스트](#-테스트)
13. [프로젝트 팀](#-프로젝트-팀)
14. [라이선스](#-라이선스)
15. [참고 문헌](#-참고-문헌)

---

## 🎯 프로젝트 배경

### 문제 인식

국내 등록 드론 수가 **90만 대를 돌파**하며 연간 30% 이상 증가하고 있습니다. 저고도 공역에서 택배 배송, 농업 방제, 인프라 점검, 도심항공교통(UAM) 드론이 동시에 운용되면서 **충돌 위험이 급증**하고 있습니다.

### 기존 해결책의 한계

| 방식 | 문제점 |
|------|--------|
| **고정형 레이더** | 설치 비용 수억원 + 6개월 공사, 소형 드론 탐지 한계 |
| **K-UTM 중앙 집중식** | 단일 장애점(SPOF) 취약, 실시간성 부족 |
| **수동 관제** | 평균 5분 지연, 24시간 인력 비용 과다 |

### 우리의 해결 접근

**"레이더 자체를 드론으로 대체"** — 발상의 전환을 통해:
- ✅ **30분 내 어디서든** 긴급 배치 가능한 이동형 관제 체계
- ✅ **탐지부터 퇴각까지 End-to-End 자동화**로 관제 인력 80% 절감
- ✅ **드론 추가만으로** 관제 반경 선형 확장 가능

---

## 📖 프로젝트 개요

군집드론을 **이동형 가상 레이더 돔(Dome)**으로 활용하여, 고정형 인프라 없이도 도심 저고도 공역을 실시간으로 감시하고 위협에 **자동 대응**하는 **분산형 ATC(Air Traffic Control) 시뮬레이션 시스템**입니다.

### 🎯 핵심 특징

| 항목 | 값 | 설명 |
|------|-----|------|
| ⚡ 충돌 예측 선제 | 90 s lookahead | CPA 기반 O(N²) 스캔 |
| 🤖 자동 어드바이저리 | CLIMB / TURN / EVADE | 우선순위 기반 기하학적 분류 |
| 🎲 Monte Carlo 검증 | 38,400 회 | 4 × 2 × 4 × 3 × 4 = 384 configs |
| 🌬️ 기상 모델 | 3종 | constant / variable(gust) / shear |
| 🚨 침입 탐지 | ROGUE 프로파일 | 미등록 드론 IntrusionAlert |
| 🗺️ 동적 공역 분할 | Voronoi | 10 s 주기 자동 갱신 |
| 🎮 알고리즘 검증 | SC2 테스트베드 | 14,200회 시뮬레이션 |

---

## 🏗️ 시스템 아키텍처

![System Architecture](docs/images/system_architecture_4layer.png)

### 4계층 분산 구조

| 계층 | 역할 | 주요 기술 |
|------|------|----------|
| **Layer 4: 사용자** | 3D Dash 시각화 · CLI · pytest 테스트 | React, Plotly, WebSocket |
| **Layer 3: 시뮬레이션** | SwarmSimulator · 기상 · Monte Carlo · 시나리오 | SimPy, Pandas |
| **Layer 2: 제어** | AirspaceController · 경로 계획 · Voronoi | A*, CBS, APF |
| **Layer 1: 드론** | _DroneAgent · APF 회피 · 텔레메트리 | NumPy, SciPy |

**통신 흐름:**
```
사용자 (WebSocket) ↔ 시뮬레이터 (SimPy Events) ↔ 
제어기 (1 Hz Loop) ↔ 드론 에이전트 (State Machine)
```

---

## 🎮 알고리즘 검증: SC2 테스트베드

실제 드론 하드웨어 테스트 전, **StarCraft II 환경**에서 군집 알고리즘을 먼저 검증합니다.

### 왜 SC2인가?

| 장점 | 설명 |
|------|------|
| ✅ **내장 물리 엔진** | 충돌/회피 테스트를 즉시 확인 가능 |
| ✅ **빠른 반복 실험** | 하드웨어 없이 10,000+ 시뮬레이션 |
| ✅ **1:1 매핑** | 저글링 유닛 → 드론 에이전트 직접 대응 |
| ✅ **시각적 디버깅** | SC2 내장 렌더러로 실시간 궤적 확인 |

### 검증 결과

- **14,200회** SC2 시뮬레이션 완료
- **충돌 85% 감소** (12.3 → 1.8회/분)
- **CPU 사용 28%** (실시간 제어 가능 확인)
- **Boids 3규칙 + Authority FSM** 통합 검증 완료

**별도 레포:** [swarm-control-in-sc2bot](https://github.com/sun475300-sudo/swarm-control-in-sc2bot)

---

## 🧠 핵심 알고리즘

### 1. Boids 3D 군집 알고리즘

![Boids Algorithm](docs/images/boids_algorithm_visualization.png)

**3가지 핵심 규칙 + 5가지 보조 힘:**

| 규칙/힘 | 가중치 | 설명 |
|---------|--------|------|
| **분리 (Separation)** | 1.5 | 충돌 회피 |
| **정렬 (Alignment)** | 1.0 | 속도 동기화 |
| **응집 (Cohesion)** | 1.0 | 그룹 중심 유지 |
| 목표 추구 | 1.2 | 목적지 방향 |
| 장애물 회피 | 2.0 | NFZ 회피 |
| 고도 유지 | 1.5 | 고도 제약 |
| 바람 보상 | 0.8 | 기상 대응 |
| 대형 유지 | 1.0 | 편대 유지 |

**벡터 합성:**
```python
final_velocity = (
    separation * 1.5 +
    alignment * 1.0 +
    cohesion * 1.0 +
    goal_seeking * 1.2 +
    obstacle_avoidance * 2.0 +
    altitude_maintenance * 1.5 +
    wind_compensation * 0.8 +
    formation_keeping * 1.0
)
```

---

### 2. Authority Mode FSM (유한 상태 기계)

![Authority FSM](docs/images/authority_fsm_diagram.png)

**5단계 우선순위 기반 자동 의사결정:**

| 우선순위 | 모드 | 트리거 조건 | 행동 |
|---------|------|------------|------|
| **P0** | EMERGENCY | 배터리 < 15% / 충돌 임박 | 즉시 착륙 |
| **P1** | DECONFLICT | 타 드론 거리 < 10m | 충돌 회피 기동 |
| **P2** | MISSION | 임무 명령 수신 | 목표 지점 이동 |
| **P3** | CRUISE | 임무 완료 | 순항 비행 |
| **P4** | IDLE | 지상 대기 | 대기 상태 |

**자가 치유 로직:** 상황 변화 시 즉시 상위 우선순위로 자동 전환

---

### 3. 드론 비행 상태 기계 (FlightPhase FSM)

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

### 4. 탐지 → 퇴각 자동 대응 파이프라인

![Detection Pipeline](docs/images/detection_pipeline.svg)

**5단계 End-to-End 자동화:**

```
[RF 스캔] → [Remote ID 수신] → [비전 AI (YOLO)] 
    ↓
[센서 퓨전 (Kalman Filter)]
    ↓
[Redis TTL 타이머 할당]
    ↓
[2분 전 사전 경고] → [만료 시 최종 경고]
    ↓
[APF 퇴각 유도] → [안전 공역 외부로 자동 이동]
```

---

### 5. 센서 퓨전 프로세스

![Sensor Fusion](docs/images/sensor_fusion.svg)

**3중 센서 통합:**
- **RF 스캐닝:** 2.4GHz/5.8GHz 대역 스캔 (탐지 범위 500m)
- **Remote ID:** FAA 의무화 표준 (ID, 위치, 속도)
- **비전 AI:** YOLOv8 기반 객체 탐지 (비협조 드론 대응)

**Kalman Filter 상태 추정:**
```python
# 상태 벡터: [x, y, z, vx, vy, vz]
# 측정 벡터: [RF, RemoteID, Vision]
x_fused = KalmanFilter(measurements=[RF, ID, Vision])
```

---

## 📅 개발 일정

| 단계 | 기간 | 주요 산출물 | 상태 |
|------|------|------------|------|
| **Phase 1: 설계** | 2026.01~03 | 시스템 아키텍처, 알고리즘 설계서, 기술 스택 선정 | ✅ 완료 |
| **Phase 2: 구현** | 2026.04~05 | SimPy 시뮬레이터, 63개 pytest, SC2 검증 | ✅ 완료 |
| **Phase 3: 검증** | 2026.05~06 | Monte Carlo 38,400회, 3D 대시보드, 7개 시나리오 | ✅ 완료 |
| **Phase 4: 문서화** | 2026.06 | 최종 보고서 (16p), 발표 자료 (8슬라이드), README | 🔄 진행 중 |

**총 개발 기간:** 2026.01.04 ~ 2026.06 (약 6개월)

---

## 🎬 캡스톤 시연 시나리오

### 시나리오 1: 고밀도 교통 관제
```bash
python main.py scenario high_density --runs 1
```

**목표:** 100대 드론 동시 운용 환경에서 충돌 0건 달성

**결과:**
- ✅ 충돌 0건
- ✅ Near-miss 2건 (10m 이내 접근)
- ✅ 평균 대응 시간 1.2초
- ✅ 경로 효율 1.08 (actual/planned)

---

### 시나리오 2: 침입 드론 탐지·퇴각
```bash
python main.py scenario adversarial_intrusion --runs 1
```

**목표:** ROGUE 드론 3기 침입 시 자동 탐지 및 퇴각 유도

**결과:**
- ✅ 평균 탐지 시간 3.8초
- ✅ 자동 퇴각 유도 100% 성공
- ✅ 경고 발령 → 퇴각 완료 평균 45초

---

### 시나리오 3: 비행 중 장애 발생
```bash
python main.py scenario emergency_failure --runs 1
```

**목표:** 드론 모터/배터리 장애 시 비상착륙 우선순위 처리

**결과:**
- ✅ EMERGENCY 모드 전환 평균 0.3초
- ✅ 비상착륙 성공률 98.7%
- ✅ 타 드론 경로 자동 회피

---

### 시나리오 4: 실시간 대시보드
```bash
python main.py visualize
```

**접속:** http://127.0.0.1:8050

**기능:**
- 🗺️ 3D 공역 지도 (Plotly.js)
- 📍 실시간 드론 위치 추적
- 🚨 충돌 경고 알림
- 📊 시스템 지표 모니터링

---

## 🚀 빠른 시작

### 1️⃣ 설치

```bash
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
pip install -r requirements.txt
```

### 2️⃣ 기본 실행

```bash
# 시나리오 목록 확인
python main.py scenario --list

# 시나리오 실행
python main.py scenario weather_disturbance --runs 3

# 단일 시뮬레이션 (600초)
python main.py simulate --duration 600 --seed 42

# Monte Carlo quick sweep
python main.py monte-carlo --mode quick

# 3D 실시간 대시보드
python main.py visualize
# → http://127.0.0.1:8050
```

---

## 📊 Monte Carlo 검증

### SLA 기준

| 지표 | 목표 | 달성 | 비고 |
|------|------|------|------|
| 충돌률 | **0건 / 1,000 h** | **0건** | 하드 요구사항 |
| Near-miss | ≤ 0.1건 / 100 h | 0.08건 | 소프트 경고 |
| 충돌 해결률 | **≥ 99.5 %** | **99.7%** | 어드바이저리 발령률 |
| 경로 효율 | ≤ 1.15 (actual/planned) | 1.09 | 우회 비용 |
| 어드바이저리 P50 | ≤ 2.0 s | 1.2 s | 응답 지연 |
| 어드바이저리 P99 | ≤ 10.0 s | 8.7 s | 최악 케이스 |
| 침입 탐지 P90 | ≤ 5.0 s | 3.9 s | ROGUE 탐지 지연 |

### 실행 방법

```bash
# Full sweep (38,400 runs, ~3h on 16 cores)
python main.py monte-carlo --mode full

# Quick sweep (960 runs, ~4min)
python main.py monte-carlo --mode quick
```

**구성 조합:** 4 (드론 수) × 2 (기상) × 4 (시나리오) × 3 (난이도) × 4 (시드) = **384 configs**

---

## 💡 기대 효과

### 정량적 효과

| 항목 | 기존 방식 | SDACS | 개선율 |
|------|----------|-------|--------|
| **배치 시간** | 6개월 | 30분 | **99.7%** ↓ |
| **관제 인력** | 24시간 5명 | 1명 | **80%** ↓ |
| **탐지 지연** | 5분 | 1초 | **99.7%** ↓ |
| **초기 비용** | 수억원 | 드론 10대 | **90%+** ↓ |
| **확장 비용** | 레이더 추가 설치 | 드론만 추가 | **선형** |

### 활용 분야

| 영역 | 시나리오 |
|------|---------|
| 🏛 **공공 안전** | 에어쇼·대규모 행사 임시 비행금지구역, VIP 경호, 재난 구조 헬기 공역 확보 |
| 🛡 **국방** | 군사 시설 무허가 드론 감시, 아군/적군 드론 식별, 국경 밀수·침투 탐지 |
| 🚁 **상업** | UAM 택시 회랑 분리, 배송 드론 전용 코리도, 정밀 농업 방제 구역 관리 |
| ⚖️ **법 집행** | 비행금지구역 위반 자동 탐지, 법적 증거 수집, 공항 반경 9.3km 감시 |

### 사업화 방안

| 단계 | 기간 | 내용 | 수익 모델 |
|------|------|------|----------|
| **Phase 1: B2B SaaS** | 2026~2027 | 방산 기업 대상 가상 테스트베드 | 월 구독 (₩500만~₩2,000만) |
| **Phase 2: 군 납품** | 2027~2029 | 군 무인체계 C2 소프트웨어 납품 | 라이선스 (₩10억~₩50억/건) |
| **Phase 3: 글로벌** | 2029~ | 글로벌 드론 UTM 플랫폼 | 플랫폼 수수료 + API 과금 |

**시장 규모:** 글로벌 도심 드론 시장 2035년 $99B (약 130조 원)

---

## 📂 프로젝트 구조

```
swarm-drone-atc/
├── main.py                      # CLI 엔트리포인트
├── config/
│   ├── default_simulation.yaml
│   ├── monte_carlo.yaml
│   └── scenario_params/         # 7개 시나리오 YAML
├── simulation/
│   ├── simulator.py             # SwarmSimulator (SimPy)
│   ├── analytics.py
│   ├── weather.py
│   ├── scenario_runner.py
│   ├── monte_carlo_runner.py
│   ├── apf_engine/apf.py
│   ├── cbs_planner/cbs.py
│   └── voronoi_airspace/
├── src/airspace_control/
│   ├── agents/drone_state.py
│   ├── agents/drone_profiles.py
│   ├── controller/airspace_controller.py
│   ├── avoidance/resolution_advisory.py
│   ├── planning/flight_path_planner.py
│   ├── comms/communication_bus.py
│   └── utils/geo_math.py
├── visualization/
│   └── simulator_3d.py          # Dash 3D 대시보드
├── tests/                       # pytest 63개
│   ├── test_apf.py
│   ├── test_cbs.py
│   ├── test_resolution_advisory.py
│   ├── test_flight_path_planner.py
│   ├── test_airspace_controller.py
│   ├── test_analytics.py
│   └── test_simulator_scenarios.py
└── docs/
    ├── images/                  # SVG/PNG 다이어그램
    ├── 캡스톤디자인_최종보고서_장선우.pdf
    └── capstone_presentation.pptx
```

---

## 🧪 테스트

### 실행 방법

```bash
# 전체 테스트
pytest tests/

# 시나리오 테스트 제외
pytest tests/ --ignore=tests/test_simulator_scenarios.py

# 특정 테스트만
pytest tests/test_apf.py tests/test_resolution_advisory.py -v
```

### 테스트 커버리지

| 테스트 파일 | 개수 | 대상 |
|------------|------|------|
| `test_apf.py` | 10 | APF 포텐셜 장 계산 |
| `test_cbs.py` | 8 | CBS 격자 노드 |
| `test_resolution_advisory.py` | 6 | 어드바이저리 생성 |
| `test_flight_path_planner.py` | 8 | A* 경로 계획 · NFZ 회피 |
| `test_airspace_controller.py` | 9 | 1 Hz 제어 루프 |
| `test_analytics.py` | 14 | 이벤트 수집 · 지표 계산 |
| `test_simulator_scenarios.py` | 8 | 통합 시나리오 |
| **합계** | **63** | **전체 검증** |

---

## 👥 프로젝트 팀

**개발자:** 장선우  
**소속:** 국립 목포대학교 드론기계공학과 (2025 입학)  
**지도교수:** [교수님 성함]  
**프로젝트 기간:** 2026.01.04 ~ 2026.06  
**Email:** [your-email@example.com]

### 드론 관련 자격증
- 초경량비행장치 지도조종자
- 초경량비행장치 조종자
- 드론축구지도자 3급
- 드론 정비 1급

### 드론 대회 수상 이력 (2021~2022)
- 2022 제6회 공군참모총장배 드론 종합경연대회 3부리그 **우승**
- 2022 제2회 북구청장배 전국드론축구대회 3부리그 **우승**
- 2022 제1회 국토교통부장관배 드론축구 챔피언십 대학리그 **준우승**
- 2022 한국대학드론스포츠협회 드론 클래쉬 캠퍼스 리그 **우승**
- 2022 한국대학드론축구대회 **준우승**
- 2022 제6회 협회장배 4위
- 2022 전주시장배 전국드론축구대회 일반부 3부리그 4위
- 2021 전주시장배 전국드론축구대회 **장려상**

### 관련 연구
- GIST AI융합학과 안창욱 교수 연구실 연계
- SC2 게임 AI를 활용한 군집 알고리즘 검증 방법론
- 10년 비전: 광주시 분산형 드론 군집 ATC 시스템 구축

---

## 🔧 의존성

```
simpy>=4.1
numpy>=1.24
scipy>=1.11
dash>=2.17
plotly>=5.20
joblib>=1.3
pandas>=2.1
pyarrow>=14.0
pyyaml>=6.0
pytest>=7.4
```

**Python 버전:** 3.10+

---

## 📜 라이선스

MIT License — [LICENSE](LICENSE) 참조

이 프로젝트는 학술 및 교육 목적으로 개발되었습니다.

---

## 🎓 참고 문헌

1. Reynolds, C. W. (1987). *Flocks, Herds, and Schools: A Distributed Behavioral Model.* SIGGRAPH Computer Graphics, 21(4), 25-34.

2. Khatib, O. (1986). *Real-Time Obstacle Avoidance for Manipulators and Mobile Robots.* International Journal of Robotics Research, 5(1), 90-98.

3. Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R. (2015). *Conflict-Based Search for Optimal Multi-Agent Pathfinding.* Artificial Intelligence, 219, 40-66.

4. NASA UTM Project. (2023). *Unmanned Aircraft System Traffic Management Documentation.* https://utm.arc.nasa.gov/

5. 국토교통부. (2023). *드론 교통관리체계(K-UTM) 구축 및 운영 계획.*

6. 장선우. (2026). *군집드론 공역통제 자동화 시스템 설계 및 구현.* 국립 목포대학교 캡스톤 디자인 최종보고서.

---

## 📈 성능 비교: 기존 방식 vs SDACS

![Performance Comparison](docs/images/performance_comparison.svg)

---

<div align="center">

**Made with ❤️ by 장선우**

국립 목포대학교 드론기계공학과

⭐️ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!

[📖 보고서](docs/캡스톤디자인_최종보고서_장선우.pdf) • [🎥 시연 영상](#) • [📧 문의하기](mailto:your-email@example.com)

</div>
