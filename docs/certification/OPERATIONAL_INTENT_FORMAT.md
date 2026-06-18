# 운영 의도(Operational Intent) 교환 포맷 사양 (ODYSSEY Phase 422)

*Created: 2026-06-18 · 근거: ASTM F3548-21 (USS Interoperability), ICAO UTM Framework, InterUSS DSS v1*
*용도: 다중 SDACS 인스턴스 간 4D 운영 의도 직렬화·교환을 위한 포맷 사양*
*선행: Phase 421 인스턴스 간 디스커버리 프로토콜 (`docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md`)*

---

## 면책 조항

본 문서는 **목포대학교 캡스톤 프로젝트 내부 개발 참고용**입니다.
실 UTM 운영에 직접 적용할 수 없으며, ASTM F3548-21 표준의 완전한 구현을 주장하지 않습니다.
Operational Intent 개념을 SDACS 시뮬레이션 환경에 적합하도록 **결정론적 모델**로 단순화한 것입니다.

---

## 1. 배경 및 동기

### 1.1 운영 의도란 무엇인가

운영 의도(Operational Intent)는 드론(또는 군집)이 **4D 공간(위도, 경도, 고도, 시간)**에서 운항할 영역을 선언하는 구조화된 데이터입니다. ASTM F3548-21에서는 USS(UAS Service Supplier)가 자신의 운영 의도를 DSS(Discovery and Synchronization Service)에 등록하고, 인접 USS가 이를 조회하여 충돌을 사전에 감지하는 메커니즘을 정의합니다.

### 1.2 Phase 421과의 관계

Phase 421은 인스턴스 간 **디스커버리·동기화·핸드오버** 프로토콜을 정의했습니다. 그 과정에서 `OperationalIntentRef`(OIR)와 `Volume4D` 데이터 클래스를 초안으로 도입했으나, 다음 항목이 미정의 상태입니다:

| 미정의 항목 | Phase 422 해결 범위 |
|---|---|
| 4D 볼륨의 GeoJSON 기반 정밀 경계 | 폴리곤·원형 지오펜스 지원 |
| WGS84 타원체 기준 고도 표현 | 절대 고도(MSL) + 상대 고도(AGL) 이중 표기 |
| ISO 8601 시간 표현 | 실 시각 + 시뮬레이션 시각 이중 표기 |
| 버퍼 마진(안전 여유) | 수평·수직·시간 방향 버퍼 |
| Operational Intent 상태 머신 전이 규칙 | 5-상태 전이 + 가드 조건 |
| 충돌 감지 알고리즘 상세 | 시간·공간 교차 검사 알고리즘 |
| 우선순위 협상 프로토콜 | Vickrey 경매 참조 (Phase 424 선행) |
| 메시지 유형 및 와이어 포맷 | CREATE/UPDATE/DELETE/NOTIFY/ACK |
| SDACS 모듈 통합 | `ws_bridge`, `AirspaceController` 연동 |

### 1.3 적용 시나리오

```
┌─────────────────────┐                    ┌─────────────────────┐
│   SDACS Instance A   │                    │   SDACS Instance B   │
│   (서울 북부 공역)    │                    │   (서울 남부 공역)    │
│                     │                    │                     │
│  Swarm-Alpha (10기) │   Operational      │  Swarm-Beta (8기)   │
│  고도 30-80m        │   Intent 교환      │  고도 50-100m       │
│  14:00-14:30        │◄──────────────────►│  14:15-14:45        │
│                     │                    │                     │
│  → 경계 인접 구간에서 고도·시간 중첩 감지  │                     │
│  → 우선순위 협상 후 Instance B가 양보     │                     │
└─────────────────────┘                    └─────────────────────┘
```

---

## 2. ASTM F3548-21 정렬

### 2.1 USS→USS Operational Intent 공유 모델

ASTM F3548-21 §5.3은 USS 간 운영 의도 공유를 다음과 같이 정의합니다:

1. **USS-A**가 DSS에 Operational Intent Reference(OIR)를 등록합니다.
2. **DSS**가 해당 4D 영역을 구독 중인 다른 USS에게 알림을 전송합니다.
3. **USS-B**가 OIR 상세 정보를 USS-A에게 직접 요청합니다 (peer-to-peer).
4. **USS-B**가 자체 의도와의 충돌 여부를 판단합니다.

```
USS-A                     DSS                      USS-B
  │                        │                         │
  │──PUT /oir/{id}────────►│                         │
  │                        │──NOTIFY (oir_id)───────►│
  │                        │                         │
  │◄──GET /oir/{id}/details──────────────────────────│
  │──200 (full intent)───────────────────────────── ►│
  │                        │                         │
  │                        │          USS-B: 충돌 판정 │
```

### 2.2 SDACS 적응

SDACS에서는 DSS 역할을 **Phase 421의 Raft 기반 Discovery Registry**가 대행합니다.
peer-to-peer 상세 조회 대신 **레지스트리가 전체 의도를 중계**하는 간소화 모델을 채택합니다.

| ASTM 원본 | SDACS 적응 | 근거 |
|---|---|---|
| DSS (클라우드 서비스) | Raft Discovery Registry (인프로세스) | 시뮬레이션 환경, 외부 의존성 제거 |
| OIR = 참조만 등록, 상세는 USS에 질의 | 전체 의도를 레지스트리에 등록 | 시뮬 지연 최소화, 단순화 |
| GeoJSON + WGS84 절대 고도 | GeoJSON + 이중 고도(WGS84 MSL / AGL) | 시뮬은 평면 좌표 병용 |
| OAuth2 인증 | mTLS + JWT (Phase 421 보안 계층 재사용) | 일관성 |
| 실시각(UTC) | ISO 8601 UTC + 시뮬레이션 시각 이중 표기 | 시뮬·실 환경 전환 지원 |

---

## 3. 4D 볼륨 정의

### 3.1 지리적 경계 (Geographic Boundary)

4D 볼륨의 수평 경계는 **GeoJSON Polygon** 또는 **원형(Circle)** 두 가지 형태를 지원합니다.

#### 3.1.1 폴리곤 경계

GeoJSON RFC 7946 규격을 따릅니다. 좌표는 `[경도, 위도]` 순서입니다.

```json
{
  "type": "Polygon",
  "coordinates": [
    [
      [126.90, 37.50],
      [126.95, 37.50],
      [126.95, 37.55],
      [126.90, 37.55],
      [126.90, 37.50]
    ]
  ]
}
```

**제약 조건:**
- 외부 링(exterior ring)만 지원합니다 (홀 미지원).
- 꼭짓점 수: 최소 4개 (폐합 포함), 최대 100개.
- 자기 교차(self-intersection) 금지.
- 반시계 방향(CCW) 정렬 권장.

#### 3.1.2 원형 경계

중심 좌표와 반지름으로 정의합니다.

```json
{
  "type": "Circle",
  "center": [126.925, 37.525],
  "radius_m": 500.0
}
```

**제약 조건:**
- `radius_m`: 미터 단위, 최소 10m, 최대 50,000m.
- 구현 시 정다각형(32변)으로 근사하여 폴리곤 연산과 통합합니다.

### 3.2 고도 범위 (Altitude Range)

```json
{
  "altitude_lower": {
    "value_m": 30.0,
    "reference": "W84",
    "units": "M"
  },
  "altitude_upper": {
    "value_m": 120.0,
    "reference": "W84",
    "units": "M"
  }
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `value_m` | float | 미터 단위 고도 값 |
| `reference` | string | `"W84"` (WGS84 타원체), `"AGL"` (지면 기준), `"MSL"` (평균 해수면) |
| `units` | string | `"M"` (미터) 고정 |

**SDACS 시뮬레이션 환경에서의 처리:**
- 시뮬레이션 내부는 `"AGL"` 기준(평면 좌표계 z축)으로 동작합니다.
- 외부 교환 시에는 `"W84"` 기준으로 변환합니다.
- 변환 로직은 `src/airspace_control/utils/coordinate_systems.py`를 활용합니다.

### 3.3 시간 창 (Time Window)

```json
{
  "time_start": {
    "value": "2026-06-18T05:00:00Z",
    "format": "RFC3339"
  },
  "time_end": {
    "value": "2026-06-18T05:30:00Z",
    "format": "RFC3339"
  },
  "sim_time_start": 0.0,
  "sim_time_end": 1800.0
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `time_start` / `time_end` | object | ISO 8601 / RFC 3339 UTC 시각 |
| `sim_time_start` / `sim_time_end` | float | 시뮬레이션 시각 (초 단위, SimPy `env.now` 기준) |

**이중 표기 규칙:**
- 실 UTM 운영 모드에서는 RFC 3339 시각이 권위적(authoritative)입니다.
- 시뮬레이션 모드에서는 `sim_time_*` 이 권위적이며, RFC 3339 시각은 참고용입니다.
- 모드 판별은 메시지 엔벨로프의 `context.mode` 필드로 수행합니다.

### 3.4 버퍼 마진 (Buffer Margins)

안전 여유를 확보하기 위해 볼륨 외곽에 버퍼를 추가합니다.

```json
{
  "lateral_buffer_m": 50.0,
  "vertical_buffer_m": 15.0,
  "temporal_buffer_s": 30.0
}
```

| 필드 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `lateral_buffer_m` | float | 50.0 | 수평 방향 버퍼 (미터) |
| `vertical_buffer_m` | float | 15.0 | 수직 방향 버퍼 (미터) |
| `temporal_buffer_s` | float | 30.0 | 시간 방향 버퍼 (초) |

**적용 규칙:**
- 충돌 감지 시 볼륨을 버퍼만큼 **확장**하여 검사합니다.
- 버퍼는 운영 의도 소유자가 설정하며, 최소값은 시스템 설정(`config/federation.yaml`)으로 강제합니다.
- 강풍 조건(풍속 >10 m/s)에서는 `lateral_buffer_m`을 1.5배로 자동 확대합니다 (APF 강풍 모드 연동).

---

## 4. JSON Schema: OperationalIntent

### 4.1 최상위 구조

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sdacs.mokpo.ac.kr/schemas/operational-intent/v0.1.0",
  "title": "SDACS Operational Intent",
  "description": "ASTM F3548-21 기반 4D 운영 의도 교환 포맷",
  "type": "object",
  "required": [
    "id", "state", "priority", "volumes", "operator_id",
    "uss_id", "aircraft_type", "created_at", "updated_at"
  ],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "UUID v4 — 운영 의도 고유 식별자"
    },
    "state": {
      "type": "string",
      "enum": ["Accepted", "Activated", "Nonconforming", "Contingent", "Ended"],
      "description": "운영 의도 현재 상태 (§5 상태 머신 참조)"
    },
    "priority": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "우선순위 (0=최고, 100=최저). 충돌 해소 시 사용"
    },
    "volumes": {
      "type": "array",
      "minItems": 1,
      "maxItems": 50,
      "items": { "$ref": "#/$defs/Volume4D" },
      "description": "정상 운항 시 점유할 4D 볼륨 배열"
    },
    "off_nominal_volumes": {
      "type": "array",
      "maxItems": 20,
      "items": { "$ref": "#/$defs/Volume4D" },
      "default": [],
      "description": "비정상(contingency) 시 사용할 확장 볼륨 배열"
    },
    "operator_id": {
      "type": "string",
      "description": "운영자 식별자 (기관·회사 ID)"
    },
    "uss_id": {
      "type": "string",
      "description": "발행 USS(SDACS 인스턴스) 식별자"
    },
    "aircraft_type": {
      "$ref": "#/$defs/AircraftType",
      "description": "항공기 유형 및 군집 정보"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "생성 시각 (RFC 3339 UTC)"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "최종 갱신 시각 (RFC 3339 UTC)"
    },
    "sim_created_at": {
      "type": "number",
      "description": "생성 시뮬레이션 시각 (초)"
    },
    "sim_updated_at": {
      "type": "number",
      "description": "최종 갱신 시뮬레이션 시각 (초)"
    }
  }
}
```

### 4.2 Volume4D 정의

```json
{
  "$defs": {
    "Volume4D": {
      "type": "object",
      "required": ["geography", "altitude_lower", "altitude_upper", "time_start", "time_end"],
      "properties": {
        "geography": {
          "oneOf": [
            { "$ref": "#/$defs/GeoPolygon" },
            { "$ref": "#/$defs/GeoCircle" }
          ],
          "description": "수평 경계 (GeoJSON Polygon 또는 Circle)"
        },
        "altitude_lower": { "$ref": "#/$defs/Altitude" },
        "altitude_upper": { "$ref": "#/$defs/Altitude" },
        "time_start": { "$ref": "#/$defs/TimeSpec" },
        "time_end": { "$ref": "#/$defs/TimeSpec" },
        "buffer": { "$ref": "#/$defs/BufferMargin" }
      }
    },
    "GeoPolygon": {
      "type": "object",
      "required": ["type", "coordinates"],
      "properties": {
        "type": { "const": "Polygon" },
        "coordinates": {
          "type": "array",
          "items": {
            "type": "array",
            "items": {
              "type": "array",
              "items": { "type": "number" },
              "minItems": 2,
              "maxItems": 2
            },
            "minItems": 4,
            "maxItems": 100
          },
          "minItems": 1,
          "maxItems": 1
        }
      }
    },
    "GeoCircle": {
      "type": "object",
      "required": ["type", "center", "radius_m"],
      "properties": {
        "type": { "const": "Circle" },
        "center": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 2,
          "maxItems": 2,
          "description": "[경도, 위도]"
        },
        "radius_m": {
          "type": "number",
          "minimum": 10,
          "maximum": 50000
        }
      }
    },
    "Altitude": {
      "type": "object",
      "required": ["value_m", "reference"],
      "properties": {
        "value_m": { "type": "number" },
        "reference": {
          "type": "string",
          "enum": ["W84", "AGL", "MSL"]
        },
        "units": {
          "type": "string",
          "const": "M",
          "default": "M"
        }
      }
    },
    "TimeSpec": {
      "type": "object",
      "required": ["value"],
      "properties": {
        "value": {
          "type": "string",
          "format": "date-time",
          "description": "RFC 3339 UTC 시각"
        },
        "sim_time": {
          "type": "number",
          "description": "시뮬레이션 시각 (초, SimPy env.now 기준)"
        }
      }
    },
    "BufferMargin": {
      "type": "object",
      "properties": {
        "lateral_buffer_m": {
          "type": "number",
          "minimum": 0,
          "default": 50.0
        },
        "vertical_buffer_m": {
          "type": "number",
          "minimum": 0,
          "default": 15.0
        },
        "temporal_buffer_s": {
          "type": "number",
          "minimum": 0,
          "default": 30.0
        }
      }
    },
    "AircraftType": {
      "type": "object",
      "required": ["category"],
      "properties": {
        "category": {
          "type": "string",
          "enum": ["SINGLE_UA", "SWARM"],
          "description": "단일 드론 또는 군집"
        },
        "swarm_count": {
          "type": "integer",
          "minimum": 1,
          "default": 1,
          "description": "군집 드론 수 (SINGLE_UA인 경우 1)"
        },
        "drone_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "해당 의도에 포함된 드론 ID 목록"
        },
        "profile": {
          "type": "string",
          "description": "드론 프로파일 이름 (drone_profiles.py 참조)"
        }
      }
    }
  }
}
```

### 4.3 상태(state) 필드 값 정의

| 값 | ASTM 대응 | 설명 |
|---|---|---|
| `Accepted` | Accepted | 의도가 등록되었으나 아직 비행이 시작되지 않은 상태 |
| `Activated` | Activated | 비행이 진행 중이며 정상 운항 중인 상태 |
| `Nonconforming` | Nonconforming | 드론이 선언된 볼륨을 이탈했으나 off_nominal_volumes 내에 있는 상태 |
| `Contingent` | Contingent | 비상 상황 발생. off_nominal_volumes도 이탈했거나 비상 절차 진행 중 |
| `Ended` | Ended | 비행 종료 또는 의도 철회 완료 |

### 4.4 우선순위(priority) 범위 가이드

| 범위 | 분류 | 예시 |
|---|---|---|
| 0-10 | 긴급 (Emergency) | 배터리 고갈 복귀, 의료 긴급 배송 |
| 11-30 | 높음 (High) | 재난 대응, 수색·구조 임무 |
| 31-60 | 보통 (Normal) | 일반 배송, 측량, 촬영 |
| 61-80 | 낮음 (Low) | 훈련 비행, 레저 비행 |
| 81-100 | 최저 (Lowest) | 테스트 비행, 시뮬레이션 전용 |

**Phase 421 호환성 참고:**
Phase 421의 `OperationalIntentRef.priority`는 1(최고)~5(최저) 범위였습니다. 본 사양의 0-100 범위로 매핑 시: `Phase421_priority = ceil(Phase422_priority / 20)` (예: 0-20→1, 21-40→2, ..., 81-100→5).

---

## 5. 상태 머신

### 5.1 상태 전이 다이어그램

```
                    CREATE
                      │
                      ▼
               ┌──────────┐
               │ Accepted │
               └─────┬────┘
                     │ ACTIVATE (비행 시작)
                     ▼
               ┌──────────┐
        ┌─────►│ Activated│◄─────────────┐
        │      └─────┬────┘              │
        │            │                   │
        │     볼륨 이탈 감지        정상 복귀
        │            │              (CONFORM)
        │            ▼                   │
        │   ┌──────────────┐             │
        │   │Nonconforming │─────────────┘
        │   └──────┬───────┘
        │          │ off_nominal_volumes도 이탈
        │          │ 또는 비상 선언
        │          ▼
        │   ┌──────────┐
        │   │Contingent│
        │   └─────┬────┘
        │         │
        │         │ 비상 해소 + 볼륨 내 복귀
        │         │ (REACTIVATE)
        └─────────┘
                     │
            ─────────┴──────────
           │                    │
     정상 종료              비상 착륙/철회
     (END)                  (END)
           │                    │
           ▼                    ▼
        ┌────────────────────────┐
        │        Ended           │
        └────────────────────────┘
```

### 5.2 상태 전이 규칙

| 현재 상태 | 이벤트 | 다음 상태 | 가드 조건 |
|---|---|---|---|
| (없음) | CREATE | Accepted | 볼륨 유효성 검증 통과, 충돌 검사 완료 |
| Accepted | ACTIVATE | Activated | 비행 시작 시점 도래, 드론 이륙 확인 |
| Accepted | CANCEL | Ended | 운영자 취소 요청 |
| Activated | DEVIATE | Nonconforming | 드론 위치가 `volumes[]` 바깥이나 `off_nominal_volumes[]` 안에 있음 |
| Activated | END | Ended | 비행 정상 종료, 모든 드론 착륙 완료 |
| Nonconforming | CONFORM | Activated | 드론이 `volumes[]` 내로 복귀 (10초 이내) |
| Nonconforming | ESCALATE | Contingent | 30초 이상 `volumes[]` 외부이거나, `off_nominal_volumes[]`도 이탈 |
| Contingent | REACTIVATE | Activated | 비상 해소 + 드론이 `volumes[]` 내 복귀 + ATC 승인 |
| Contingent | END | Ended | 비상 착륙 완료 또는 의도 강제 철회 |

### 5.3 타임아웃 규칙

| 상태 | 최대 체류 시간 | 초과 시 동작 |
|---|---|---|
| Accepted | `volumes[0].time_start` + 120초 | 자동 `Ended` 전이 (비행 미시작) |
| Nonconforming | 30초 | 자동 `Contingent` 전이 |
| Contingent | 120초 | ATC에 수동 개입 요청, 로그 기록 |

---

## 6. 충돌 감지: 볼륨 겹침 알고리즘

### 6.1 개요

두 Operational Intent의 볼륨이 **시간·공간 모두에서 교차**할 때 충돌(conflict)로 판정합니다. Phase 421에서 정의한 AABB 겹침 검사를 **GeoJSON 폴리곤 지원**으로 확장합니다.

### 6.2 충돌 감지 절차

```
입력: Intent_A.volumes[], Intent_B.volumes[]
출력: 겹침 여부 (bool) + 겹침 볼륨 (optional)

1단계: 시간 교차 검사 (O(1))
  ┌─ A.time_start <= B.time_end + B.temporal_buffer
  └─ A.time_end   >= B.time_start - A.temporal_buffer
  → false이면 겹침 없음 (fast reject)

2단계: 고도 교차 검사 (O(1))
  ┌─ A.alt_lower - A.vertical_buffer <= B.alt_upper + B.vertical_buffer
  └─ A.alt_upper + A.vertical_buffer >= B.alt_lower - B.vertical_buffer
  → false이면 겹침 없음 (fast reject)

3단계: 수평 교차 검사
  3a. 바운딩 박스 사전 검사 (O(1))
      양쪽 폴리곤의 AABB가 겹치지 않으면 fast reject
  3b. 정밀 폴리곤 교차 검사
      Sutherland-Hodgman 알고리즘 또는 Shapely intersection
      → 교차 면적 > 0 이면 겹침

4단계: 겹침 볼륨 산출
  - 수평: 교차 폴리곤
  - 고도: max(A.lower, B.lower) ~ min(A.upper, B.upper)
  - 시간: max(A.start, B.start) ~ min(A.end, B.end)
```

### 6.3 SDACS 구현 매핑

```python
def check_intent_conflict(
    intent_a: OperationalIntent,
    intent_b: OperationalIntent,
) -> ConflictResult | None:
    """두 운영 의도 간 4D 볼륨 충돌을 검사합니다.

    Phase 421의 volumes_overlap()을 확장하여 GeoJSON 폴리곤과
    버퍼 마진을 지원합니다.

    Returns
    -------
    ConflictResult | None
        겹침이 있으면 ConflictResult, 없으면 None.
    """
    for vol_a in intent_a.volumes:
        for vol_b in intent_b.volumes:
            # 1단계: 시간 교차
            buf_a = vol_a.buffer.temporal_buffer_s
            buf_b = vol_b.buffer.temporal_buffer_s
            if vol_a.time_end_sim + buf_a < vol_b.time_start_sim - buf_b:
                continue
            if vol_a.time_start_sim - buf_a > vol_b.time_end_sim + buf_b:
                continue

            # 2단계: 고도 교차
            if not _altitude_overlaps(vol_a, vol_b):
                continue

            # 3단계: 수평 교차
            overlap_poly = _geographic_intersection(vol_a, vol_b)
            if overlap_poly is None:
                continue

            return ConflictResult(
                intent_a_id=intent_a.id,
                intent_b_id=intent_b.id,
                overlap_volume=_build_overlap_volume(
                    overlap_poly, vol_a, vol_b
                ),
            )
    return None
```

### 6.4 복잡도 분석

| 단계 | 복잡도 | 비고 |
|---|---|---|
| 시간·고도 교차 | O(1) | 범위 비교 |
| AABB 사전 검사 | O(1) | 바운딩 박스 캐싱 |
| 폴리곤 교차 | O(n*m) | n, m = 각 폴리곤의 꼭짓점 수 (최대 100) |
| 전체 (의도 쌍) | O(V_a * V_b * n * m) | V = 볼륨 배열 크기 (최대 50) |

**최적화 전략:**
- 시간·고도 fast reject로 대부분의 비교를 O(1)에서 종료합니다.
- 볼륨 배열이 큰 경우 시간 순 정렬 후 이분 탐색으로 후보를 줄입니다.
- `simulation/spatial_hash.py`의 `SpatialHash`를 활용하여 공간 인덱싱을 적용합니다.

---

## 7. 우선순위 협상

### 7.1 기본 규칙

두 Operational Intent가 충돌할 때, 다음 우선순위로 해소합니다:

1. **상태 우선**: `Contingent` > `Nonconforming` > `Activated` > `Accepted`
2. **숫자 우선순위**: `priority` 값이 낮은 쪽이 우선 (0이 최고)
3. **선착순**: 동일 우선순위 시 `created_at`이 이른 쪽이 우선

### 7.2 Vickrey 경매 기반 협상 (Phase 424 선행 정의)

기본 규칙으로 해소되지 않는 경우(동일 우선순위 + 동시 생성), **2차 가격 경매(Vickrey Auction)** 메커니즘을 적용합니다.

```
Instance A                  Registry                  Instance B
    │                          │                          │
    │  CONFLICT_NOTIFY         │  CONFLICT_NOTIFY         │
    │◄─────────────────────────│─────────────────────────►│
    │                          │                          │
    │  BID(value=V_a)          │  BID(value=V_b)          │
    │─────────────────────────►│◄─────────────────────────│
    │                          │                          │
    │           [Registry: 최고 입찰자 = A, 지불 = V_b]     │
    │                          │                          │
    │  AUCTION_RESULT          │  AUCTION_RESULT          │
    │  (winner=A, cost=V_b)    │  (loser=B, yield=true)   │
    │◄─────────────────────────│─────────────────────────►│
```

**Vickrey 경매 규칙:**
- 각 인스턴스는 해당 볼륨의 **가치(bid value)**를 비공개 입찰합니다.
- 가치는 미션 긴급도·배터리 잔량·우회 비용 등의 가중 합으로 산출합니다.
- 최고 입찰자가 공역을 확보하되, 지불 가격은 **2위 입찰가**입니다 (진실 보고 유인).
- 패배한 인스턴스는 `off_nominal_volumes`로 우회하거나 시간대를 이동합니다.
- 입찰 마감: `CONFLICT_NOTIFY` 수신 후 5초 (시뮬 시간).

**입찰 가치 산출 공식 (후보):**

```
bid_value = w_urgency * mission_urgency
          + w_battery * (1 - battery_remaining)
          + w_detour  * detour_cost_estimate
          + w_swarm   * swarm_size_factor
```

| 가중치 | 기본값 | 설명 |
|---|---|---|
| `w_urgency` | 0.4 | 미션 긴급도 (0-1) |
| `w_battery` | 0.2 | 배터리 소모율 반영 |
| `w_detour` | 0.3 | 우회 시 추가 거리·시간 비용 |
| `w_swarm` | 0.1 | 군집 규모 (대규모일수록 우회 어려움) |

### 7.3 충돌 해소 전략

Phase 421에서 정의한 4가지 전략을 본 사양에서 구체화합니다:

| 전략 | 적용 조건 | 동작 |
|---|---|---|
| `PRIORITY_YIELD` | 우선순위 차이 >= 20 | 낮은 우선순위 인스턴스가 즉시 양보 |
| `TEMPORAL_SHIFT` | 시간 겹침만 존재 | 후순위 의도의 시간 창을 이동 |
| `ALTITUDE_SPLIT` | 수직 여유 >= 30m | 고도대를 분리하여 동시 운항 허용 |
| `VICKREY_AUCTION` | 기본 규칙 미결정 | Vickrey 경매로 최종 결정 |

---

## 8. 메시지 유형

### 8.1 공통 엔벨로프

Phase 421의 `sdacs-discovery` 프로토콜 위에 `sdacs-intent` 프로토콜을 정의합니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "CREATE | UPDATE | DELETE | NOTIFY | ACK",
  "msg_id": "uuid-v4",
  "timestamp": "2026-06-18T05:00:00Z",
  "sim_timestamp": 0.0,
  "sender_id": "sdacs-instance-001",
  "context": {
    "mode": "SIMULATION",
    "auth_mode": "SIMULATED"
  },
  "payload": { }
}
```

### 8.2 CREATE — 운영 의도 생성

인스턴스가 새로운 Operational Intent를 레지스트리에 등록합니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "CREATE",
  "msg_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-06-18T05:00:00Z",
  "sim_timestamp": 0.0,
  "sender_id": "sdacs-seoul-01",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "intent": {
      "id": "intent-uuid-001",
      "state": "Accepted",
      "priority": 35,
      "volumes": [
        {
          "geography": {
            "type": "Polygon",
            "coordinates": [
              [
                [126.90, 37.50],
                [126.95, 37.50],
                [126.95, 37.55],
                [126.90, 37.55],
                [126.90, 37.50]
              ]
            ]
          },
          "altitude_lower": { "value_m": 30.0, "reference": "W84" },
          "altitude_upper": { "value_m": 120.0, "reference": "W84" },
          "time_start": {
            "value": "2026-06-18T05:00:00Z",
            "sim_time": 0.0
          },
          "time_end": {
            "value": "2026-06-18T05:30:00Z",
            "sim_time": 1800.0
          },
          "buffer": {
            "lateral_buffer_m": 50.0,
            "vertical_buffer_m": 15.0,
            "temporal_buffer_s": 30.0
          }
        }
      ],
      "off_nominal_volumes": [
        {
          "geography": {
            "type": "Circle",
            "center": [126.925, 37.525],
            "radius_m": 1000.0
          },
          "altitude_lower": { "value_m": 0.0, "reference": "W84" },
          "altitude_upper": { "value_m": 150.0, "reference": "W84" },
          "time_start": {
            "value": "2026-06-18T05:00:00Z",
            "sim_time": 0.0
          },
          "time_end": {
            "value": "2026-06-18T05:45:00Z",
            "sim_time": 2700.0
          },
          "buffer": {
            "lateral_buffer_m": 100.0,
            "vertical_buffer_m": 30.0,
            "temporal_buffer_s": 60.0
          }
        }
      ],
      "operator_id": "OP-MOKPO-UAV-001",
      "uss_id": "sdacs-seoul-01",
      "aircraft_type": {
        "category": "SWARM",
        "swarm_count": 10,
        "drone_ids": [
          "DR-001", "DR-002", "DR-003", "DR-004", "DR-005",
          "DR-006", "DR-007", "DR-008", "DR-009", "DR-010"
        ],
        "profile": "delivery_standard"
      },
      "created_at": "2026-06-18T05:00:00Z",
      "updated_at": "2026-06-18T05:00:00Z",
      "sim_created_at": 0.0,
      "sim_updated_at": 0.0
    }
  }
}
```

### 8.3 UPDATE — 운영 의도 갱신

기존 의도의 상태·볼륨·우선순위를 변경합니다. `intent.id`로 대상을 식별합니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "UPDATE",
  "msg_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
  "timestamp": "2026-06-18T05:01:00Z",
  "sim_timestamp": 60.0,
  "sender_id": "sdacs-seoul-01",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "intent_id": "intent-uuid-001",
    "updates": {
      "state": "Activated",
      "updated_at": "2026-06-18T05:01:00Z",
      "sim_updated_at": 60.0
    },
    "reason": "비행 시작 — 10기 이륙 완료"
  }
}
```

### 8.4 DELETE — 운영 의도 삭제

의도를 철회합니다. 상태를 `Ended`로 전이한 후 레지스트리에서 비활성화합니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "DELETE",
  "msg_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
  "timestamp": "2026-06-18T05:28:00Z",
  "sim_timestamp": 1680.0,
  "sender_id": "sdacs-seoul-01",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "intent_id": "intent-uuid-001",
    "reason": "미션 완료 — 10기 전원 착륙"
  }
}
```

### 8.5 NOTIFY — 변경 통보

레지스트리가 구독 중인 인스턴스에게 의도 변경을 통보합니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "NOTIFY",
  "msg_id": "d4e5f6a7-b8c9-0123-defa-456789012345",
  "timestamp": "2026-06-18T05:01:01Z",
  "sim_timestamp": 60.1,
  "sender_id": "registry-leader",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "event_type": "INTENT_ACTIVATED",
    "intent_id": "intent-uuid-001",
    "uss_id": "sdacs-seoul-01",
    "affected_volume_summary": {
      "lat_range": [37.50, 37.55],
      "lon_range": [126.90, 126.95],
      "alt_range_m": [30.0, 120.0],
      "time_range": ["2026-06-18T05:00:00Z", "2026-06-18T05:30:00Z"]
    },
    "conflict_detected": false,
    "subscribers_notified": ["sdacs-busan-01", "sdacs-incheon-01"]
  }
}
```

**event_type 값:**

| 값 | 설명 |
|---|---|
| `INTENT_CREATED` | 새 의도 등록 |
| `INTENT_ACTIVATED` | 의도 활성화 (비행 시작) |
| `INTENT_UPDATED` | 볼륨·우선순위 변경 |
| `INTENT_NONCONFORMING` | 볼륨 이탈 감지 |
| `INTENT_CONTINGENT` | 비상 상태 전이 |
| `INTENT_ENDED` | 의도 종료 |
| `INTENT_DELETED` | 의도 삭제 |
| `CONFLICT_DETECTED` | 충돌 감지 (§6 알고리즘 결과) |

### 8.6 ACK — 수신 확인

모든 메시지에 대한 수신 확인 응답입니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "ACK",
  "msg_id": "e5f6a7b8-c9d0-1234-efab-567890123456",
  "timestamp": "2026-06-18T05:01:02Z",
  "sim_timestamp": 60.2,
  "sender_id": "sdacs-busan-01",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "ack_msg_id": "d4e5f6a7-b8c9-0123-defa-456789012345",
    "status": "RECEIVED",
    "processing_result": "OK"
  }
}
```

| `status` 값 | 설명 |
|---|---|
| `RECEIVED` | 메시지 수신 완료 |
| `ACCEPTED` | 처리 성공 |
| `REJECTED` | 처리 거부 (사유: `error` 필드) |
| `ERROR` | 처리 중 오류 발생 |

---

## 9. 와이어 포맷

### 9.1 전송 프로토콜

| 계층 | 프로토콜 | 설명 |
|---|---|---|
| 애플리케이션 | JSON (UTF-8) | 본 문서의 메시지 포맷 |
| 전송 | HTTPS/1.1 또는 WebSocket (WSS) | Phase 421 `ws_bridge` 재사용 |
| 보안 | mTLS (mutual TLS 1.3) | Phase 421 §6 보안 계층 |
| 인증 | JWT Bearer Token (RS256) | Phase 421 §6.2 JWT 구조 |

### 9.2 REST 엔드포인트 (HTTPS 모드)

| 메서드 | 경로 | 메시지 유형 | 설명 |
|---|---|---|---|
| POST | `/api/v1/intents` | CREATE | 운영 의도 생성 |
| PUT | `/api/v1/intents/{id}` | UPDATE | 운영 의도 갱신 |
| DELETE | `/api/v1/intents/{id}` | DELETE | 운영 의도 삭제 |
| GET | `/api/v1/intents/{id}` | - | 운영 의도 상세 조회 |
| POST | `/api/v1/intents/query` | - | 4D 볼륨 기반 의도 검색 |

### 9.3 WebSocket 모드

Phase 421의 `ws_bridge`를 확장하여 `sdacs-intent` 프로토콜 메시지를 전송합니다. NOTIFY 및 ACK는 WebSocket 푸시로 전달됩니다.

```
ws://localhost:8765 (시뮬레이션)
wss://sdacs.example.com:8765 (운영)
```

### 9.4 메시지 크기 제한

| 항목 | 제한 |
|---|---|
| 단일 메시지 최대 크기 | 256 KB |
| `volumes[]` 최대 항목 수 | 50 |
| `off_nominal_volumes[]` 최대 항목 수 | 20 |
| 폴리곤 최대 꼭짓점 수 | 100 |
| `drone_ids[]` 최대 항목 수 | 500 |

### 9.5 시뮬레이션 환경 간소화

Phase 421 §6.3과 동일하게 `auth_mode`에 따라 보안을 전환합니다:

- `"SIMULATED"`: 서명 생략, `sender_id` 기반 검증만 수행합니다.
- `"STRICT"`: mTLS + JWT 전체 적용합니다.

---

## 10. 예제 시나리오

### 10.1 시나리오 A: 정상 운항 — 충돌 없음

서울 북부(Instance A)에서 10기 군집이 배송 임무를 수행합니다. 인접한 서울 남부(Instance B)와 공역이 겹치지 않습니다.

**순서:**

```
Instance A                     Registry                     Instance B
    │                             │                             │
    │  CREATE (intent-001)        │                             │
    │  state=Accepted, pri=35     │                             │
    │  alt: 30-80m, 14:00-14:30   │                             │
    │────────────────────────────►│                             │
    │                             │  NOTIFY (INTENT_CREATED)    │
    │                             │────────────────────────────►│
    │                             │                             │
    │                             │◄──────ACK (RECEIVED)────────│
    │◄──────ACK (ACCEPTED)────────│                             │
    │                             │                             │
    │  UPDATE (state=Activated)   │                             │
    │────────────────────────────►│                             │
    │                             │  NOTIFY (INTENT_ACTIVATED)  │
    │                             │────────────────────────────►│
    │                             │                             │
    │  ... (정상 비행 30분) ...    │                             │
    │                             │                             │
    │  DELETE (미션 완료)          │                             │
    │────────────────────────────►│                             │
    │                             │  NOTIFY (INTENT_ENDED)      │
    │                             │────────────────────────────►│
```

### 10.2 시나리오 B: 볼륨 중첩 — 우선순위 양보

Instance A(배송, priority=35)와 Instance B(재난 대응, priority=15)의 고도·시간이 겹칩니다.

**충돌 감지 및 해소:**

```
Instance A                     Registry                     Instance B
    │                             │                             │
    │  CREATE (intent-001)        │                             │
    │  pri=35, alt: 30-120m       │                             │
    │────────────────────────────►│                             │
    │◄──────ACK (ACCEPTED)────────│                             │
    │                             │                             │
    │                             │  CREATE (intent-002)        │
    │                             │  pri=15, alt: 50-100m       │
    │                             │◄────────────────────────────│
    │                             │                             │
    │                             │ [충돌 감지: 고도 50-100m 겹침] │
    │                             │                             │
    │  NOTIFY (CONFLICT_DETECTED) │  NOTIFY (CONFLICT_DETECTED) │
    │  resolution=PRIORITY_YIELD  │  resolution=PRIORITY_YIELD  │
    │◄────────────────────────────│────────────────────────────►│
    │                             │                             │
    │  [pri 차이 = 20 → A가 양보] │                             │
    │                             │                             │
    │  UPDATE (intent-001)        │                             │
    │  alt: 30-45m (고도 하향)    │                             │
    │────────────────────────────►│                             │
    │                             │  NOTIFY (INTENT_UPDATED)    │
    │                             │────────────────────────────►│
    │                             │                             │
    │                             │  ACK (ACCEPTED)             │
    │                             │◄────────────────────────────│
```

### 10.3 시나리오 C: Nonconforming → 복귀

비행 중 드론 1기가 강풍에 의해 선언된 볼륨을 이탈합니다.

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "UPDATE",
  "msg_id": "f6a7b8c9-d0e1-2345-fabc-678901234567",
  "timestamp": "2026-06-18T05:15:00Z",
  "sim_timestamp": 900.0,
  "sender_id": "sdacs-seoul-01",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "intent_id": "intent-uuid-001",
    "updates": {
      "state": "Nonconforming",
      "updated_at": "2026-06-18T05:15:00Z",
      "sim_updated_at": 900.0
    },
    "reason": "DR-003 볼륨 이탈 — 풍속 12m/s 돌풍, off_nominal_volumes 내 위치",
    "deviated_drones": ["DR-003"],
    "deviation_details": {
      "drone_id": "DR-003",
      "declared_volume_idx": 0,
      "actual_position": [126.96, 37.56, 85.0],
      "distance_from_boundary_m": 120.0,
      "wind_speed_ms": 12.3
    }
  }
}
```

**8초 후 복귀:**

```json
{
  "protocol": "sdacs-intent",
  "version": "0.1.0",
  "msg_type": "UPDATE",
  "msg_id": "a7b8c9d0-e1f2-3456-abcd-789012345678",
  "timestamp": "2026-06-18T05:15:08Z",
  "sim_timestamp": 908.0,
  "sender_id": "sdacs-seoul-01",
  "context": { "mode": "SIMULATION", "auth_mode": "SIMULATED" },
  "payload": {
    "intent_id": "intent-uuid-001",
    "updates": {
      "state": "Activated",
      "updated_at": "2026-06-18T05:15:08Z",
      "sim_updated_at": 908.0
    },
    "reason": "DR-003 볼륨 내 복귀 완료 — APF 강풍 모드 보정"
  }
}
```

---

## 11. SDACS 통합

### 11.1 모듈 매핑

| 기능 | 기존 모듈 | 파일 경로 | Phase 422 활용 방식 |
|---|---|---|---|
| 메시지 전송 | WebSocket 브릿지 | `simulation/ws_bridge.py` | `sdacs-intent` 프로토콜 메시지 직렬화·전송 |
| 공역 관제 | AirspaceController | `src/airspace_control/controller/airspace_controller.py` | 충돌 예측 시 Operational Intent 생성·갱신 |
| 4D 예약 | AirspaceReservation | `simulation/airspace_reservation.py` | `Reservation` → `Volume4D` 변환, 겹침 검사 |
| 드론 상태 | DroneAgent | `simulation/drone_agent.py` | Nonconforming 감지 (위치 vs 볼륨 비교) |
| 드론 프로파일 | DroneProfiles | `src/airspace_control/agents/drone_profiles.py` | `AircraftType.profile` 매핑 |
| 좌표 변환 | CoordinateSystems | `src/airspace_control/utils/coordinate_systems.py` | AGL ↔ W84 고도 변환 |
| 메시지 타입 | MessageTypes | `src/airspace_control/comms/message_types.py` | 기존 `TelemetryMessage` 확장 |
| K-UTM 연동 | KUTMProtocol | `simulation/kutm_protocol.py` | 비행계획 → Operational Intent 변환 |

### 11.2 AirspaceController의 Intent 생산 흐름

```
DroneAgent.step() (10Hz)
    │
    ├─ 이륙 시 → AirspaceController에 ClearanceRequest 전송
    │
    ▼
AirspaceController._process_clearance() (1Hz)
    │
    ├─ FlightPathPlanner로 경로 산출
    ├─ AirspaceReservation으로 4D 슬롯 예약
    │
    ├─ [NEW] Reservation → Volume4D 변환
    ├─ [NEW] OperationalIntent 생성 (state=Accepted)
    ├─ [NEW] ws_bridge를 통해 CREATE 메시지 전송
    │
    ├─ ClearanceResponse로 드론에 승인 응답
    │
    ▼
DroneAgent 이륙
    │
    ├─ [NEW] AirspaceController가 UPDATE (state=Activated) 전송
    │
    ├─ 비행 중 위치 모니터링 (10Hz)
    │   ├─ 볼륨 내: 정상
    │   ├─ 볼륨 외 + off_nominal 내: UPDATE (state=Nonconforming)
    │   └─ off_nominal 외: UPDATE (state=Contingent)
    │
    ├─ 착륙
    │
    └─ [NEW] DELETE (미션 완료) 전송
```

### 11.3 ws_bridge의 Intent 소비 흐름

```
ws_bridge 수신 (WebSocket)
    │
    ├─ 프로토콜 판별: "sdacs-discovery" → Phase 421 핸들러
    │                  "sdacs-intent"    → Phase 422 핸들러
    │
    ▼
Phase 422 핸들러
    │
    ├─ NOTIFY (INTENT_CREATED / INTENT_ACTIVATED)
    │   └─ AirspaceController에 외부 의도 등록
    │       → 충돌 감지 스캔에 외부 볼륨 포함
    │
    ├─ NOTIFY (CONFLICT_DETECTED)
    │   └─ 우선순위 비교 → 양보/경매 판단
    │       → 볼륨 조정 후 UPDATE 발신
    │
    ├─ NOTIFY (INTENT_NONCONFORMING / INTENT_CONTINGENT)
    │   └─ 인접 인스턴스 비상 상태 반영
    │       → 해당 영역 드론에 경고·회피 지시
    │
    └─ NOTIFY (INTENT_ENDED / INTENT_DELETED)
        └─ 외부 의도 레지스트리에서 제거
```

### 11.4 신규 모듈 (Phase 422 구현 시 생성 예정)

| 모듈 (후보) | 경로 (후보) | 역할 |
|---|---|---|
| `IntentSerializer` | `src/federation/intent_serializer.py` | OperationalIntent ↔ JSON 직렬화·역직렬화 |
| `IntentValidator` | `src/federation/intent_validator.py` | JSON Schema 검증 + 비즈니스 규칙 검증 |
| `ConflictResolver` | `src/federation/conflict_resolver.py` | 충돌 감지 + 우선순위 협상 + Vickrey 경매 |
| `IntentStateManager` | `src/federation/intent_state_manager.py` | 상태 머신 전이 + 타임아웃 관리 |
| `VolumeGeometry` | `src/federation/volume_geometry.py` | GeoJSON 폴리곤 교차·버퍼 확장 연산 |

Phase 421에서 예고된 `IntentManager`(`src/federation/intent_manager.py`)가 이들 모듈을 오케스트레이션합니다.

---

## 12. 프로토콜 버전 협상

Phase 421 §8의 버전 정책을 동일하게 적용합니다.

| 버전 변경 | 호환성 | 예시 |
|---|---|---|
| PATCH (0.1.x) | 완전 호환 | 오타 수정, 설명 추가 |
| MINOR (0.x.0) | 하위 호환 | 선택 필드 추가 (예: 새 `AircraftType.profile` 값) |
| MAJOR (x.0.0) | 비호환 | 메시지 구조 변경, 필수 필드 추가/삭제 |

`sdacs-intent` 프로토콜 버전은 메시지 엔벨로프의 `version` 필드로 교환합니다.
`sdacs-discovery` 프로토콜 버전과 **독립적으로 관리**합니다.

---

## 13. 관련 링크

| 항목 | 참조 |
|---|---|
| ASTM F3548-21 | [ASTM 표준 페이지](https://www.astm.org/f3548-21.html) |
| GeoJSON RFC 7946 | [RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946) |
| InterUSS Platform (오픈소스 DSS 구현) | [github.com/interuss/dss](https://github.com/interuss/dss) |
| SDACS Phase 421 디스커버리 프로토콜 | `docs/certification/INSTANCE_DISCOVERY_PROTOCOL.md` |
| SDACS ODYSSEY 로드맵 | `docs/SIMULATOR_ODYSSEY_PLAN.md` — Track 🛰 Phase 421-440 |
| Phase 423 (지역 간 핸드오버) | *미작성 — Phase 421 §5 핸드오버 프로토콜 확장 예정* |
| Phase 424 (연합 충돌 해소) | *미작성 — 본 문서 §7 Vickrey 경매를 확장 예정* |
| Phase 425 (연합 NOTAM 전파) | *미작성 — NOTIFY 메시지를 NFZ 브로드캐스트로 확장 예정* |

---

*끝.*
