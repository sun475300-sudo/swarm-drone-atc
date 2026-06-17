# 야간·비가시권(BVLOS) 특별비행승인 요건 검증 시나리오 (GENESIS Phase 310)

*Created: 2026-06-18 · SDACS Capstone Certification*
*용도: 특별비행승인 신청 시 첨부할 시뮬레이션 검증 결과 근거 문서*

> SDACS(군집드론 공역통제 자동화 시스템)가 야간 운용 및 비가시권(BVLOS) 운용 조건에서
> 안전 요건을 충족함을 검증하기 위한 시뮬레이션 시나리오 정의서입니다.

---

## 1. 규제 근거 (Regulatory Basis)

### 1.1 항공안전법 시행규칙 제310조 -- 야간비행 특별승인

| 항목 | 내용 |
|---|---|
| 조문 | 항공안전법 시행규칙 제310조 (무인비행장치 야간비행 특별승인) |
| 적용 시간 | 일몰 후 ~ 일출 전 (Civil Twilight 기준) |
| 핵심 요건 | 항공등화 장치 장착, 감시자(Visual Observer) 배치, 비상 절차 수립 |
| 승인 기관 | 지방항공청 (Seoul/Busan Regional Office of Aviation) |
| 갱신 주기 | 6개월 단위 재승인 |

### 1.2 드론활용촉진법 시행규칙 -- 비가시권 비행 승인 기준

| 항목 | 내용 |
|---|---|
| 조문 | 드론 활용의 촉진 및 기반조성에 관한 법률 시행규칙 제26조 |
| 핵심 요건 | C2(Command & Control) 링크 이중화, DAA(Detect-and-Avoid) 시스템 장착 |
| 운용 범위 | 지상 조종 범위를 초과하는 비가시권 비행 전 구간 |
| 추가 조건 | 실시간 텔레메트리 모니터링, 비상 자동복귀(RTL) 기능 확보 |
| 승인 기관 | 국토교통부 (MOLIT) 또는 위임 지방항공청 |

### 1.3 국토교통부 드론 특별비행 가이드라인 (2024개정)

| 항목 | 내용 |
|---|---|
| 문서 | 드론 특별비행승인 가이드라인 (국토교통부 고시) |
| 주요 개정 사항 | Risk Assessment 의무화 (SORA 기반), 비행 시나리오별 위험도 분류 |
| SAIL 기준 | Specific Assurance and Integrity Level I ~ VI 단계별 요건 |
| 시뮬레이션 요건 | 승인 신청 시 **시뮬레이션 기반 검증 결과** 첨부 가능 (2024개정 신설) |
| 관련 표준 | JARUS SORA 2.5, EASA Specific Category |

### 1.4 추가 참조 규정

| 규정 | 조항 | 관련 사항 |
|---|---|---|
| 항공안전법 | 제129조 (초경량비행장치 비행제한) | 야간·인구밀집·공역 제한 |
| 국토교통부 | 무인비행장치 비가시권 운용 기준 | 최대 통신 범위·비상 복귀·기상 한계 |
| ASTM | F3411 (Remote ID) | BVLOS 운용 시 Remote ID 방송 요건 |
| ASTM | F3442 (DAA Performance) | DAA 시스템 성능 기준 |
| EASA | SC-RPAS | 원격조종항공기 특별조건 |

---

## 2. 야간 운용 검증 시나리오 (Night Operation Scenarios: N-1 ~ N-10)

### 2.1 시나리오 상세

#### N-1: 항공등화 장치 요건 검증 (Lighting System Check)

- **목적**: 야간 비행 시 항공등화 시스템이 규정 광도 및 점멸 주기를 유지하며 시뮬레이션 내 가시성 모델이 정상 동작하는지 확인합니다.
- **조건**: 시정(visibility) 5 km, 풍속 5 m/s, 고도 60~120 m AGL
- **절차**:
  1. 전체 드론에 `lighting_mode: NIGHT_ANTI_COLLISION` 파라미터를 활성화합니다.
  2. 시뮬레이션 300초 동안 등화 상태 로그를 수집합니다.
  3. 등화 실패 주입 없이 기준선(baseline) 가시성 데이터를 확보합니다.
- **통과 기준**: 모든 드론의 등화 가동률 >= 99.9%, 점멸 주기 편차 < 5%

#### N-2: 감시자 통신 확인 (Visual Observer Communication)

- **목적**: 야간 비행 시 감시자(Visual Observer)와 조종자 간 통신 링크가 유지되는지 검증합니다.
- **조건**: 시정 3 km, 풍속 8 m/s, 감시자 위치 복수(3개소) 배치
- **절차**:
  1. 감시자 노드를 지상 관제소와 별도 통신 채널로 구성합니다.
  2. 10초 간격 heartbeat 교환을 시뮬레이션합니다.
  3. 통신 지연(latency) 및 패킷 손실률을 측정합니다.
- **통과 기준**: 통신 지연 P95 < 500 ms, 패킷 손실률 < 1%, 30초 이상 통신 두절 발생 시 자동 RTL 트리거

#### N-3: 등화 장애 시 비상 복귀 (Emergency Return with Lighting Failure)

- **목적**: 비행 중 항공등화 장치가 고장 난 경우 비상 복귀(RTL) 절차가 정상 수행되는지 확인합니다.
- **조건**: 시정 5 km, 풍속 5 m/s, 비행 중 50% 시점에서 등화 장애 주입
- **절차**:
  1. 정상 야간 비행 중 `lighting_failure` 이벤트를 드론 5대에 주입합니다.
  2. 장애 감지 후 RTL 절차 자동 개시를 확인합니다.
  3. 복귀 경로상 타 드론과의 분리 기준 유지를 검증합니다.
- **통과 기준**: 장애 감지에서 RTL 개시까지 < 3초, 복귀 중 충돌 0건, 분리 위반 0건

#### N-4: 야간 장애물 회피 (Obstacle Avoidance at Night)

- **목적**: 야간 시정 저하 환경에서 APF(Artificial Potential Field) 기반 장애물 회피가 정상 작동하는지 검증합니다.
- **조건**: 시정 1.5 km (안개), 풍속 10 m/s, 정적 장애물 20개 배치
- **절차**:
  1. 공역 내 무작위 정적 장애물(건물, 송전탑 등)을 배치합니다.
  2. 50대 드론이 목적지를 향해 비행하며 APF 회피를 수행합니다.
  3. 야간 전용 센서 모델(`sensor_mode: NIGHT_IR`)의 탐지 거리를 축소하여 적용합니다.
- **통과 기준**: 장애물 충돌 0건, 경로 효율(route efficiency) <= 1.25, APF 반응 시간 P99 < 200 ms

#### N-5: 야간 GPS 거부 항법 (GPS-Denied Navigation at Night)

- **목적**: GPS 신호가 차단된 야간 환경에서 관성 항법(INS) 폴백이 안전한 비행을 보장하는지 확인합니다.
- **조건**: 시정 3 km, 풍속 5 m/s, GPS 재밍 구역 반경 500 m
- **절차**:
  1. 공역 중심부에 GPS 재밍 구역을 설정합니다.
  2. 재밍 구역 진입 시 `gps_status: DENIED` 전환을 확인합니다.
  3. INS 기반 위치 추정 드리프트와 안전 절차(호버링에서 RTL로 전환)를 검증합니다.
- **통과 기준**: GPS 상실 감지 < 2초, INS 드리프트 60초 내 < 15 m, 충돌 0건

#### N-6: 야간 다수 드론 동시 이착륙 (Night Mass Takeoff/Landing)

- **목적**: 야간 환경에서 다수 드론의 동시 이착륙 시퀀스가 안전하게 수행되는지 확인합니다.
- **조건**: 시정 5 km, 풍속 3 m/s, 드론 50대 동시 이륙
- **절차**:
  1. 50대 드론을 75 m 간격으로 배치 후 동시 이륙 명령을 발행합니다.
  2. 이륙 시퀀싱(순차 이륙 간격)이 최소 분리 기준을 준수하는지 확인합니다.
  3. 착륙 단계에서도 동일 검증을 수행합니다.
- **통과 기준**: 분리 위반 0건, 이륙 완료 시간 < 180초, 착륙 완료 시간 < 240초

#### N-7: 야간 저시정 비상 회피 (Night Low-Visibility Emergency Avoidance)

- **목적**: 시정 1 km 미만의 극저시정 야간 환경에서 비상 회피 기동(emergency avoidance maneuver)이 작동하는지 확인합니다.
- **조건**: 시정 0.8 km, 풍속 12 m/s (돌풍 포함), 드론 30대
- **절차**:
  1. CPA(Closest Point of Approach) 경보 기반 비상 회피를 활성화합니다.
  2. 의도적 근접 경로(near-miss trajectory)를 2쌍에 주입합니다.
  3. 회피 기동 수행 및 분리 복원을 확인합니다.
- **통과 기준**: 근접 회피 성공률 100%, 분리 복원 시간 < 10초, 충돌 0건

#### N-8: 야간 배터리 부족 비상착륙 (Night Low-Battery Emergency Landing)

- **목적**: 야간 비행 중 배터리 잔량 부족 시 비상착륙 절차가 안전하게 수행되는지 확인합니다.
- **조건**: 시정 5 km, 풍속 5 m/s, 드론 40대 중 10% 배터리 급속 소진 주입
- **절차**:
  1. 시뮬레이션 180초 시점에서 4대 드론에 `battery_drain_rate: 3x` 주입합니다.
  2. 배터리 임계치(15%) 도달 시 비상착륙 프로토콜 개시를 확인합니다.
  3. 비상착륙 경로가 타 드론 비행 경로와 충돌하지 않음을 검증합니다.
- **통과 기준**: 비상착륙 개시 < 2초, 착륙 완료 < 60초, 충돌 0건

#### N-9: 야간 통신 두절 복구 (Night Communication Loss Recovery)

- **목적**: 야간에 C2 링크가 일시 두절된 후 복구되는 과정에서 드론이 안전 상태를 유지하는지 검증합니다.
- **조건**: 시정 3 km, 풍속 8 m/s, 통신 두절 지속 60초
- **절차**:
  1. `comms_loss` 이벤트를 드론 5대에 주입합니다 (두절 지속 60초).
  2. Lost-link 프로토콜 3단계(호버링 30초 대기 -> RTL 고도 80 m 상승 -> 복귀/착륙) 수행을 확인합니다.
  3. 통신 복구 후 정상 운용 재개를 검증합니다.
- **통과 기준**: 프로토콜 단계 전환 정확도 100%, 두절 중 충돌 0건, 복구 후 30초 내 정상 운용 재개

#### N-10: 야간 고밀도 교통 종합 시나리오 (Night High-Density Comprehensive)

- **목적**: 야간 조건에서 고밀도(100대) 교통 상황의 전체 안전 체계를 종합 검증합니다.
- **조건**: 시정 3 km, 풍속 10 m/s (돌풍 15 m/s), 드론 100대, 비행 시간 600초
- **절차**:
  1. `s01_normal_high_density` 시나리오를 야간 파라미터로 확장합니다.
  2. 5계층 안전망(APF-CBS-CPA-ATC-UTM) 전체 활성화 상태에서 시뮬레이션을 수행합니다.
  3. 충돌률, 충돌 해결률, 경로 효율, advisory 응답 시간을 수집합니다.
- **통과 기준**: 충돌 0건, 충돌 해결률 >= 99.5%, 경로 효율 <= 1.15, advisory 응답 P95 < 2초

---

### 2.2 야간 시나리오 파라미터 표 (Night Scenario Parameter Table)

| ID | 시나리오 명 | 풍속 (m/s) | 시정 (km) | 고도 (m AGL) | 드론 수 | 통과 기준 | SDACS 모듈 매핑 |
|---|---|:-:|:-:|:-:|:-:|---|---|
| N-1 | 항공등화 장치 요건 | 5 | 5.0 | 60~120 | 30 | 등화 가동률 >= 99.9% | `DroneAgent.lighting_system` |
| N-2 | 감시자 통신 확인 | 8 | 3.0 | 30~120 | 50 | P95 지연 < 500ms, 손실 < 1% | `CommQualitySimulator` |
| N-3 | 등화 장애 비상 복귀 | 5 | 5.0 | 60~120 | 30 | 감지->RTL < 3초, 충돌 0 | `DroneAgent.rtl()`, `ContingencyPlanner` |
| N-4 | 야간 장애물 회피 | 10 | 1.5 | 60~120 | 50 | 장애물 충돌 0, 효율 <= 1.25 | `SwarmSimulator.apf_avoidance()`, `APF_PARAMS_WINDY` |
| N-5 | GPS 거부 항법 | 5 | 3.0 | 60~90 | 30 | 드리프트 < 15m/60초, 충돌 0 | `DroneAgent.gps_status`, INS fallback |
| N-6 | 야간 동시 이착륙 | 3 | 5.0 | 0~120 | 50 | 분리 위반 0, 이륙 < 180초 | `AirspaceController`, `FlightPathPlanner` |
| N-7 | 저시정 비상 회피 | 12+gust | 0.8 | 60~120 | 30 | 회피 성공 100%, 충돌 0 | CPA 모듈, `AdvancedPathPlanner` |
| N-8 | 배터리 부족 비상착륙 | 5 | 5.0 | 30~120 | 40 | 착륙 개시 < 2초, 충돌 0 | `BatteryOptimizationController` |
| N-9 | 통신 두절 복구 | 8 | 3.0 | 60~120 | 50 | 프로토콜 정확 100%, 충돌 0 | `CommRelayPlanner`, Lost-link Protocol |
| N-10 | 야간 고밀도 종합 | 10+gust15 | 3.0 | 30~120 | 100 | 해결률 >= 99.5%, 충돌 0 | 5계층 전체 (APF-CBS-CPA-ATC-UTM) |

---

## 3. 비가시권(BVLOS) 운용 검증 시나리오 (BVLOS Scenarios: B-1 ~ B-10)

### 3.1 시나리오 상세

#### B-1: C2 링크 단절 절차 (C2 Link Loss Procedure)

- **목적**: BVLOS 운용 중 C2(Command & Control) 링크가 완전 단절되었을 때 Lost-link 프로토콜이 정확히 실행되는지 검증합니다.
- **조건**: 풍속 8 m/s, 시정 10 km, 통신 거리 2,000 m, 드론 30대
- **절차**:
  1. 시뮬레이션 120초 시점에서 3대 드론의 C2 링크를 완전 차단합니다.
  2. Lost-link 프로토콜 3단계를 검증합니다.
     - Phase 1: 30초 호버링 대기 (`phase1_loiter_s: 30`)
     - Phase 2: RTL 고도 80 m 상승 (`phase2_rtl_altitude_m: 80.0`)
     - Phase 3: 착륙 (`phase3_land: true`)
  3. 단절 드론의 경로가 타 드론과 분리를 유지하는지 확인합니다.
- **통과 기준**: 프로토콜 전환 정확도 100%, 복귀 중 충돌 0건, RTL 완료 < 120초

#### B-2: DAA 시스템 성능 (Detect-and-Avoid System Performance)

- **목적**: BVLOS 환경에서 DAA(Detect-and-Avoid) 시스템이 비협조 항공기(non-cooperative traffic)를 적시에 탐지 및 회피하는지 확인합니다.
- **조건**: 풍속 5 m/s, 시정 10 km, 드론 50대 + 비협조 항공기 5대
- **절차**:
  1. 비협조 항공기(ADS-B 미장착)를 무작위 경로로 공역에 투입합니다.
  2. SDACS의 DAA 모듈(CPA 기반)이 탐지, 경보, 회피 기동을 수행하는지 확인합니다.
  3. 회피 후 원래 경로로 복귀하는 시간을 측정합니다.
- **통과 기준**: 탐지율 >= 99%, 회피 성공률 100%, 경로 복귀 < 30초

#### B-3: 최대 통신 거리 시험 (Maximum Range Communication Test)

- **목적**: BVLOS 운용의 최대 통신 거리에서 C2 링크 품질이 안전 운용 기준을 충족하는지 확인합니다.
- **조건**: 풍속 5 m/s, 시정 10 km, 통신 거리 1,500~2,000 m (설정 `comm_range_m: 2000`)
- **절차**:
  1. 드론을 지상 관제소로부터 점진적으로 이격(500 m 단위)시킵니다.
  2. 각 거리에서 C2 링크 품질(RSSI, 지연, 패킷 손실)을 측정합니다.
  3. 2,000 m 경계에서 링크 열화(degradation) 시 자동 복귀 트리거를 확인합니다.
- **통과 기준**: 1,500 m까지 패킷 손실 < 0.5%, 2,000 m에서 손실 < 2%, 경계 도달 시 자동 복귀 트리거

#### B-4: 지상국 간 핸드오버 (BVLOS Handover Between Ground Stations)

- **목적**: 장거리 BVLOS 운용에서 드론이 한 지상국의 통신 범위를 벗어나 다음 지상국으로 핸드오버될 때 제어 연속성이 유지되는지 확인합니다.
- **조건**: 풍속 5 m/s, 시정 10 km, 지상국 2개소 (간격 3 km), 드론 20대
- **절차**:
  1. 지상국 A 관할에서 이륙 후 지상국 B 방향으로 비행합니다.
  2. 통신 범위 중첩 구간(overlap zone)에서 핸드오버 절차를 수행합니다.
  3. 핸드오버 중 명령 지연, 텔레메트리 손실, 제어 공백 시간을 측정합니다.
- **통과 기준**: 핸드오버 시간 < 3초, 제어 공백 0초, 핸드오버 중 분리 위반 0건

#### B-5: BVLOS 중 기상 악화 (Weather Degradation During BVLOS)

- **목적**: BVLOS 비행 중 기상 조건이 급격히 악화될 때 안전 절차(비상 복귀 또는 대기)가 정확히 수행되는지 확인합니다.
- **조건**: 초기 풍속 5 m/s -> 300초 후 15 m/s (돌풍 20 m/s), 시정 10 km -> 2 km
- **절차**:
  1. `VariableWind` + `ShearWind` 복합 기상 모델을 적용합니다.
  2. 풍속 10 m/s 초과 시 `APF_PARAMS_WINDY` 자동 전환을 확인합니다.
  3. 풍속 15 m/s 초과 시 비상 RTL 또는 안전 대기 절차 개시를 검증합니다.
- **통과 기준**: APF 파라미터 전환 < 1초, 비상 절차 개시 < 5초, 충돌 0건

#### B-6: BVLOS 장거리 경로 효율 (Long-Range Route Efficiency)

- **목적**: BVLOS 최대 운용 거리(8 km)에서 경로 계획 효율이 기준 이내인지 확인합니다.
- **조건**: 풍속 8 m/s, 시정 10 km, 비행 거리 5~8 km, 드론 30대
- **절차**:
  1. 출발-목적지 거리 5 km, 6 km, 7 km, 8 km 경로를 생성합니다.
  2. CBS + FlightPathPlanner의 경로 계획 결과를 직선 거리 대비 비교합니다.
  3. 중간 경유지(waypoint) 수와 에너지 소모량을 기록합니다.
- **통과 기준**: 경로 효율(실제 거리/직선 거리) <= 1.20, 배터리 잔량 >= 15% 도착

#### B-7: 다수 드론 BVLOS 동시 운용 (Multi-Drone BVLOS Simultaneous Operation)

- **목적**: 대규모(100대) BVLOS 동시 운용에서 ATC 시스템의 처리 능력과 안전성을 검증합니다.
- **조건**: 풍속 10 m/s, 시정 10 km, 드론 100대, 비행 거리 3~8 km
- **절차**:
  1. 100대 드론에 무작위 BVLOS 경로를 할당합니다.
  2. `AirspaceController`의 동시 clearance 처리 능력을 측정합니다.
  3. 10분간 충돌률, 충돌 해결률, clearance 지연을 기록합니다.
- **통과 기준**: 충돌 0건, 충돌 해결률 >= 99.5%, clearance 지연 P95 < 5초

#### B-8: BVLOS 비상 착륙 구역 선정 (Emergency Landing Zone Selection)

- **목적**: BVLOS 운용 중 비상 상황 발생 시 최적 비상착륙 구역을 실시간으로 선정하는 기능을 검증합니다.
- **조건**: 풍속 8 m/s, 시정 5 km, 비상착륙 구역 후보 10개소 사전 등록
- **절차**:
  1. 비행 중 드론 3대에 `MOTOR_FAILURE` 장애를 주입합니다.
  2. 비상착륙 구역 선정 알고리즘이 바람 방향, 거리, 장애물을 고려하여 최적 구역을 선택하는지 확인합니다.
  3. 선택된 구역까지의 활공 경로(glide path)가 안전한지 검증합니다.
- **통과 기준**: 구역 선정 < 2초, 활공 경로 충돌 0건, 착륙 성공률 100%

#### B-9: Remote ID 연속 방송 검증 (Remote ID Continuous Broadcast)

- **목적**: BVLOS 전 구간에서 Remote ID가 중단 없이 방송되는지 확인합니다.
- **조건**: 풍속 5 m/s, 시정 10 km, 드론 50대, 비행 시간 600초
- **절차**:
  1. 전체 드론에서 Remote ID 메시지(위치, 속도, 운영자 ID)를 1 Hz로 방송합니다.
  2. 600초간 수신 로그를 수집하여 누락률을 계산합니다.
  3. C2 링크 품질 저하 구간에서도 Remote ID 방송이 유지되는지 확인합니다.
- **통과 기준**: Remote ID 방송률 >= 99.5%, 최대 연속 누락 < 3초

#### B-10: BVLOS 복합 비상 시나리오 (BVLOS Compound Emergency)

- **목적**: BVLOS 운용 중 복수의 비상 상황(통신 두절 + 기상 악화 + 배터리 부족)이 동시 발생할 때 시스템의 종합 대응 능력을 검증합니다.
- **조건**: 풍속 12 m/s (돌풍 18 m/s), 시정 3 km, 드론 80대, 복합 장애 주입
- **절차**:
  1. 300초 시점: 드론 10%에 C2 링크 두절을 주입합니다.
  2. 360초 시점: 풍속 15 m/s 돌풍을 주입합니다.
  3. 420초 시점: 드론 5%에 `BATTERY_CRITICAL` 장애를 주입합니다.
  4. 각 비상 상황에 대한 우선순위 기반 대응을 검증합니다.
- **통과 기준**: 충돌 0건, 모든 비상 드론 안전 착륙, 비상 대응 시간 P95 < 10초

---

### 3.2 BVLOS 시나리오 파라미터 표 (BVLOS Scenario Parameter Table)

| ID | 시나리오 명 | 풍속 (m/s) | 시정 (km) | 고도 (m AGL) | 드론 수 | 통과 기준 | SDACS 모듈 매핑 |
|---|---|:-:|:-:|:-:|:-:|---|---|
| B-1 | C2 링크 단절 절차 | 8 | 10 | 60~120 | 30 | 프로토콜 100%, 충돌 0 | Lost-link Protocol, `ContingencyPlanner` |
| B-2 | DAA 시스템 성능 | 5 | 10 | 30~120 | 50+5 | 탐지 >= 99%, 회피 100% | CPA 모듈, `AdvancedPathPlanner` |
| B-3 | 최대 통신 거리 | 5 | 10 | 60~120 | 20 | 손실 < 2%@2km | `CommQualitySimulator`, `comm_range_m` |
| B-4 | 지상국 핸드오버 | 5 | 10 | 60~120 | 20 | 핸드오버 < 3초, 공백 0 | `AirspaceControllerHA`, `CommRelayPlanner` |
| B-5 | 기상 악화 대응 | 5->15+gust | 10->2 | 60~120 | 50 | 전환 < 1초, 충돌 0 | `VariableWind`, `ShearWind`, `APF_PARAMS_WINDY` |
| B-6 | 장거리 경로 효율 | 8 | 10 | 60~120 | 30 | 효율 <= 1.20, 배터리 >= 15% | `FlightPathPlanner`, CBS Planner |
| B-7 | 다수 BVLOS 동시 운용 | 10 | 10 | 30~120 | 100 | 해결률 >= 99.5%, 충돌 0 | `AirspaceController`, 5계층 전체 |
| B-8 | 비상착륙 구역 선정 | 8 | 5 | 30~120 | 30 | 선정 < 2초, 착륙 100% | `RecoveryPlanner`, `GlidepathController` |
| B-9 | Remote ID 연속 방송 | 5 | 10 | 30~120 | 50 | 방송률 >= 99.5% | UTM 모듈, Remote ID |
| B-10 | 복합 비상 시나리오 | 12+gust18 | 3 | 30~120 | 80 | 충돌 0, 안전 착륙 100% | 5계층 전체 + `ContingencyPlanner` |

---

## 4. 특별비행승인 신청 체크리스트 (Approval Document Checklist)

대한민국 항공안전법 및 드론활용촉진법에 따른 야간·BVLOS 특별비행승인 신청 시 구비 문서 및 확인 항목입니다.

### 4.1 야간 비행 승인 체크리스트 (20항목)

| # | 체크 항목 | 근거 법령 | 상태 |
|:-:|---|---|:-:|
| 1 | 충돌방지등 장착 및 작동 확인 | 항공안전법 시행규칙 SS310 | [ ] |
| 2 | 위치등(좌-적, 우-녹, 후-백) 장착 | 항공안전법 시행규칙 SS310 | [ ] |
| 3 | 착륙등 장착 및 원격 점등 가능 | 항공안전법 시행규칙 SS310 | [ ] |
| 4 | 비상 착륙지 조명 확보 | 항공안전법 시행규칙 SS310 | [ ] |
| 5 | 시각감시자(Visual Observer) 배치 계획 | 항공안전법 시행규칙 SS310 | [ ] |
| 6 | 감시자-조종자 통신 장비 시험 성적서 | 항공안전법 시행규칙 SS310 | [ ] |
| 7 | GPS + INS 이중화 항법 시스템 확인 | 드론 특별비행 가이드라인 | [ ] |
| 8 | 야간 장애물 데이터베이스 로드 확인 | 드론 특별비행 가이드라인 | [ ] |
| 9 | 배터리 잔량 30% 이상 비행 시작 조건 설정 | 드론 특별비행 가이드라인 | [ ] |
| 10 | 야간 비행 보험 가입 증명서 | 항공안전법 SS129 | [ ] |
| 11 | 기상 확인 (풍속 <= 10 m/s, 시정 >= 5 km) | 항공안전법 시행규칙 SS310 | [ ] |
| 12 | NOTAM(항공고시보) 발행 확인 | 항공안전법 SS68 | [ ] |
| 13 | 비상 절차 브리핑 완료 | 항공안전법 시행규칙 SS310 | [ ] |
| 14 | RTL 경로 장애물 클리어 확인 | 드론 특별비행 가이드라인 | [ ] |
| 15 | 지상 안전 구역(Ground Risk Buffer) 설정 | JARUS SORA 2.5 | [ ] |
| 16 | 텔레메트리 기록 시스템 정상 작동 확인 | 드론활용촉진법 시행규칙 SS26 | [ ] |
| 17 | 등화 전용 배터리 잔량 확인 (본체와 별도) | 항공안전법 시행규칙 SS310 | [ ] |
| 18 | 비행 경로 인근 항공기 정보 확인 (AIP) | 항공안전법 SS68 | [ ] |
| 19 | 지자체 및 관할 기관 사전 통보 | 항공안전법 시행규칙 SS308 | [ ] |
| 20 | 조종자 야간 비행 자격 확인 (1종 이상) | 항공안전법 SS125 | [ ] |

### 4.2 BVLOS 비행 승인 체크리스트 (20항목)

| # | 체크 항목 | 근거 법령 | 상태 |
|:-:|---|---|:-:|
| 1 | DAA(탐지 및 회피) 시스템 장착 | EASA SC-RPAS, ASTM F3442 | [ ] |
| 2 | C2 링크 이중화 (Primary: LTE + Backup: RF) | 드론활용촉진법 시행규칙 SS26 | [ ] |
| 3 | C2 단절 시 자동 복귀(Lost-link Protocol) | 드론활용촉진법 시행규칙 SS26 | [ ] |
| 4 | ADS-B Out 송출기 장착 | 항공안전법 SS127의2 | [ ] |
| 5 | Remote ID 방송 (ASTM F3411 준수) | 항공안전법 SS127의2 | [ ] |
| 6 | 통신 범위 시험 (최대 운용 거리의 120%) | 드론 특별비행 가이드라인 | [ ] |
| 7 | 비상착륙지 3개소 이상 지정 | 드론 특별비행 가이드라인 | [ ] |
| 8 | 에너지 예측 및 안전 마진 확보 (>= 20%) | 드론 특별비행 가이드라인 | [ ] |
| 9 | 기상 실시간 모니터링 시스템 연동 | 드론활용촉진법 시행규칙 SS26 | [ ] |
| 10 | 비행 경로 NFZ(비행금지구역) 간섭 없음 확인 | 항공안전법 SS127 | [ ] |
| 11 | SORA 리스크 평가 완료 | 가이드라인 2024개정 | [ ] |
| 12 | BVLOS 보장 포함 보험 가입 증명서 | 항공안전법 SS129 | [ ] |
| 13 | 비행계획 신고 완료 | 항공안전법 시행규칙 SS308 | [ ] |
| 14 | 지상 안전 완충 구역(Ground Risk Buffer) 설정 | JARUS SORA 2.5 | [ ] |
| 15 | 핸드오버 절차 검증 완료 (다중 GCS 운용 시) | 드론활용촉진법 시행규칙 SS26 | [ ] |
| 16 | 텔레메트리 기록 1 Hz 이상 확보 | 드론활용촉진법 시행규칙 SS26 | [ ] |
| 17 | 풍속 한계(>= 12 m/s) 자동 중단 설정 | 드론 특별비행 가이드라인 | [ ] |
| 18 | 조종자 BVLOS 비행 경험 50시간 이상 증빙 | 항공안전법 SS125 | [ ] |
| 19 | 비상 절차 시뮬레이션 훈련 완료 (B-1~B-10) | 가이드라인 2024개정 | [ ] |
| 20 | 관할 항공청 승인서 수령 | 항공안전법 시행규칙 SS310 | [ ] |

---

## 5. SDACS 시뮬레이션 통합 가이드 (SDACS Integration Guide)

### 5.1 Config YAML 기본 파라미터 참조

모든 시나리오는 `config/default_simulation.yaml`을 기본으로 하되, 다음 파라미터를 오버라이드하여 야간/BVLOS 조건을 재현합니다.

```yaml
# config/default_simulation.yaml 기본값 참조
simulation:
  seed: 42
  duration_minutes: 10
  time_step_hz: 10
  control_hz: 1

drones:
  default_count: 100
  max_speed_ms: 15.0
  cruise_speed_ms: 8.0
  comm_range_m: 2000.0
  battery_capacity_wh: 50.0

separation_standards:
  lateral_min_m: 50.0
  vertical_min_m: 15.0
  conflict_lookahead_s: 90.0
```

### 5.2 야간 시나리오 오버라이드 파라미터

```yaml
# 야간 공통 확장 파라미터 (scenario_params/night_common.yaml 생성 권장)
night_operations:
  enabled: true
  civil_twilight_offset_min: -30   # 일몰 30분 후 시작
  visibility_km: 3.0               # 기본 야간 시정
  lighting:
    mode: NIGHT_ANTI_COLLISION
    flash_rate_hz: 1.0
    intensity_cd: 400               # 칸델라
    failure_injection:
      enabled: false                 # N-3에서 true로 전환
      affected_ratio: 0.15
  sensor:
    mode: NIGHT_IR                   # 야간 적외선 센서 모델
    detection_range_factor: 0.6      # 주간 대비 60% 탐지 거리
  visual_observer:
    count: 3
    heartbeat_interval_s: 10
    max_latency_ms: 500
```

### 5.3 BVLOS 시나리오 오버라이드 파라미터

```yaml
# BVLOS 공통 확장 파라미터 (scenario_params/bvlos_common.yaml 생성 권장)
bvlos_operations:
  enabled: true
  max_range_m: 8000                  # BVLOS 최대 운용 거리
  c2_link:
    primary: LTE
    backup: RF_868MHZ
    redundancy: true
    loss_detection_timeout_s: 5
  lost_link_protocol:
    phase1_loiter_s: 30              # comms_loss.yaml 참조
    phase2_rtl_altitude_m: 80.0
    phase3_land: true
  daa:
    enabled: true
    sensor_range_m: 500
    min_separation_m: 100
    reaction_time_s: 2.0
  remote_id:
    broadcast_hz: 1.0
    fields: [position, velocity, operator_id, flight_id]
  handover:
    overlap_zone_m: 500
    max_transition_time_s: 3.0
```

### 5.4 시나리오별 Config 매핑

| 시나리오 | 기반 Config | 오버라이드 항목 | 실행 명령 |
|---|---|---|---|
| N-1 | `default_simulation.yaml` | `night_common.yaml` | `python main.py scenario night_lighting` |
| N-2 | `default_simulation.yaml` | `night_common.yaml` + observer 확장 | `python main.py scenario night_observer_comm` |
| N-3 | `default_simulation.yaml` | `lighting.failure_injection.enabled: true` | `python main.py scenario night_lighting_failure` |
| N-4 | `default_simulation.yaml` | `sensor.detection_range_factor: 0.6` + 장애물 | `python main.py scenario night_obstacle` |
| N-5 | `default_simulation.yaml` | `gps.jammed_zone_radius_m: 500` | `python main.py scenario night_gps_denied` |
| N-6 | `mass_takeoff.yaml` | `night_common.yaml` 병합 | `python main.py scenario night_mass_takeoff` |
| N-7 | `default_simulation.yaml` | `visibility_km: 0.8`, `wind: gust` | `python main.py scenario night_low_vis` |
| N-8 | `emergency_failure.yaml` | `night_common.yaml` + `battery_drain_rate: 3x` | `python main.py scenario night_low_battery` |
| N-9 | `comms_loss.yaml` | `night_common.yaml` 병합 | `python main.py scenario night_comms_loss` |
| N-10 | `high_density.yaml` | `night_common.yaml` + `weather_disturbance` 병합 | `python main.py scenario night_high_density` |
| B-1 | `comms_loss.yaml` | `bvlos_common.yaml` | `python main.py scenario bvlos_c2_loss` |
| B-2 | `default_simulation.yaml` | `bvlos_common.yaml` + DAA 확장 | `python main.py scenario bvlos_daa` |
| B-3 | `default_simulation.yaml` | `comm_range_m` 점진 확장 | `python main.py scenario bvlos_max_range` |
| B-4 | `default_simulation.yaml` | `bvlos_common.yaml` + handover 확장 | `python main.py scenario bvlos_handover` |
| B-5 | `weather_disturbance.yaml` | `bvlos_common.yaml` 병합 | `python main.py scenario bvlos_weather` |
| B-6 | `default_simulation.yaml` | `route: min_distance 5km~8km` | `python main.py scenario bvlos_long_range` |
| B-7 | `high_density.yaml` | `bvlos_common.yaml` 병합 | `python main.py scenario bvlos_multi_drone` |
| B-8 | `emergency_failure.yaml` | `bvlos_common.yaml` + landing zone | `python main.py scenario bvlos_emergency_land` |
| B-9 | `default_simulation.yaml` | `remote_id.broadcast_hz: 1.0` | `python main.py scenario bvlos_remote_id` |
| B-10 | `default_simulation.yaml` | 복합: comms_loss + weather + battery | `python main.py scenario bvlos_compound` |

### 5.5 기존 시나리오 Config 참조 관계

```
config/
+-- default_simulation.yaml          <-- 모든 시나리오의 기반
+-- monte_carlo.yaml                 <-- MC 스윕 설정 (N-10, B-10 변형 가능)
+-- scenario_params/
    +-- high_density.yaml            <-- N-10, B-7 기반
    +-- mass_takeoff.yaml            <-- N-6 기반
    +-- emergency_failure.yaml       <-- N-8, B-8 기반
    +-- comms_loss.yaml              <-- N-9, B-1 기반
    +-- weather_disturbance.yaml     <-- N-7, B-5 기반
    +-- route_conflict.yaml          <-- B-6 경로 효율 참조
    +-- adversarial_intrusion.yaml   <-- B-2 비협조 항공기 참조
    +-- multi_city.yaml              <-- B-4 핸드오버 참조
    +-- swarm_autonomous_no_preplan.yaml <-- GPS denied 참조
```

### 5.6 SDACS 모듈-시나리오 매핑 종합

| SDACS 모듈 | 소스 파일 | 야간 시나리오 | BVLOS 시나리오 |
|---|---|---|---|
| `DroneAgent` | `simulation/drone_agent.py` | N-1 ~ N-10 전체 | B-1 ~ B-10 전체 |
| `SwarmSimulator` | `src/boids_swarm.py` | N-4 (APF), N-10 | B-7, B-10 |
| `AirspaceController` | `src/airspace_control/controller/airspace_controller.py` | N-6, N-10 | B-2, B-7, B-10 |
| `AirspaceControllerHA` | `src/raft/airspace_controller_ha.py` | -- | B-4 |
| `FlightPathPlanner` | `src/airspace_control/planning/flight_path_planner.py` | N-6 | B-6 |
| `AdvancedPathPlanner` | `simulation/advanced_path_planner.py` | N-4, N-7 | B-2 |
| `ContingencyPlanner` | `simulation/contingency_planner.py` | N-3 | B-1, B-10 |
| `RecoveryPlanner` | `simulation/emergency_recovery_system.py` | N-8 | B-8 |
| `BatteryOptimizationController` | `simulation/battery_optimization_controller.py` | N-8 | B-6 |
| `CommQualitySimulator` | `simulation/comm_quality.py` | N-2 | B-3 |
| `CommRelayPlanner` | `simulation/comm_relay.py` | N-9 | B-4 |
| `WindModel` (Constant/Variable/Shear) | `simulation/weather.py` | N-7, N-9, N-10 | B-5, B-10 |
| `GlidepathController` | `simulation/autonomous_landing.py` | -- | B-8 |
| CBS Planner | `cbs_planner` config section | N-10 | B-6, B-7 |
| CPA 모듈 | `AirspaceController` 내장 | N-7 | B-2 |
| APF 모듈 | `SwarmSimulator.apf_avoidance()` | N-4, N-10 | B-5, B-10 |
| UTM / Remote ID | UTM 계층 | -- | B-9 |

---

## 6. 검증 결과 기록 양식 (Verification Result Template)

각 시나리오 수행 후 아래 양식에 따라 결과를 기록합니다.

```
============================================================
 시나리오 검증 결과서
============================================================
시나리오 ID   : [N-XX / B-XX]
시나리오 명   : [한글명]
수행 일시     : YYYY-MM-DD HH:MM KST
수행자        : [이름 / 소속]
SDACS 버전    : [git commit hash]
Config 파일   : [사용한 YAML 경로]

[조건]
- 풍속          : ____ m/s (모델: Constant / Variable / Shear)
- 시정          : ____ km
- 고도 범위     : ____ ~ ____ m AGL
- 드론 수       : ____대
- 시뮬레이션 시간: ____초
- 난수 시드     : ____

[결과]
- 충돌 건수        : ____
- 충돌 해결률      : ____% (공식: 1 - collisions/(conflicts + collisions))
- 경로 효율        : ____ (실제 거리 / 직선 거리)
- 핵심 지표        : [시나리오별 통과 기준 대비 실측값]

[판정]
- PASS / FAIL
- 비고: [특이사항, 개선 필요 항목]
============================================================
```

---

## 7. 변경 이력 (Revision History)

| 버전 | 일자 | 작성자 | 변경 내용 |
|:-:|---|---|---|
| 0.1 | 2026-06-18 | SDACS Team | 초안 작성 -- GENESIS Phase 310 기본 구조 |
| 1.0 | 2026-06-18 | SDACS Team | 정식 버전 -- 시나리오 상세 기술, Config 매핑, 모듈 매핑 종합, 체크리스트 확장 |

---

*GENESIS Phase 310 -- 야간 및 비가시권(BVLOS) 특별비행승인 요건 검증 시나리오 정의 완료*
