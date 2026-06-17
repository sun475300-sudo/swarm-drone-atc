# 보험 요율 산정 인터페이스 사양 (Insurance Rate Interface Specification)

*GENESIS Phase 308 · Created: 2026-06-18 · 근거: 항공사업법 §70, 드론활용촉진법 시행령 §15, 보험업법*

> SDACS 시뮬레이션의 리스크 산출 모델(`simulation/insurance_risk.py`)을 기반으로,
> 실제 보험사 시스템과 연동하기 위한 RESTful API 인터페이스를 정의합니다.
> 본 사양은 군집드론 운용자가 법정 의무보험에 가입하고 보험금을 청구하는 전체 생명주기를 포괄합니다.

---

## 1. 개요

### 1.1 목적

군집드론 공역통제 시스템(SDACS)과 보험사 백엔드 간의 데이터 교환 표준을 정의합니다.
기존 참조 구현체(`simulation/insurance_risk.py`의 `InsuranceRiskCalculator`)가 산출하는
리스크 점수 및 보험료 추정치를 보험사 API와 동기화하여, 실시간 견적·계약·증권 조회·보험금 청구를
자동화하는 것이 목표입니다.

### 1.2 참조 구현체

| 항목 | 값 |
|---|---|
| 모듈 경로 | `simulation/insurance_risk.py` |
| 핵심 클래스 | `InsuranceRiskCalculator` |
| 리스크 팩터 | `RiskFactors` (frozen dataclass, 7개 필드) |
| 보장 등급 | `CoverageTier` — BASIC / STANDARD / PREMIUM |
| 기본 보험료 | 50,000 KRW (base_premium_krw) |
| 등급별 한도 | BASIC 5천만원 / STANDARD 2억원 / PREMIUM 10억원 |

### 1.3 용어 정의

| 용어 | 정의 |
|---|---|
| Quote | 보험 견적 — 리스크 평가 기반 예상 보험료 산출 |
| Bind | 보험 계약 체결 — 견적을 수락하여 정식 증권 발행 |
| Policy | 보험 증권 — 유효한 보험 계약 문서 |
| Claim | 보험금 청구 — 사고 발생 시 보상 요청 |
| MTOW | Maximum Take-Off Weight — 최대이륙중량 (kg) |
| SAIL | Specific Assurance and Integrity Level — SORA 리스크 수준 |

---

## 2. API 엔드포인트 사양

### 2.1 공통 사항

| 항목 | 값 |
|---|---|
| Base URL | `https://{insurer-host}/api/v1/insurance` |
| 인증 | Bearer Token (API Key) — `Authorization: Bearer {api_key}` |
| Content-Type | `application/json; charset=utf-8` |
| 날짜 형식 | ISO 8601 (`YYYY-MM-DDTHH:mm:ssZ`) |
| 통화 단위 | KRW (원) — 정수 표현 |
| 에러 응답 | RFC 7807 Problem Details |

### 2.2 공통 에러 응답 형식

```json
{
  "type": "https://sdacs.example.com/errors/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "drone_mtow_kg must be finite and positive",
  "instance": "/api/v1/insurance/quote",
  "timestamp": "2026-06-18T09:00:00Z"
}
```

### 2.3 HTTP 상태 코드

| 코드 | 의미 | 사용 상황 |
|:-:|---|---|
| 200 | OK | 조회 성공 |
| 201 | Created | 계약 체결, 청구 접수 성공 |
| 400 | Bad Request | 요청 형식 오류 |
| 401 | Unauthorized | API 키 누락 또는 만료 |
| 404 | Not Found | 증권/청구 ID 미존재 |
| 422 | Unprocessable Entity | 리스크 팩터 값 범위 초과 |
| 429 | Too Many Requests | 요율 제한 초과 |
| 500 | Internal Server Error | 보험사 내부 오류 |

---

## 3. 엔드포인트 상세

### 3.1 POST /api/v1/insurance/quote — 보험 견적 요청

SDACS가 비행 계획 및 리스크 팩터를 전송하면, 보험사가 리스크 점수·추천 등급·예상 보험료를 반환합니다.

#### 요청 (Request)

```json
{
  "request_id": "uuid-v4",
  "operator": {
    "operator_id": "OP-2026-001",
    "operator_name": "SDACS Test Operator",
    "experience_hours": 250.0,
    "license_type": "SUPER_LIGHT_1",
    "license_number": "KR-UAS-2026-0042"
  },
  "drone": {
    "drone_id": "DR-SWARM-001",
    "model": "DJI Matrice 350 RTK",
    "mtow_kg": 9.2,
    "serial_number": "1ZNBJ4G00CC0001",
    "registration_number": "KR-UD-2026-00123"
  },
  "flight_plan": {
    "departure_time": "2026-06-18T09:00:00Z",
    "duration_hours": 2.5,
    "altitude_max_m": 120,
    "operation_area": {
      "center_lat": 37.5665,
      "center_lon": 126.9780,
      "radius_m": 500
    }
  },
  "risk_factors": {
    "population_density": 5200.0,
    "flight_hours": 2.5,
    "weather_severity": 0.3,
    "drone_mtow_kg": 9.2,
    "operator_experience_hours": 250.0,
    "payload_hazard_level": 1,
    "proximity_airports_km": 12.5
  },
  "coverage_tier_preference": "STANDARD"
}
```

#### 요청 필드 사양

| 필드 | 타입 | 필수 | 설명 | 제약 조건 |
|---|---|:-:|---|---|
| `request_id` | string (UUID) | O | 요청 고유 식별자 | UUID v4 형식 |
| `operator.operator_id` | string | O | 운용자 식별 번호 | — |
| `operator.experience_hours` | float | O | 운용 경력 시간 | >= 0 |
| `operator.license_type` | string | O | 자격증 종류 | 아래 표 참조 |
| `drone.mtow_kg` | float | O | 최대이륙중량 (kg) | > 0, finite |
| `drone.registration_number` | string | O | 기체 신고 번호 | — |
| `flight_plan.duration_hours` | float | O | 예정 비행 시간 | > 0 |
| `flight_plan.altitude_max_m` | float | O | 최대 비행 고도 (m AGL) | > 0 |
| `risk_factors.population_density` | float | O | 인구 밀도 (명/km2) | >= 0, finite |
| `risk_factors.flight_hours` | float | O | 비행 시간 | >= 0, finite |
| `risk_factors.weather_severity` | float | O | 기상 심각도 (0.0~1.0) | finite |
| `risk_factors.drone_mtow_kg` | float | O | 기체 중량 (kg) | > 0, finite |
| `risk_factors.operator_experience_hours` | float | O | 운용 경력 (시간) | >= 0, finite |
| `risk_factors.payload_hazard_level` | int | O | 탑재물 위험 등급 | 0~5 |
| `risk_factors.proximity_airports_km` | float | O | 공항 근접 거리 (km) | >= 0, finite |
| `coverage_tier_preference` | string | X | 희망 보장 등급 | BASIC/STANDARD/PREMIUM |

#### 자격증 종류 (license_type)

| 값 | 설명 | 근거 |
|---|---|---|
| `SUPER_LIGHT_1` | 1종 초경량비행장치 조종자 | 항공안전법 §125 |
| `SUPER_LIGHT_2` | 2종 초경량비행장치 조종자 | 항공안전법 §125 |
| `SUPER_LIGHT_3` | 3종 초경량비행장치 조종자 | 항공안전법 §125 |
| `SUPER_LIGHT_4` | 4종 초경량비행장치 조종자 | 항공안전법 §125 |
| `COMMERCIAL` | 사업용 무인비행장치 조종자 | 드론활용촉진법 §11 |

#### 응답 (Response) — 200 OK

```json
{
  "quote_id": "QT-2026-00001",
  "request_id": "uuid-v4",
  "risk_assessment": {
    "risk_score": 0.4562,
    "risk_grade": "MODERATE",
    "scoring_breakdown": {
      "population_density_component": 0.156,
      "weather_severity_component": 0.045,
      "weight_component": 0.0552,
      "experience_component": 0.075,
      "payload_component": 0.02,
      "airport_proximity_component": 0.0583,
      "flight_hours_component": 0.0467
    }
  },
  "recommended_tier": "STANDARD",
  "premium_krw": 116496,
  "coverage_limit_krw": 200000000,
  "tier_options": [
    {
      "tier": "BASIC",
      "premium_krw": 72810,
      "coverage_limit_krw": 50000000,
      "multiplier": 1.0
    },
    {
      "tier": "STANDARD",
      "premium_krw": 116496,
      "coverage_limit_krw": 200000000,
      "multiplier": 1.6
    },
    {
      "tier": "PREMIUM",
      "premium_krw": 174744,
      "coverage_limit_krw": 1000000000,
      "multiplier": 2.4
    }
  ],
  "quote_valid_until": "2026-06-25T09:00:00Z",
  "regulatory_compliance": {
    "aviation_business_act_70": true,
    "drone_promotion_act_15": true,
    "minimum_coverage_met": true
  }
}
```

---

### 3.2 POST /api/v1/insurance/bind — 보험 계약 체결

견적(Quote)을 수락하여 정식 보험 계약을 체결합니다.

#### 요청 (Request)

```json
{
  "quote_id": "QT-2026-00001",
  "operator_id": "OP-2026-001",
  "selected_tier": "STANDARD",
  "payment": {
    "method": "BANK_TRANSFER",
    "account_holder": "SDACS 운용자"
  },
  "policy_start_date": "2026-06-18T00:00:00Z",
  "policy_end_date": "2027-06-17T23:59:59Z",
  "additional_insured": []
}
```

#### 요청 필드 사양

| 필드 | 타입 | 필수 | 설명 |
|---|---|:-:|---|
| `quote_id` | string | O | 수락할 견적 ID |
| `operator_id` | string | O | 운용자 식별 번호 |
| `selected_tier` | string | O | 선택한 보장 등급 (BASIC/STANDARD/PREMIUM) |
| `payment.method` | string | O | 결제 수단 (BANK_TRANSFER / CARD / VIRTUAL_ACCOUNT) |
| `payment.account_holder` | string | O | 결제자 명의 |
| `policy_start_date` | string (ISO 8601) | O | 증권 시작일 |
| `policy_end_date` | string (ISO 8601) | O | 증권 종료일 |
| `additional_insured` | array | X | 추가 피보험자 목록 |

#### 응답 (Response) — 201 Created

```json
{
  "policy_id": "POL-2026-00001",
  "quote_id": "QT-2026-00001",
  "status": "ACTIVE",
  "tier": "STANDARD",
  "premium_krw": 116496,
  "coverage_limit_krw": 200000000,
  "policy_start_date": "2026-06-18T00:00:00Z",
  "policy_end_date": "2027-06-17T23:59:59Z",
  "policy_document_url": "https://{insurer-host}/policies/POL-2026-00001/document.pdf",
  "insurer": {
    "company_name": "한국드론보험(주)",
    "license_number": "보험업 제2026-001호"
  },
  "created_at": "2026-06-18T09:05:00Z"
}
```

---

### 3.3 GET /api/v1/insurance/policies/{policy_id} — 보험 증권 조회

발행된 보험 증권의 상세 정보를 조회합니다.

#### 요청

```
GET /api/v1/insurance/policies/POL-2026-00001
Authorization: Bearer {api_key}
```

#### 응답 (Response) — 200 OK

```json
{
  "policy_id": "POL-2026-00001",
  "status": "ACTIVE",
  "operator": {
    "operator_id": "OP-2026-001",
    "operator_name": "SDACS Test Operator"
  },
  "drone": {
    "drone_id": "DR-SWARM-001",
    "model": "DJI Matrice 350 RTK",
    "mtow_kg": 9.2,
    "registration_number": "KR-UD-2026-00123"
  },
  "coverage": {
    "tier": "STANDARD",
    "limit_krw": 200000000,
    "deductible_krw": 500000,
    "covers": [
      "THIRD_PARTY_LIABILITY",
      "PROPERTY_DAMAGE",
      "BODILY_INJURY",
      "DRONE_HULL_DAMAGE"
    ]
  },
  "premium": {
    "annual_krw": 116496,
    "payment_status": "PAID",
    "next_payment_date": null
  },
  "risk_assessment": {
    "risk_score": 0.4562,
    "risk_grade": "MODERATE"
  },
  "validity": {
    "start_date": "2026-06-18T00:00:00Z",
    "end_date": "2027-06-17T23:59:59Z",
    "is_valid": true
  },
  "claims_summary": {
    "total_claims": 0,
    "pending_claims": 0,
    "approved_claims": 0,
    "total_paid_krw": 0
  },
  "policy_document_url": "https://{insurer-host}/policies/POL-2026-00001/document.pdf"
}
```

#### 증권 상태 (status)

| 값 | 설명 |
|---|---|
| `ACTIVE` | 유효 — 보장 중 |
| `EXPIRED` | 만료 — 갱신 필요 |
| `CANCELLED` | 해지 — 보장 종료 |
| `SUSPENDED` | 정지 — 보험료 미납 등 |
| `PENDING` | 대기 — 심사 중 |

---

### 3.4 POST /api/v1/insurance/claims — 사고 보험금 청구

드론 사고 발생 시 보험금을 청구합니다. SDACS 시뮬레이션의 충돌 이벤트 데이터와 연동됩니다.

#### 요청 (Request)

```json
{
  "policy_id": "POL-2026-00001",
  "claim_type": "THIRD_PARTY_LIABILITY",
  "incident": {
    "incident_time": "2026-07-15T14:23:00Z",
    "location": {
      "lat": 37.5665,
      "lon": 126.9780,
      "altitude_m": 85.0
    },
    "description": "비행 중 돌풍으로 인한 비정상 착륙, 제3자 재산 피해 발생",
    "weather_conditions": {
      "wind_speed_ms": 12.5,
      "visibility_m": 8000,
      "precipitation": "NONE"
    },
    "sdacs_event_id": "EVT-2026-07-15-001",
    "collision_data": {
      "collision_type": "GROUND_IMPACT",
      "impact_speed_ms": 5.2,
      "drone_damage_level": "MODERATE"
    }
  },
  "claimed_amount_krw": 15000000,
  "evidence": [
    {
      "type": "FLIGHT_LOG",
      "url": "https://sdacs.example.com/logs/EVT-2026-07-15-001.json"
    },
    {
      "type": "SDACS_TELEMETRY",
      "url": "https://sdacs.example.com/telemetry/EVT-2026-07-15-001.csv"
    }
  ],
  "third_party": {
    "name": "피해자명",
    "contact": "010-0000-0000",
    "damage_description": "주차 차량 상부 파손"
  }
}
```

#### 요청 필드 사양

| 필드 | 타입 | 필수 | 설명 |
|---|---|:-:|---|
| `policy_id` | string | O | 보험 증권 ID |
| `claim_type` | string | O | 청구 유형 (아래 표 참조) |
| `incident.incident_time` | string (ISO 8601) | O | 사고 발생 시각 |
| `incident.location.lat` | float | O | 사고 위치 위도 |
| `incident.location.lon` | float | O | 사고 위치 경도 |
| `incident.location.altitude_m` | float | O | 사고 고도 (m AGL) |
| `incident.description` | string | O | 사고 상세 설명 |
| `incident.sdacs_event_id` | string | X | SDACS 이벤트 ID (자동 연동 시) |
| `incident.collision_data` | object | X | SDACS 충돌 데이터 |
| `claimed_amount_krw` | int | O | 청구 금액 (원) |
| `evidence` | array | O | 증빙 자료 목록 (최소 1건) |
| `third_party` | object | 조건부 | 제3자 피해 시 필수 |

#### 청구 유형 (claim_type)

| 값 | 설명 |
|---|---|
| `THIRD_PARTY_LIABILITY` | 제3자 배상 책임 |
| `PROPERTY_DAMAGE` | 재산 피해 |
| `BODILY_INJURY` | 인체 상해 |
| `DRONE_HULL_DAMAGE` | 기체 파손 (PREMIUM 등급만) |

#### 증빙 자료 유형 (evidence type)

| 값 | 설명 |
|---|---|
| `FLIGHT_LOG` | SDACS 비행 로그 (JSON) |
| `SDACS_TELEMETRY` | SDACS 텔레메트리 데이터 (CSV) |
| `PHOTO` | 사고 현장 사진 |
| `VIDEO` | 사고 현장 영상 |
| `POLICE_REPORT` | 경찰 사고 보고서 |
| `MEDICAL_REPORT` | 의료 진단서 (인체 상해 시) |

#### 응답 (Response) — 201 Created

```json
{
  "claim_id": "CLM-2026-00001",
  "policy_id": "POL-2026-00001",
  "status": "SUBMITTED",
  "claim_type": "THIRD_PARTY_LIABILITY",
  "claimed_amount_krw": 15000000,
  "submitted_at": "2026-07-15T15:00:00Z",
  "estimated_processing_days": 14,
  "adjuster_assigned": false
}
```

#### 청구 상태 (claim status)

| 값 | 설명 |
|---|---|
| `SUBMITTED` | 접수 완료 |
| `UNDER_REVIEW` | 심사 중 |
| `ADDITIONAL_INFO_REQUIRED` | 추가 자료 요청 |
| `APPROVED` | 승인 — 지급 예정 |
| `PARTIALLY_APPROVED` | 부분 승인 |
| `DENIED` | 거절 |
| `PAID` | 지급 완료 |

---

## 4. 리스크 점수 산출 공식

`InsuranceRiskCalculator.compute_risk_score()` 메서드에 구현된 가중 합산 모델을 정의합니다.

### 4.1 입력 정규화

각 리스크 팩터는 아래와 같이 0~최대값 범위로 정규화됩니다.

| 변수 | 정규화 공식 | 범위 |
|---|---|---|
| `pop` | `min(population_density / 10,000, 5.0)` | [0, 5.0] |
| `weather` | `clamp(weather_severity, 0.0, 1.0)` | [0, 1.0] |
| `weight` | `min(drone_mtow_kg / 25.0, 2.0)` | [0, 2.0] |
| `experience_bonus` | `max(0.0, 1.0 - operator_experience_hours / 500.0)` | [0, 1.0] |
| `payload` | `payload_hazard_level / 5.0` | [0, 1.0] |
| `airport` | `clamp(1.0 - proximity_airports_km / 30.0, 0.0, 1.0)` | [0, 1.0] |
| `hours` | `min(ln(1 + flight_hours) / 5.0, 1.0)` | [0, 1.0] |

> `experience_bonus`는 역비례 -- 경력이 많을수록 리스크가 낮아집니다.
> `airport`도 역비례 -- 공항에서 멀수록 리스크가 낮아집니다.

### 4.2 가중 합산

```
risk_score = 0.30 * pop
           + 0.15 * weather
           + 0.15 * weight
           + 0.15 * experience_bonus
           + 0.10 * payload
           + 0.10 * airport
           + 0.05 * hours
```

최종 점수는 `clamp(score, 0.0, 2.0)` 범위로 제한됩니다.

### 4.3 가중치 근거

| 팩터 | 가중치 | 근거 |
|---|:-:|---|
| 인구 밀도 | 30% | 제3자 피해 확률의 최대 결정 요인 |
| 기상 심각도 | 15% | 바람/강수 등 비행 안전 직접 영향 |
| 기체 중량 | 15% | 충돌 에너지 비례 — EASA 기준 참조 |
| 운용자 경력 | 15% | 사고율 역상관 — 보험 통계 기반 |
| 탑재물 위험도 | 10% | 위험물 운반 시 피해 확대 |
| 공항 근접도 | 10% | 유인기 충돌 위험 |
| 비행 시간 | 5% | 노출 시간 비례 리스크 |

### 4.4 등급 판정 기준

| 리스크 점수 | 추천 등급 | 보장 한도 |
|:-:|---|---|
| < 0.4 | BASIC | 5,000만원 |
| 0.4 ~ 0.9 미만 | STANDARD | 2억원 |
| >= 0.9 | PREMIUM | 10억원 |

### 4.5 보험료 산출

```
premium_krw = base_premium_krw * (1.0 + risk_score) * tier_multiplier
```

| 등급 | tier_multiplier |
|---|:-:|
| BASIC | 1.0 |
| STANDARD | 1.6 |
| PREMIUM | 2.4 |

> 기본 보험료(base_premium_krw)의 기본값은 50,000원입니다.

---

## 5. 한국 보험 규제 매핑

### 5.1 항공사업법 제70조 (보험 가입 의무)

항공사업법 제70조는 항공기를 사용하여 사업을 하는 자에 대해 배상책임보험의 가입을 의무화합니다.
드론 운용 시에도 이 의무가 적용되며, SDACS는 비행 전 보험 가입 여부를 자동으로 검증합니다.

| 의무 사항 | SDACS 구현 | API 필드 |
|---|---|---|
| 배상책임보험 가입 | 비행 전 보험 검증 게이트 | `policy.status == "ACTIVE"` |
| 최소 보장 금액 충족 | 등급별 한도 검증 | `coverage.limit_krw >= 최소요건` |
| 유효기간 내 비행 | 비행 계획 기간과 증권 기간 교차 검증 | `validity.start_date ~ end_date` |

### 5.2 드론활용촉진법 시행령 제15조 (배상보험 기준)

드론활용촉진법 시행령 제15조는 무인비행장치 사업자의 배상보험 가입 기준을 규정합니다.

| 기준 | 내용 | SDACS 매핑 |
|---|---|---|
| 대인 배상 | 사망 시 1억 5천만원 이상 | `STANDARD` 이상 등급 권장 |
| 대물 배상 | 재산 피해 시 실손 보상 | `claim_type: PROPERTY_DAMAGE` |
| 가입 시기 | 비행 개시 전 | Quote -> Bind -> 비행 승인 순서 강제 |
| 보험 증서 비치 | 운용 현장 보험증서 보유 | `policy_document_url` 접근 가능 |

### 5.3 보험업법 상 배상책임보험 요건

보험업법에 따른 배상책임보험의 일반 요건을 SDACS API가 충족하는 방식입니다.

| 요건 | 설명 | API 필드 매핑 |
|---|---|---|
| 보험자 적격 | 금융위 인가 보험사 | `insurer.license_number` |
| 피보험자 특정 | 운용자 및 기체 명시 | `operator_id`, `drone.registration_number` |
| 보험 목적 특정 | 배상 책임 범위 명시 | `coverage.covers[]` |
| 보험 기간 | 시작/종료일 명시 | `validity.start_date`, `validity.end_date` |
| 보험료 납입 | 납입 상태 확인 | `premium.payment_status` |
| 보험금 청구 절차 | 사고 통지 및 증빙 | POST `/claims` 엔드포인트 |

---

## 6. 규제-기능-API 매핑 종합표

| 규제 조항 | 규제 요건 | SDACS 기능 | API 엔드포인트 / 필드 |
|---|---|---|---|
| 항공사업법 §70 | 배상책임보험 가입 의무 | 비행 전 보험 검증 게이트 | GET `/policies/{id}` -> `status == "ACTIVE"` |
| 항공사업법 §70 | 최소 보장 금액 | 등급별 한도 검증 | `coverage.limit_krw` |
| 드론활용촉진법 시행령 §15 | 대인 배상 1.5억+ | STANDARD/PREMIUM 자동 추천 | `recommended_tier`, `coverage_limit_krw` |
| 드론활용촉진법 시행령 §15 | 비행 전 보험 가입 | Quote->Bind->Flight 워크플로우 | POST `/quote` -> POST `/bind` |
| 드론활용촉진법 시행령 §15 | 보험증서 비치 | 전자 증권 URL 제공 | `policy_document_url` |
| 보험업법 | 보험자 적격 확인 | 인가 보험사 정보 표시 | `insurer.license_number` |
| 보험업법 | 피보험자 특정 | 운용자/기체 정보 등록 | `operator`, `drone` 객체 |
| 보험업법 | 보험금 청구 절차 | 사고 보험금 청구 API | POST `/claims` |
| 항공안전법 §125 | 조종자 자격 | 자격증 정보 연동 | `operator.license_type`, `license_number` |
| SORA (EASA) | 리스크 기반 운용 승인 | 리스크 점수 산출 | `risk_assessment.risk_score`, `risk_grade` |

---

## 7. 통합 가이드

### 7.1 인증 및 연결

SDACS에서 보험사 API에 연결하기 위한 설정 항목입니다.

```yaml
# config/insurance_api.yaml
insurance:
  provider: "한국드론보험(주)"
  base_url: "https://api.drone-insurance.example.com/api/v1/insurance"
  api_key_env: "SDACS_INSURANCE_API_KEY"   # 환경 변수에서 읽음
  timeout_seconds: 30
  retry:
    max_attempts: 3
    backoff_seconds: [1, 2, 4]
  webhook:
    endpoint: "https://sdacs.example.com/webhooks/insurance"
    secret_env: "SDACS_WEBHOOK_SECRET"
    events:
      - "policy.activated"
      - "policy.expired"
      - "claim.status_changed"
      - "claim.paid"
```

> API 키와 Webhook Secret은 반드시 환경 변수로 관리합니다.
> 소스 코드에 하드코딩하지 않습니다.

### 7.2 Webhook 이벤트

보험사가 SDACS에 상태 변경을 실시간 통지하는 이벤트입니다.

| 이벤트 | 페이로드 | 용도 |
|---|---|---|
| `policy.activated` | `{ policy_id, status }` | 증권 활성화 확인 |
| `policy.expired` | `{ policy_id, expired_at }` | 갱신 알림 트리거 |
| `claim.status_changed` | `{ claim_id, old_status, new_status }` | 청구 진행 추적 |
| `claim.paid` | `{ claim_id, paid_amount_krw }` | 보험금 지급 확인 |

#### Webhook 검증

```
X-Webhook-Signature: HMAC-SHA256({webhook_secret}, {request_body})
```

SDACS는 수신 시 서명을 검증하여 위조 요청을 거부합니다.

### 7.3 SDACS 비행 전 보험 검증 워크플로우

```
1. 비행 계획 생성
   └─ FlightPathPlanner가 경로 확정

2. 리스크 팩터 수집
   └─ InsuranceRiskCalculator.compute_risk_score() 로컬 사전 평가
   └─ 인구 밀도, 기상, 기체 정보, 운용자 경력 자동 수집

3. 보험 견적 요청
   └─ POST /api/v1/insurance/quote
   └─ 보험사 리스크 점수와 로컬 점수 교차 검증

4. 보험 계약 체결 (최초 또는 갱신 시)
   └─ POST /api/v1/insurance/bind

5. 비행 전 보험 유효성 검증
   └─ GET /api/v1/insurance/policies/{policy_id}
   └─ status == "ACTIVE" 확인
   └─ coverage_limit_krw >= 법정 최소 금액 확인
   └─ 비행 계획 기간이 증권 유효 기간 내 확인

6. 비행 승인 / 거부
   └─ 보험 미가입 또는 만료 시 비행 차단

7. (사고 발생 시) 보험금 청구
   └─ POST /api/v1/insurance/claims
   └─ SDACS 텔레메트리 + 비행 로그 자동 첨부
```

### 7.4 기존 모듈 연동

| SDACS 모듈 | 보험 API 연동 지점 | 설명 |
|---|---|---|
| `simulation/insurance_risk.py` | 리스크 점수 로컬 계산 | 참조 구현 — API 견적과 교차 검증 |
| `src/airspace_control/planning/flight_path_planner.py` | 비행 계획 데이터 제공 | 경로/고도/운용 영역 정보 |
| `config/default_simulation.yaml` | 기본 파라미터 | 풍속/밀도 기본값 |
| `docs/certification/FLIGHT_PLAN_FORM.md` | 비행 계획 양식 | 보험 견적 입력 데이터 원본 |
| `docs/certification/ACCIDENT_REPORT_FORM.md` | 사고 보고 양식 | 보험금 청구 근거 자료 |

### 7.5 레이트 제한

| 엔드포인트 | 제한 | 윈도우 |
|---|:-:|---|
| POST `/quote` | 100회 | 분당 |
| POST `/bind` | 10회 | 분당 |
| GET `/policies/{id}` | 300회 | 분당 |
| POST `/claims` | 10회 | 분당 |

---

## 8. 부록

### 8.1 리스크 등급 (risk_grade)

| 점수 범위 | 등급 | 설명 |
|:-:|---|---|
| 0.0 ~ 0.2 미만 | LOW | 저위험 — 비도심, 경량 기체, 숙련 운용자 |
| 0.2 ~ 0.4 미만 | LOW_MODERATE | 저~중위험 |
| 0.4 ~ 0.6 미만 | MODERATE | 중위험 — 도심 인접, 표준 운용 |
| 0.6 ~ 0.9 미만 | HIGH | 고위험 — 고밀도 지역, 중량 기체 |
| 0.9 ~ 2.0 | CRITICAL | 극고위험 — 특별 심사 필요 |

### 8.2 보장 범위 상세 (covers)

| 보장 항목 | 설명 | BASIC | STANDARD | PREMIUM |
|---|---|:-:|:-:|:-:|
| `THIRD_PARTY_LIABILITY` | 제3자 배상 책임 | O | O | O |
| `PROPERTY_DAMAGE` | 재산 피해 보상 | O | O | O |
| `BODILY_INJURY` | 인체 상해 보상 | X | O | O |
| `DRONE_HULL_DAMAGE` | 기체 파손 보상 | X | X | O |

### 8.3 인증 및 보안 요건

| 항목 | 사양 |
|---|---|
| 인증 | Bearer Token (API Key) + HMAC-SHA256 Webhook 서명 |
| 전송 암호화 | TLS 1.3 필수 |
| 데이터 보존 | 견적 90일, 증권 10년 (보험업법 기록 보존 의무) |
| 개인정보 | 최소 수집 원칙, 비행 목적 외 사용 금지 |

### 8.4 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 1.0 | 2026-06-18 | SDACS 개발팀 | 최초 작성 (GENESIS Phase 308) |
