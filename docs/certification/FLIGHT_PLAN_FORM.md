# 📋 비행계획 신고 양식 자동 생성 (GENESIS Phase 303)

*Created: 2026-06-17 · 근거 법령: 항공안전법 시행규칙 §306 (비행계획 제출), 드론원스톱 시스템 (Drone One-Stop)*
*면책: 본 문서는 SDACS 시뮬레이션 데이터를 드론원스톱 비행계획 신고 양식에 매핑하기 위한 **개발자 참고 자료**이며, 운영자의 법적 신고 의무를 갈음하지 않는다. 실 운영 시 최신 시행규칙·국토교통부 고시·드론원스톱 시스템 공지를 확인해야 한다.*

---

## 1. 개요

드론원스톱(Drone One-Stop)은 국토교통부가 운영하는 무인비행장치 비행승인 통합 포털이다.
항공안전법 시행규칙 §306에 따라 비행계획을 신고해야 하며, SDACS는 시뮬레이션 시나리오 데이터로부터
이 신고 양식의 대부분 필드를 자동 추출하여 JSON/PDF로 export하는 파이프라인을 제공한다.

**목표:**
- 시뮬레이션 시나리오 1건 → 드론원스톱 신청서 1건 자동 생성
- 수동 입력 최소화 (운영자 서명·보험 증서 등 외부 절차만 잔여)
- SORA 결과(GENESIS 302) 자동 첨부

---

## 2. 비행계획 신고 양식 필드 매핑

드론원스톱 신청서의 주요 필드와 SDACS 모듈 간 매핑을 정의한다.

### 2.1 신청자 정보

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 신청자 성명 | 운영자 이름 | `config/operator_profile.yaml` `name` | 외부 입력 |
| 연락처 | 전화번호 | `config/operator_profile.yaml` `phone` | 외부 입력 |
| 소속 기관 | 회사/기관명 | `config/operator_profile.yaml` `organization` | 외부 입력 |
| 자격증명 번호 | 1~4종 자격번호 | `config/operator_profile.yaml` `license_id` | Phase 309 매핑 참조 |

> **주의:** 신청자 정보는 시뮬레이션 데이터가 아닌 운영자 프로파일 설정 파일에서 읽는다.
> `config/operator_profile.yaml`은 `.gitignore` 대상이며, 템플릿만 제공한다.

### 2.2 기체 정보

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 기체 종류 | 멀티콥터/고정익/VTOL | `DroneProfile.name` → `UAType` 매핑 | `simulation/remote_id.py` `UAType` enum |
| 최대이륙중량 (MTOW) | kg | `DroneProfile` 기반 산정 | `src/airspace_control/agents/drone_profiles.py` |
| 기체 등록번호 | 국토부 등록번호 | `config/operator_profile.yaml` `registration_id` | 외부 입력 |
| 제조사·모델명 | 기체 제조 정보 | `config/operator_profile.yaml` `aircraft_model` | 외부 입력 |
| Remote ID | ASTM F3411 식별자 | `RemoteIDMessage.uas_id` | `simulation/remote_id.py` |

> `DRONE_PROFILES` 5종(`COMMERCIAL_DELIVERY`, `SURVEILLANCE`, `EMERGENCY`, `RECREATIONAL`, `ROGUE`)은
> 시뮬레이션용 프로파일이며, 실 기체 등록 정보와 1:1 대응하지 않을 수 있다.

### 2.3 비행 목적

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 비행 목적 | 촬영/배송/순찰/긴급 등 | `MissionType` enum | `simulation/mission_scheduler.py` |
| 세부 설명 | 미션 상세 | 시나리오 YAML `description` | `config/scenario_params/*.yaml` |

`MissionType` → 드론원스톱 비행 목적 코드 매핑:

| `MissionType` | 드론원스톱 분류 | 코드 |
|---|---|---|
| `EMERGENCY` | 긴급 구조·수색 | `PURPOSE_EMERGENCY` |
| `SURVEILLANCE` | 감시·정찰·촬영 | `PURPOSE_SURVEILLANCE` |
| `DELIVERY` | 화물 배송 | `PURPOSE_DELIVERY` |
| `PATROL` | 순찰 | `PURPOSE_PATROL` |
| `INSPECTION` | 시설 점검 | `PURPOSE_INSPECTION` |

### 2.4 비행 일시·기간

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 비행 시작 일시 | 예정 비행 시작 | 시나리오 실행 시각 또는 수동 입력 | ISO 8601 (KST) |
| 비행 종료 일시 | 예정 비행 종료 | `simulation_duration_min` 기반 산정 | 시나리오 YAML |
| 비행 시간 (분) | 총 비행 시간 | `config/default_simulation.yaml` `duration_minutes` | 기본 10분 |

### 2.5 비행 구역

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 중심 좌표 (위도/경도) | 비행 구역 중심 | `config/default_simulation.yaml` `airspace.home.lat/lon` | 기본: 35.1595°N, 126.8526°E (광주) |
| 비행 반경 (m) | 구역 반경 | `airspace.bounds_km` → 반경 변환 | `area_km2` 기반 |
| 최저 고도 (m AGL) | 하한 고도 | `drones.min_altitude_m` | 기본 30m |
| 최고 고도 (m AGL) | 상한 고도 | `drones.max_altitude_m` | 기본 120m |
| NFZ 회피 구역 | 비행금지구역 | 시나리오 YAML `nfz` 섹션 | `_sdacs.injectDynamicNFZ()` |
| 회랑 정보 | 지정 비행 경로 | 시나리오 YAML `corridors` 섹션 | 해당 시 |

### 2.6 비행 방식

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 비행 방식 | 자율/수동/BVLOS | `FlightPhase` + 시나리오 설정 | `src/airspace_control/agents/drone_state.py` |
| 가시권 여부 | VLOS/BVLOS | 시나리오 YAML `bvlos` 플래그 | BVLOS 시 SORA 의무 |
| 군집 여부 | 군집 비행 | `drone_count > 1` | SDACS 기본 군집 |
| 자율비행 수준 | 자율/반자율/수동 | `DroneAgent` FSM 모드 | 시나리오별 설정 |

`FlightPhase` enum 값 참조:

| `FlightPhase` | 의미 | 비행 방식 분류 |
|---|---|---|
| `GROUNDED` | 지상 대기 | — |
| `TAKEOFF` | 이륙 | 자율 |
| `ENROUTE` | 경로 비행 | 자율 (CBS 경로) |
| `HOLDING` | 체공 대기 | 자율 (ATC 명령) |
| `LANDING` | 착륙 | 자율 |
| `RTL` | 복귀 (Lost-link) | 자율 비상 |
| `EVADING` | APF 회피 기동 | 자율 긴급 |
| `FAILED` | 고장 | — |

### 2.7 안전 대책

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 충돌 방지 체계 | DAA 설명 | 5계층 안전망 (L1-L5) | RTM Phase 306 참조 |
| 비상 절차 | RTL/착륙 절차 | `DroneAgent` RTL FSM | Lost-link 자동 복귀 |
| 통신 두절 대응 | Lost-link 프로토콜 | `CommsStatus` + `FailureType` | `drone_state.py` |
| 기상 제한 | 풍속 제한 등 | `APF_PARAMS_WINDY` (>10 m/s 전환) | `src/airspace_control/apf_params.py` |

5계층 안전망 요약 (드론원스톱 안전 대책 기술서용):

| 계층 | 이름 | 기능 | 갱신 주기 |
|---|---|---|---|
| L1 | APF | 즉시 척력 장애물 회피 | 10 Hz |
| L2 | CBS | 다중 에이전트 경로 충돌 해소 | 0.1 Hz |
| L3 | CPA | 90초 미래 충돌 예측 경보 | 1 Hz |
| L4 | ATC | 전역 관제 명령 (9종) | 1 Hz |
| L5 | UTM | NFZ·Remote ID·LAANC 전략 관리 | 0.1 Hz |

### 2.8 보험 정보

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| 보험 가입 여부 | 필수 | `InsuranceRiskCalculator` 결과 | `simulation/insurance_risk.py` |
| 보험사·증권번호 | 증서 정보 | `config/operator_profile.yaml` `insurance` | 외부 입력 |
| 보상 한도 (원) | 보험 한도 | `TIER_LIMIT_KRW` | BASIC 5천만 / STANDARD 2억 / PREMIUM 10억 |
| 리스크 등급 | 보험료 산정 근거 | `RiskFactors` → `InsuranceRiskCalculator` | Phase 696 |

### 2.9 Remote ID

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| RID 송출 방식 | Broadcast/Network | `simulation/remote_id.py` | ASTM F3411 v2.0 |
| UA 타입 | 기체 분류 | `UAType` enum | MULTIROTOR/AIRPLANE/VTOL/기타 |
| 식별 방식 | 일련번호/등록번호 | `IDType` enum | `SERIAL_NUMBER` / `REGISTRATION_ID` |
| 운영자 ID | 원격조종자 식별 | `RemoteIDMessage.operator_id` | |

### 2.10 SORA 평가 결과

| 양식 필드 | 설명 | SDACS 소스 | 비고 |
|---|---|---|---|
| iGRC (지상 위험 등급) | Intrinsic GRC | `_sdacs.soraAssess()` | GENESIS 302 |
| ARC (공중 위험 등급) | Air Risk Class | `_sdacs.soraAssess()` | JARUS 2.0 |
| SAIL (특정 보증 수준) | SAIL I-VI | `_sdacs.soraAssess()` 결과 | iGRC x ARC 매트릭스 |
| OSO (운영 안전 목표) | 26개 항목 | SORA Annex E 기반 | SAIL별 필수 OSO |
| 인구 밀도 구분 | sparsely/populated/assembly | `soraAssess({ populationDensity })` | 시나리오 입력 |

---

## 3. 자동 생성 파이프라인

SDACS 시뮬레이션 시나리오에서 드론원스톱 신청서 데이터를 자동 추출하는 4단계 파이프라인이다.

### Step 1: 시나리오 YAML에서 비행 구역·기간 추출

```
시나리오 YAML (config/scenario_params/*.yaml)
    ↓ 파싱
├── drone_count          → 기체 수
├── simulation_duration_min → 비행 시간
├── area_km2             → 비행 반경 산정
└── drone_profile_distribution → 기체 종류 비율

기본 설정 (config/default_simulation.yaml)
    ↓ 병합
├── airspace.home.lat/lon → 중심 좌표
├── airspace.bounds_km    → 구역 경계
├── drones.min_altitude_m → 최저 고도
└── drones.max_altitude_m → 최고 고도
```

### Step 2: DroneAgent 설정에서 기체 제원 매핑

```
DroneProfile (src/airspace_control/agents/drone_profiles.py)
    ↓ 변환
├── max_speed_ms     → 최대 속도 (km/h 변환)
├── max_altitude_m   → 최고 비행 고도
├── endurance_min    → 최대 체공 시간
├── battery_wh       → 배터리 용량
└── comm_range_m     → 통신 범위

UAType (simulation/remote_id.py)
    ↓ 매핑
└── MULTIROTOR / AIRPLANE / VTOL → 드론원스톱 기체 종류 코드
```

### Step 3: soraAssess() 호출 → SAIL 등급 첨부

```
soraAssess({
  populationDensity: "populated",
  bvlos: true,
  maxHeight: 120,
  droneWeight: 25
})
    ↓ 결과
├── iGRC       → 지상 위험 등급
├── arc        → 공중 위험 등급
├── sail       → SAIL I-VI
└── oso[]      → 필수 운영 안전 목표 리스트

→ 결과를 flight_plan.sora 필드에 자동 삽입
```

### Step 4: JSON/PDF Export

```
flight_plan_data (Python dict)
    ↓ 검증 (flight_plan.schema.json)
    ↓ 직렬화
├── flight_plan.json    → 기계 판독용 (API 연동)
├── flight_plan.pdf     → 인쇄·제출용 (reportlab / weasyprint)
└── flight_plan.csv     → 대량 신청 시 일괄 업로드
```

---

## 4. Export 포맷 스펙 (`flight_plan.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "sdacs://flight-plan/v1",
  "title": "SDACS 비행계획 신고 양식",
  "type": "object",
  "required": ["applicant", "aircraft", "flight", "safety", "sora"],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0.0"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time",
      "description": "양식 생성 시각 (ISO 8601, KST)"
    },
    "applicant": {
      "type": "object",
      "required": ["name", "phone", "license_id"],
      "properties": {
        "name": { "type": "string" },
        "phone": { "type": "string", "pattern": "^\\d{2,3}-\\d{3,4}-\\d{4}$" },
        "organization": { "type": "string" },
        "license_id": { "type": "string", "description": "1~4종 자격번호" },
        "license_grade": { "type": "integer", "minimum": 1, "maximum": 4 }
      }
    },
    "aircraft": {
      "type": "object",
      "required": ["ua_type", "mtow_kg", "registration_id"],
      "properties": {
        "ua_type": { "type": "string", "enum": ["MULTIROTOR", "AIRPLANE", "VTOL", "HELICOPTER", "OTHER"] },
        "mtow_kg": { "type": "number", "minimum": 0 },
        "registration_id": { "type": "string", "description": "국토부 등록번호" },
        "manufacturer": { "type": "string" },
        "model": { "type": "string" },
        "remote_id": {
          "type": "object",
          "properties": {
            "uas_id": { "type": "string" },
            "id_type": { "type": "string", "enum": ["SERIAL_NUMBER", "REGISTRATION_ID", "UTM_ASSIGNED"] },
            "operator_id": { "type": "string" }
          }
        }
      }
    },
    "flight": {
      "type": "object",
      "required": ["purpose", "start_time", "end_time", "area"],
      "properties": {
        "purpose": {
          "type": "string",
          "enum": ["EMERGENCY", "SURVEILLANCE", "DELIVERY", "PATROL", "INSPECTION", "OTHER"]
        },
        "purpose_detail": { "type": "string" },
        "start_time": { "type": "string", "format": "date-time" },
        "end_time": { "type": "string", "format": "date-time" },
        "duration_min": { "type": "number", "minimum": 0 },
        "area": {
          "type": "object",
          "required": ["center_lat", "center_lon", "radius_m", "min_alt_m", "max_alt_m"],
          "properties": {
            "center_lat": { "type": "number", "minimum": -90, "maximum": 90 },
            "center_lon": { "type": "number", "minimum": -180, "maximum": 180 },
            "radius_m": { "type": "number", "minimum": 0 },
            "min_alt_m": { "type": "number", "minimum": 0 },
            "max_alt_m": { "type": "number", "minimum": 0, "maximum": 150 }
          }
        },
        "flight_mode": {
          "type": "string",
          "enum": ["AUTONOMOUS", "SEMI_AUTONOMOUS", "MANUAL"]
        },
        "bvlos": { "type": "boolean" },
        "swarm": { "type": "boolean" },
        "drone_count": { "type": "integer", "minimum": 1 }
      }
    },
    "safety": {
      "type": "object",
      "properties": {
        "daa_system": { "type": "string", "description": "DAA 체계 설명 (5계층 안전망)" },
        "emergency_procedure": { "type": "string", "description": "비상 절차 (RTL 등)" },
        "lost_link_protocol": { "type": "string" },
        "weather_limits": {
          "type": "object",
          "properties": {
            "max_wind_ms": { "type": "number" },
            "min_visibility_m": { "type": "number" }
          }
        },
        "safety_layers": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "layer": { "type": "string" },
              "name": { "type": "string" },
              "function": { "type": "string" },
              "update_hz": { "type": "number" }
            }
          }
        }
      }
    },
    "insurance": {
      "type": "object",
      "properties": {
        "insured": { "type": "boolean" },
        "provider": { "type": "string" },
        "policy_number": { "type": "string" },
        "coverage_tier": { "type": "string", "enum": ["BASIC", "STANDARD", "PREMIUM"] },
        "limit_krw": { "type": "integer" },
        "risk_score": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    },
    "sora": {
      "type": "object",
      "required": ["igrc", "arc", "sail"],
      "properties": {
        "igrc": { "type": "integer", "minimum": 1, "maximum": 12 },
        "arc": { "type": "string", "description": "Air Risk Class (ARC-a ~ ARC-d)" },
        "sail": { "type": "integer", "minimum": 1, "maximum": 6 },
        "population_density": { "type": "string", "enum": ["sparsely", "populated", "assembly"] },
        "oso_results": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "oso_id": { "type": "string" },
              "description": { "type": "string" },
              "level": { "type": "string", "enum": ["O", "L", "M", "H"] }
            }
          }
        }
      }
    }
  }
}
```

---

## 5. 드론원스톱 제출 흐름

실제 드론원스톱(drone.onestop.go.kr) 제출 절차와 SDACS 연동 지점을 정리한다.

### 5.1 제출 흐름도

```
[SDACS 시뮬레이션 완료]
    │
    ▼
(1) flight_plan export 실행
    │  → flight_plan.json 생성
    │  → flight_plan.pdf 생성
    │
    ▼
(2) 운영자: 드론원스톱 로그인
    │  (공동인증서 / 간편인증)
    │
    ▼
(3) 비행승인 신청 메뉴 진입
    │  → "비행계획 신고" 선택
    │
    ▼
(4) 양식 수동 입력 또는 SDACS JSON 참조 입력
    │  ├── 신청자 정보 → operator_profile
    │  ├── 기체 정보   → aircraft 섹션
    │  ├── 비행 구역   → flight.area 섹션
    │  ├── 비행 목적   → flight.purpose
    │  ├── 안전 대책   → safety 섹션 (PDF 첨부)
    │  └── SORA 결과   → sora 섹션 (PDF 첨부)
    │
    ▼
(5) 첨부 서류 업로드
    │  ├── 보험 증서 사본 (외부)
    │  ├── SORA 평가서 (SDACS 자동 생성)
    │  ├── 안전 대책서 (5계층 안전망 요약)
    │  └── 기체 등록증 사본 (외부)
    │
    ▼
(6) 신청서 제출
    │
    ▼
(7) 승인 대기 → 승인/보완/반려
```

### 5.2 SDACS 자동화 범위

| 단계 | 자동화 수준 | 설명 |
|---|---|---|
| (1) Export | 완전 자동 | 시나리오 데이터 → JSON/PDF |
| (2) 로그인 | 수동 | 운영자 인증 필수 |
| (3) 메뉴 진입 | 수동 | 드론원스톱 UI |
| (4) 양식 입력 | 반자동 | JSON 데이터 참조 입력 (향후 API 연동 시 완전 자동) |
| (5) 첨부 서류 | 반자동 | SORA·안전대책서는 SDACS 생성, 보험·등록증은 수동 |
| (6) 제출 | 수동 | 운영자 최종 확인·서명 |
| (7) 승인 | 외부 | 관할 기관 처리 |

### 5.3 향후 API 연동 계획 (ODYSSEY Track)

드론원스톱이 공개 API를 제공할 경우, SDACS에서 직접 제출하는 자동화 파이프라인을 구현할 수 있다.
현재(2026-06) 기준 공개 API는 미제공 상태이며, JSON export + 수동 입력이 최선이다.

---

## 6. 시나리오별 양식 예시

`config/scenario_params/high_density.yaml` 시나리오 기준 자동 추출 결과 예시:

| 필드 | 자동 추출값 |
|---|---|
| 비행 목적 | 배송(60%), 감시(30%), 긴급(10%) — 혼합 |
| 기체 수 | 100 |
| 비행 시간 | 10분 |
| 중심 좌표 | 35.1595°N, 126.8526°E |
| 비행 반경 | ~5,642m (area_km2=100 기준) |
| 최저/최고 고도 | 30m / 120m AGL |
| 비행 방식 | 자율 (AUTONOMOUS) |
| BVLOS | true (군집 운영 특성상) |
| 군집 여부 | true |

---

## 7. 구현 상태

| 항목 | 상태 | 비고 |
|---|---|---|
| 필드 매핑 정의 | 🟢 완료 | 본 문서 |
| JSON 스키마 | 🟢 완료 | `flight_plan.schema.json` 정의 |
| 시나리오 YAML 파서 | ⬜ 계획 | Step 1 구현 필요 |
| DroneProfile 변환기 | ⬜ 계획 | Step 2 구현 필요 |
| soraAssess 연동 | 🟢 사용 가능 | GENESIS 302 완료 |
| PDF 렌더러 | ⬜ 계획 | reportlab 또는 weasyprint |
| 드론원스톱 API 연동 | ⬜ 미정 | 공개 API 미제공 |

---

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 법령 적합성 매트릭스 (Phase 301), §306 항목
- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 5계층 안전망 RTM (Phase 306)
- [`KC_RADIO_CERTIFICATION.md`](KC_RADIO_CERTIFICATION.md) — 전파인증 체크리스트 (Phase 304)
- [`PILOT_LICENSE_MAPPING.md`](PILOT_LICENSE_MAPPING.md) — 조종자 자격증명 매핑 (Phase 309)
- [`AIRSPACE_CLASS_MAPPING.md`](AIRSPACE_CLASS_MAPPING.md) — ICAO 공역 클래스 매핑 (ODYSSEY 408)
- [`../SDACS_API.md`](../SDACS_API.md) — 407 API 실측 (`soraAssess` production)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 인증 Phase 301-320
