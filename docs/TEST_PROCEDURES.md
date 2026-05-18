# SDACS 시험절차서 (Test Procedure Document)

> **문서 번호**: SDACS-STP-001  
> **버전**: 1.0  
> **작성일**: 2026-05-18  
> **대상**: TTA GS인증 심사, 학술 논문 투고, 제3자 재현성 검증  

---

## 1. 개요

본 문서는 군집드론 공역통제 자동화 시스템(SDACS)의 소프트웨어 기능 검증을 위한 시험절차를 정의한다. 모든 시험은 `pytest` 자동화 프레임워크를 통해 실행 가능하며, Docker 환경에서 동일하게 재현된다.

### 1.1 시험 환경

| 항목 | 사양 |
|------|------|
| 운영체제 | Ubuntu 22.04 (Docker), Windows 11 (개발) |
| Python | 3.11.x |
| 주요 프레임워크 | SimPy 4.x, NumPy 1.24+, Dash 2.17+ |
| RNG 시드 | 42 (고정, 재현성 보장) |
| PYTHONHASHSEED | 0 |
| CPU 스레드 | OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 |

### 1.2 시험 실행 명령어

```bash
# 전체 자동화 시험 (권장)
pytest tests/ -v --tb=short \
  --cov=src --cov=simulation \
  --cov-report=html:reports/coverage_html \
  --junitxml=reports/test_results.xml

# 시나리오별 실행
python main.py scenario <시나리오명>

# Monte Carlo 스윕
python main.py monte-carlo --mode quick   # 80회
python main.py monte-carlo --mode full    # 38,400회
```

### 1.3 합격 기준 요약

| 지표 | 기준값 |
|------|--------|
| 충돌 해결률(CRR) | ≥ 95% |
| 경로효율(PE) | ≤ 1.15 |
| Near-miss 비율 | < 0.5 / 1,000 flight-sec |
| 어드바이저리 지연 | < 1 s |
| NFZ 침범 | 0건 |
| 전체 테스트 통과 | 3,461+ |
| 코드 커버리지 | ≥ 75% (핵심 모듈 ≥ 86%) |

---

## 2. 단위 시험 (Unit Tests)

### TP-U01: APF 반발력 계산
- **대상 모듈**: `simulation/apf_engine/apf.py`
- **매핑 요구사항**: REQ-006, REQ-009
- **사전 조건**: `pytest` 설치, 프로젝트 루트에서 실행
- **실행 절차**:
  ```bash
  pytest tests/test_apf.py -v
  ```
- **기대 결과**:
  - `test_two_drones_repulsion`: 근접 드론 간 반발력 방향이 서로 멀어지는 방향
  - `test_obstacle_repulsion`: 장애물 근처 드론에 장애물에서 멀어지는 힘 발생
  - `test_windy_increases_repulsion`: 풍속 15 m/s 시 반발력 크기가 풍속 0보다 큼
- **판정 기준**: 모든 테스트 PASS

### TP-U02: 비행 단계 상태 머신
- **대상 모듈**: `visualization/_embedded_sim.py`
- **매핑 요구사항**: REQ-010, REQ-011, REQ-012, REQ-013
- **실행 절차**:
  ```bash
  pytest tests/test_core_functions.py -v -k "TestSimulator3dUpdate"
  ```
- **기대 결과**:

  | 테스트 | 검증 내용 | 기대값 |
  |--------|-----------|--------|
  | test_takeoff_reaches_cruise | TAKEOFF → ENROUTE 전환 | position[2] == CRUISE_ALT(60m) |
  | test_landing_touches_ground | LANDING → GROUNDED 전환 | position[2] == 0.0 |
  | test_battery_critical_forces_landing | 배터리 4% → LANDING | flight_phase == LANDING |
  | test_holding_to_rtl | HOLDING 5s → RTL | flight_phase == RTL |
  | test_failed_descends | FAILED → 하강 | position[2] 감소 |

- **판정 기준**: 8개 테스트 모두 PASS

### TP-U03: 동력 소모 모델
- **대상 모듈**: `simulation/drone_agent.py`
- **매핑 요구사항**: REQ-005
- **실행 절차**:
  ```bash
  pytest tests/test_core_functions.py -v -k "TestEstimatePowerW"
  ```
- **기대 결과**:
  - 속도 증가 → 전력 증가
  - 역풍 → 실효 속도 증가 → 전력 증가
  - 전력값은 항상 0 이상
- **판정 기준**: 9개 테스트 모두 PASS

### TP-U04: CBS 경로 최적화
- **대상 모듈**: CBS(Conflict-Based Search) 모듈
- **매핑 요구사항**: REQ-016
- **실행 절차**:
  ```bash
  pytest tests/test_cbs.py -v
  ```
- **기대 결과**: 격자 좌표 계산, 해시 가능성, 격자 해상도 범위 검증
- **판정 기준**: 모든 테스트 PASS

### TP-U05: 어드바이저리 생성
- **대상 모듈**: Resolution Advisory 모듈
- **매핑 요구사항**: REQ-003, REQ-008, REQ-012, REQ-018
- **실행 절차**:
  ```bash
  pytest tests/test_resolution_advisory.py -v
  ```
- **기대 결과**:

  | 테스트 | 검증 내용 |
  |--------|-----------|
  | test_urgent_cpa_triggers_evade_apf | CPA < 10s → EVADE_APF |
  | test_lost_link_sequence_three_phases | 통신두절 3단계 시퀀스 |
  | test_head_on_triggers_turn_right | 정면충돌 → 우측 회피 (ICAO) |

- **판정 기준**: 모든 테스트 PASS

### TP-U06: 안전 수정 회귀 방지
- **대상**: 충돌 필터, RTL APF, ROGUE 어드바이저리, 바람 제외, 상태 전이
- **매핑 요구사항**: REQ-002, REQ-006, REQ-012, REQ-018
- **실행 절차**:
  ```bash
  pytest tests/test_safety_fixes.py -v
  ```
- **판정 기준**: 모든 테스트 PASS (약 55개)

---

## 3. 통합 시험 (Integration Tests)

### TP-I01: 관제 컨트롤러 통합
- **대상 모듈**: `src/airspace_control/controller/`
- **매핑 요구사항**: REQ-002, REQ-003, REQ-015, REQ-017
- **실행 절차**:
  ```bash
  pytest tests/test_airspace_controller.py -v
  ```
- **기대 결과**:
  - 텔레메트리 수신 → 드론 위치 등록
  - 분리간격 50m 이하 → 충돌 탐지
  - 강풍 15 m/s → 분리간격 150m 상한 적용
  - 만료 어드바이저리 자동 제거
- **판정 기준**: 모든 테스트 PASS

### TP-I02: 메트릭 파이프라인
- **대상 모듈**: `src/analytics/`
- **매핑 요구사항**: REQ-007, REQ-014, REQ-022
- **실행 절차**:
  ```bash
  pytest tests/test_metrics.py tests/test_core_analytics.py -v
  ```
- **기대 결과**:
  - 충돌 해결률 공식 검증: `1 - collisions/(conflicts + collisions)`
  - 경로효율 계산 정확성
  - SLA 위반 탐지
- **판정 기준**: 모든 테스트 PASS

### TP-I03: 엔진 통합
- **대상**: SimPy 시뮬레이터 + APF + 관제
- **매핑 요구사항**: REQ-001, REQ-006, REQ-014
- **실행 절차**:
  ```bash
  pytest tests/test_engine_integration.py -v
  ```
- **판정 기준**: 모든 테스트 PASS

---

## 4. 시나리오 시험 (Scenario Tests)

### TP-S01: 정상 고밀도 교통 (s01_normal_high_density)

- **매핑 요구사항**: REQ-001, REQ-002, REQ-007, REQ-014
- **사전 조건**: 드론 100대, 시뮬레이션 10분
- **실행 절차**:
  ```bash
  python main.py scenario high_density
  # 또는
  pytest tests/test_simulator_scenarios.py -v -k "TestBaseScenario"
  ```
- **설정값**:

  | 파라미터 | 값 |
  |---------|-----|
  | drone_count | 100 |
  | simulation_duration | 10분 |
  | arrival_rate | 20대/분 |
  | area | 100 km² |
  | profile_mix | DELIVERY 60%, SURVEILLANCE 30%, EMERGENCY 10% |

- **기대 결과**:

  | 지표 | 허용 기준 |
  |------|-----------|
  | collision_count | 0 |
  | conflict_resolution_rate | ≥ 0.995 |
  | route_efficiency | ≤ 1.15 |

- **판정 기준**: 3개 KPI 모두 충족

---

### TP-S02: 비상 드론 장애 (s02_emergency_drone_failure)

- **매핑 요구사항**: REQ-005, REQ-013, REQ-022
- **사전 조건**: 드론 80대, 장애 주입 3~7분
- **실행 절차**:
  ```bash
  python main.py scenario emergency_failure
  # 또는
  pytest tests/test_simulator_scenarios.py -v -k "TestFailureScenario"
  ```
- **설정값**:

  | 파라미터 | 값 |
  |---------|-----|
  | drone_count | 80 |
  | simulation_duration | 10분 |
  | failure_rate | 5% |
  | failure_types | MOTOR 30%, BATTERY 40%, GPS 20%, COMMS 10% |

- **기대 결과**:

  | 지표 | 허용 기준 |
  |------|-----------|
  | collision_count | 0 |
  | emergency_response_p50 | ≤ 2.0 s |
  | emergency_response_p99 | ≤ 10.0 s |
  | clearance_time | ≤ 60 s |

- **판정 기준**: 모든 KPI 충족

---

### TP-S03: 대규모 동시 이착륙 (s03_mass_takeoff_landing)

- **매핑 요구사항**: REQ-001, REQ-010, REQ-011
- **사전 조건**: 드론 100대, 패드 각 5개
- **실행 절차**:
  ```bash
  python main.py scenario mass_takeoff
  ```
- **설정값**:

  | 파라미터 | 값 |
  |---------|-----|
  | drone_count | 100 |
  | simultaneous_takeoffs | 100 |
  | simultaneous_landings | 100 (t=300s) |
  | simulation_duration | 600 s |

- **기대 결과**: 동시 이착륙 시 충돌 0건, 모든 드론 안전 착륙
- **판정 기준**: collision_count == 0

---

### TP-S04: 경로 충돌 해소 (s04_route_conflict_resolution)

- **매핑 요구사항**: REQ-006, REQ-008, REQ-014, REQ-016
- **사전 조건**: 4가지 충돌 기하 100회씩 = 400회 충돌 상황
- **실행 절차**:
  ```bash
  python main.py scenario route_conflict
  ```
- **설정값**:

  | 충돌 유형 | 횟수 |
  |-----------|------|
  | 정면 충돌 (head_on) | 100 |
  | 90도 교차 (crossing_90deg) | 100 |
  | 추월 (overtake) | 100 |
  | 다중 수렴 (converging_multi) | 100 |

- **기대 결과**: 400회 중 충돌 해결률 ≥ 99.5%
- **판정 기준**: conflict_resolution_rate ≥ 0.995

---

### TP-S05: 통신 두절 (s05_comms_loss)

- **매핑 요구사항**: REQ-012, REQ-024
- **사전 조건**: 드론 50대, 통신 두절 30~300초 사이 랜덤 발생
- **실행 절차**:
  ```bash
  python main.py scenario comms_loss
  # 또는
  pytest tests/test_simulator_scenarios.py -v -k "TestCommsLossScenario"
  ```
- **설정값**:

  | 파라미터 | 값 |
  |---------|-----|
  | drone_count | 50 |
  | affected_drones | 1~10대 |
  | duration | 30~180 s |
  | phase1_loiter | 30 s |
  | phase2_rtl_altitude | 80 m |

- **기대 결과**:
  - Lost-link 드론이 HOLDING → RTL → LANDING 3단계 자동 수행
  - 귀환 중 다른 드론과 충돌 없음
- **판정 기준**: collision_count == 0, 모든 affected 드론 안전 착륙

---

### TP-S06: 기상 교란 (s06_weather_disturbance)

- **매핑 요구사항**: REQ-009, REQ-023
- **사전 조건**: 드론 100대, 3가지 풍속 모델
- **실행 절차**:
  ```bash
  python main.py scenario weather_disturbance
  # 또는
  pytest tests/test_simulator_scenarios.py -v -k "TestWeatherScenario"
  ```
- **설정값**:

  | 풍속 모델 | 속도 |
  |-----------|------|
  | 정상풍 (constant) | 5 m/s, 서풍 |
  | 돌풍 (variable) | 평균 10 m/s, 순간 최대 15 m/s |
  | 고도 전단 (shear) | 저고도 5 m/s, 고고도 20 m/s |

- **기대 결과**:
  - 돌풍 15 m/s 시 APF_PARAMS_WINDY 자동 전환
  - 전 시나리오 충돌 0건
- **판정 기준**: collision_count == 0

---

### TP-S07: 적대적 드론 침입 (s07_adversarial_intrusion)

- **매핑 요구사항**: REQ-018, REQ-025
- **사전 조건**: 드론 50대 + 침입자 3대 (5분 후 등장)
- **실행 절차**:
  ```bash
  python main.py scenario adversarial_intrusion
  # 또는
  pytest tests/test_simulator_scenarios.py -v -k "TestIntrusionScenario"
  ```
- **설정값**:

  | 파라미터 | 값 |
  |---------|-----|
  | intrusion_count | 3 |
  | start_time | 5분 |
  | behavior_mix | RANDOM_WALK 40%, BEELINE 40%, LOITER 20% |

- **기대 결과**:

  | 지표 | 허용 기준 |
  |------|-----------|
  | detection_rate | ≥ 95% |
  | detection_latency_p90 | ≤ 5.0 s |
  | false_positive_rate | ≤ 0.1% |

- **판정 기준**: 3개 KPI 모두 충족

---

### TP-S08: 다중 도시 동시 운영 (s08_multi_city_operation)

- **매핑 요구사항**: REQ-001, REQ-019
- **사전 조건**: 서울(100대) + 부산(80대) + 대구(60대) = 240대 동시 운영
- **실행 절차**:
  ```bash
  python main.py scenario multi_city
  ```
- **기대 결과**: 3개 독립 공역에서 각각 충돌 0건
- **판정 기준**: 총 collision_count == 0

---

### TP-S09: 자율 군집 비행 (s09_swarm_autonomous_no_preplan)

- **매핑 요구사항**: REQ-006, REQ-007, REQ-020
- **사전 조건**: 드론 20대, 사전 경로 없음, 다이아몬드 포메이션
- **실행 절차**:
  ```bash
  python main.py scenario swarm_autonomous_no_preplan
  ```
- **설정값**:

  | 파라미터 | 값 |
  |---------|-----|
  | drone_count | 20 |
  | formation | DIAMOND (leader 4, followers 4 each) |
  | spacing | 80 m |
  | break_threshold | 위협 50m |

- **기대 결과**:

  | 지표 | 허용 기준 |
  |------|-----------|
  | collision_count | 0 |
  | conflict_resolution_rate | ≥ 0.98 |
  | route_efficiency | ≤ 1.20 |
  | formation_breaks | ≤ 8건 |

- **판정 기준**: 4개 KPI 모두 충족

---

## 5. E2E 시험 (End-to-End Tests)

### TP-E01: 전체 시뮬레이션 파이프라인

- **매핑 요구사항**: REQ-001, REQ-014, REQ-019
- **실행 절차**:
  ```bash
  pytest tests/test_e2e_quick.py -v
  ```
- **기대 결과**:
  - 시뮬레이터 초기화 → 실행 → 결과 수집 전 과정 정상
  - 동일 시드 두 번 실행 → 동일 결과 (결정론적)
  - 모든 메트릭 JSON 직렬화 가능
- **판정 기준**: 11개 E2E 테스트 모두 PASS

### TP-E02: Monte Carlo 소규모 스윕

- **매핑 요구사항**: REQ-019, REQ-020
- **실행 절차**:
  ```bash
  python main.py monte-carlo --mode quick
  ```
- **기대 결과**:
  - 80회 스윕 정상 완료
  - 결과 CSV/JSON 생성
  - CRR ≥ 95%, PE ≤ 1.15 (평균)
- **판정 기준**: 스윕 완료, 집계 메트릭 기준값 충족

### TP-E03: 재현성 검증

- **매핑 요구사항**: REQ-019
- **실행 절차**:
  ```bash
  pytest tests/test_verify_canonical_hashes.py -v
  python main.py simulate --duration 30 --seed 42
  # 두 번 실행 후 결과 비교
  ```
- **기대 결과**: SHA-256 해시가 두 실행에서 동일
- **판정 기준**: 해시 일치

---

## 6. 성능 시험 (Performance Tests)

### TP-P01: 틱 처리 성능

- **매핑 요구사항**: REQ-021
- **목표**: 드론 30대 기준 틱 처리 ≤ 100 ms
- **실행 절차**:
  ```bash
  pytest tests/test_e2e_quick.py -v -k "test_response_time_analysis"
  pytest tests/test_e2e_quick.py -v -k "test_various_drone_counts"
  ```
- **판정 기준**: 평균 tick_time_ms < 100 ms

### TP-P02: 처리량 (Throughput)

- **매핑 요구사항**: REQ-007, REQ-021
- **목표**: 시뮬레이션 실시간 배율 ≥ 1.0x
- **실행 절차**:
  ```bash
  pytest tests/test_e2e_quick.py -v -k "test_throughput_calculation"
  ```
- **판정 기준**: 시뮬레이션 시간 / 실제 실행 시간 ≥ 1.0

---

## 7. Monte Carlo 전체 스윕

### TP-MC01: 전체 38,400회 스윕

- **매핑 요구사항**: REQ-020
- **주의**: 16코어 기준 약 25분 소요
- **실행 절차**:
  ```bash
  PYTHONHASHSEED=0 OMP_NUM_THREADS=1 \
  python main.py monte-carlo --mode full
  ```
- **기대 결과**:
  - 38,400회 중 CRR ≥ 95% 비율 ≥ 99%
  - 결과 `results/summary.parquet` 생성
  - per-run JSON 420개 생성
- **판정 기준**: 집계 통계가 논문 Table 3 기준값과 ±2σ 이내

---

## 8. 시험 결과 요약 양식

각 시험 완료 후 아래 양식에 결과를 기록한다.

| 시험 ID | 시험명 | 실행일시 | 환경 | 결과 | 비고 |
|---------|--------|---------|------|------|------|
| TP-U01 | APF 반발력 계산 | | | ☐ PASS ☐ FAIL | |
| TP-U02 | 비행 단계 상태 머신 | | | ☐ PASS ☐ FAIL | |
| TP-U03 | 동력 소모 모델 | | | ☐ PASS ☐ FAIL | |
| TP-U04 | CBS 경로 최적화 | | | ☐ PASS ☐ FAIL | |
| TP-U05 | 어드바이저리 생성 | | | ☐ PASS ☐ FAIL | |
| TP-U06 | 안전 수정 회귀 방지 | | | ☐ PASS ☐ FAIL | |
| TP-I01 | 관제 컨트롤러 통합 | | | ☐ PASS ☐ FAIL | |
| TP-I02 | 메트릭 파이프라인 | | | ☐ PASS ☐ FAIL | |
| TP-I03 | 엔진 통합 | | | ☐ PASS ☐ FAIL | |
| TP-S01 | 정상 고밀도 교통 | | | ☐ PASS ☐ FAIL | |
| TP-S02 | 비상 드론 장애 | | | ☐ PASS ☐ FAIL | |
| TP-S03 | 대규모 동시 이착륙 | | | ☐ PASS ☐ FAIL | |
| TP-S04 | 경로 충돌 해소 | | | ☐ PASS ☐ FAIL | |
| TP-S05 | 통신 두절 | | | ☐ PASS ☐ FAIL | |
| TP-S06 | 기상 교란 | | | ☐ PASS ☐ FAIL | |
| TP-S07 | 적대적 드론 침입 | | | ☐ PASS ☐ FAIL | |
| TP-S08 | 다중 도시 동시 운영 | | | ☐ PASS ☐ FAIL | |
| TP-S09 | 자율 군집 비행 | | | ☐ PASS ☐ FAIL | |
| TP-E01 | 전체 시뮬레이션 파이프라인 | | | ☐ PASS ☐ FAIL | |
| TP-E02 | Monte Carlo 소규모 스윕 | | | ☐ PASS ☐ FAIL | |
| TP-E03 | 재현성 검증 | | | ☐ PASS ☐ FAIL | |
| TP-P01 | 틱 처리 성능 | | | ☐ PASS ☐ FAIL | |
| TP-P02 | 처리량 | | | ☐ PASS ☐ FAIL | |
| TP-MC01 | 전체 Monte Carlo | | | ☐ PASS ☐ FAIL | |

---

## 9. 관련 문서

| 문서 | 위치 |
|------|------|
| RTM (요구사항-테스트 추적 매트릭스) | `reports/rtm.md` |
| 커버리지 리포트 | `reports/coverage_html/index.html` |
| JUnit 시험 결과 | `reports/test_results.xml` |
| 환경 스냅샷 | `reports/environment_snapshot.txt` |
| 재현성 가이드 | `docs/REPRODUCIBILITY.md` |
| Monte Carlo 설정 | `config/monte_carlo.yaml` |
| 시나리오 파라미터 | `config/scenario_params/*.yaml` |
