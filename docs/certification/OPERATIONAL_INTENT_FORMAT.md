# ODYSSEY Phase 422 — 운영 의도(Operational Intent) 교환 포맷 사양

*Operational Intent Exchange Format Specification*
*Created: 2026-06-18 — ODYSSEY Phase 422*

> **목적**: SDACS 다중 인스턴스 간(inter-USS) 운영 의도를 교환하기 위한 4D 볼륨 직렬화 포맷을 정의합니다.
> ASTM F3548-21 표준에 정렬하며, Phase 421 인스턴스 디스커버리 프로토콜과 연동합니다.

---

## 1. 표준 정렬

| 표준 | 항목 | SDACS 매핑 |
|------|------|-----------|
| ASTM F3548-21 | §A2.5 Operational Intent | `OperationalIntent` 스키마 |
| ASTM F3548-21 | §A2.3 Volume4D | `Volume4D` 스키마 |
| ICAO UTM Framework Ed.4 | Annex E | 공역 분류 (Phase 408) |
| GUTMA | Inter-USS Protocol v1 | 메시지 교환 패턴 |

## 2. 4D 볼륨 정의

### 2.1 Volume4D 스키마

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "Volume4D",
  "description": "4차원 공역 볼륨 (공간 3D + 시간 1D)",
  "type": "object",
  "required": ["outline_polygon", "altitude_lower", "altitude_upper", "time_start", "time_end"],
  "properties": {
    "outline_polygon": {
      "description": "GeoJSON Polygon (WGS84, [lng, lat] 순서)",
      "type": "object",
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
            }
          }
        }
      }
    },
    "outline_circle": {
      "description": "대안: 원형 볼륨 (center + radius)",
      "type": "object",
      "properties": {
        "center": {
          "type": "object",
          "properties": {
            "lng": { "type": "number" },
            "lat": { "type": "number" }
          }
        },
        "radius_m": { "type": "number", "minimum": 0 }
      }
    },
    "altitude_lower": {
      "description": "하한 고도 (m, WGS84 타원체 위)",
      "type": "object",
      "properties": {
        "value_m": { "type": "number" },
        "reference": { "enum": ["W84", "SFC"], "default": "W84" }
      }
    },
    "altitude_upper": {
      "description": "상한 고도 (m, WGS84 타원체 위)",
      "type": "object",
      "properties": {
        "value_m": { "type": "number" },
        "reference": { "enum": ["W84", "SFC"], "default": "W84" }
      }
    },
    "time_start": {
      "description": "시작 시각 (ISO 8601 UTC)",
      "type": "string",
      "format": "date-time"
    },
    "time_end": {
      "description": "종료 시각 (ISO 8601 UTC)",
      "type": "string",
      "format": "date-time"
    },
    "buffer_lateral_m": {
      "description": "수평 완충 마진 (m)",
      "type": "number",
      "default": 50
    },
    "buffer_vertical_m": {
      "description": "수직 완충 마진 (m)",
      "type": "number",
      "default": 15
    },
    "buffer_temporal_s": {
      "description": "시간 완충 마진 (초)",
      "type": "number",
      "default": 30
    }
  }
}
```

## 3. OperationalIntent 스키마

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "OperationalIntent",
  "description": "SDACS 운영 의도 교환 메시지",
  "type": "object",
  "required": ["id", "state", "priority", "volumes", "operator_id", "uss_id", "aircraft"],
  "properties": {
    "id": {
      "description": "UUID v4 고유 식별자",
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "description": "의도 버전 (충돌 시 최신 우선)",
      "type": "integer",
      "minimum": 1
    },
    "state": {
      "description": "현재 상태",
      "enum": ["Accepted", "Activated", "Nonconforming", "Contingent", "Ended"]
    },
    "priority": {
      "description": "우선순위 (0=최저, 100=최고, 긴급 의료=90+)",
      "type": "integer",
      "minimum": 0,
      "maximum": 100
    },
    "volumes": {
      "description": "정상 운영 4D 볼륨 배열",
      "type": "array",
      "items": { "$ref": "#/definitions/Volume4D" },
      "minItems": 1
    },
    "off_nominal_volumes": {
      "description": "비정상/비상 시 확장 볼륨",
      "type": "array",
      "items": { "$ref": "#/definitions/Volume4D" }
    },
    "operator_id": {
      "description": "운영자 식별자",
      "type": "string"
    },
    "uss_id": {
      "description": "관제 인스턴스(USS) 식별자",
      "type": "string",
      "format": "uri"
    },
    "aircraft": {
      "type": "object",
      "properties": {
        "type": { "enum": ["FIXED_WING", "ROTORCRAFT", "VTOL", "SWARM"] },
        "swarm_count": { "type": "integer", "minimum": 1 },
        "mtow_kg": { "type": "number" },
        "registration_ids": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" }
  }
}
```

## 4. 상태 머신 (State Machine)

```
                ┌──────────┐
     CREATE     │ Accepted │
    ────────►   │ (대기중)  │
                └────┬─────┘
                     │ ACTIVATE
                     ▼
                ┌──────────┐
                │ Activated│ ◄──── 정상 운영 중
                │ (활성)   │
                └──┬───┬───┘
        이탈 감지  │   │  비상 선언
                   ▼   ▼
           ┌──────────┐ ┌───────────┐
           │Nonconform│ │Contingent │
           │(이탈)    │ │(비상)     │
           └──┬───────┘ └──┬────────┘
              │             │
              ▼             ▼
                ┌──────────┐
                │  Ended   │
                │ (종료)   │
                └──────────┘
```

### 상태 전이 규칙

| 현재 상태 | 전이 가능 | 트리거 |
|----------|----------|--------|
| Accepted | Activated, Ended | 비행 시작 또는 취소 |
| Activated | Nonconforming, Contingent, Ended | 이탈/비상/임무 완료 |
| Nonconforming | Activated, Contingent, Ended | 복귀/비상 격상/강제 종료 |
| Contingent | Ended | 비상 착륙 완료 |
| Ended | — | 최종 상태 |

## 5. 메시지 유형

| 유형 | 방향 | 설명 |
|------|------|------|
| `INTENT_CREATE` | USS-A → DSS → USS-B | 새 운영 의도 등록 |
| `INTENT_UPDATE` | USS-A → DSS → USS-B | 기존 의도 수정 (state/volume 변경) |
| `INTENT_DELETE` | USS-A → DSS → USS-B | 의도 철회 |
| `INTENT_NOTIFY` | DSS → USS-B | 인접 인스턴스에 새 의도 알림 |
| `INTENT_ACK` | USS-B → USS-A | 수신 확인 |
| `CONFLICT_ALERT` | DSS → USS-A, USS-B | 볼륨 충돌 감지 알림 |
| `PRIORITY_NEGOTIATE` | USS-A ↔ USS-B | 우선순위 협상 (Vickrey 경매) |
| `HANDOVER_REQUEST` | USS-A → USS-B | 관제권 이양 요청 (Phase 423 연계) |

### 메시지 봉투 (Wire Format)

```json
{
  "message_type": "INTENT_CREATE",
  "message_id": "msg-uuid-v4",
  "timestamp": "2026-06-18T12:00:00Z",
  "sender_uss_id": "https://sdacs-a.example.com",
  "recipient_uss_id": "https://sdacs-b.example.com",
  "payload": { ... },
  "signature": "HMAC-SHA256 서명"
}
```

## 6. 충돌 감지 알고리즘

두 OperationalIntent의 충돌은 시간적 교차 **AND** 공간적 교차로 판정합니다.

### 6.1 시간적 교차

```python
def temporal_overlap(a: Volume4D, b: Volume4D) -> bool:
    a_start = a.time_start - timedelta(seconds=a.buffer_temporal_s)
    a_end = a.time_end + timedelta(seconds=a.buffer_temporal_s)
    b_start = b.time_start - timedelta(seconds=b.buffer_temporal_s)
    b_end = b.time_end + timedelta(seconds=b.buffer_temporal_s)
    return a_start < b_end and b_start < a_end
```

### 6.2 공간적 교차

```python
def spatial_overlap(a: Volume4D, b: Volume4D) -> bool:
    # 수직 겹침
    a_lower = a.altitude_lower.value_m - a.buffer_vertical_m
    a_upper = a.altitude_upper.value_m + a.buffer_vertical_m
    b_lower = b.altitude_lower.value_m - b.buffer_vertical_m
    b_upper = b.altitude_upper.value_m + b.buffer_vertical_m
    if a_lower >= b_upper or b_lower >= a_upper:
        return False
    # 수평 겹침 (GeoJSON 폴리곤 교차 + 버퍼)
    a_poly = buffer(shape(a.outline_polygon), a.buffer_lateral_m)
    b_poly = buffer(shape(b.outline_polygon), b.buffer_lateral_m)
    return a_poly.intersects(b_poly)
```

### 6.3 충돌 해소 (Phase 424 연계)

| 방법 | 조건 | 설명 |
|------|------|------|
| 우선순위 기반 | priority 차이 ≥ 10 | 높은 우선순위 의도 유지, 낮은 쪽 재경로 |
| Vickrey 경매 | priority 차이 < 10 | 두 USS가 비공개 입찰, 2등가격 결정 |
| 시간 분할 | 고도 분리 불가 | 시간대를 나누어 순차 운용 |
| 고도 분리 | 수평 분리 불가 | 최소 30m 수직 이격 |

## 7. 예시 시나리오

### 7.1 의료 긴급 배송 (우선순위 95)

```json
{
  "id": "oi-2026-med-001",
  "version": 1,
  "state": "Activated",
  "priority": 95,
  "volumes": [{
    "outline_circle": {
      "center": { "lng": 126.3922, "lat": 34.7938 },
      "radius_m": 500
    },
    "altitude_lower": { "value_m": 50, "reference": "SFC" },
    "altitude_upper": { "value_m": 120, "reference": "SFC" },
    "time_start": "2026-06-18T09:00:00Z",
    "time_end": "2026-06-18T09:30:00Z",
    "buffer_lateral_m": 100,
    "buffer_temporal_s": 60
  }],
  "off_nominal_volumes": [{
    "outline_circle": {
      "center": { "lng": 126.3922, "lat": 34.7938 },
      "radius_m": 1000
    },
    "altitude_lower": { "value_m": 0, "reference": "SFC" },
    "altitude_upper": { "value_m": 150, "reference": "SFC" },
    "time_start": "2026-06-18T09:00:00Z",
    "time_end": "2026-06-18T10:00:00Z"
  }],
  "operator_id": "mokpo-univ-drone-lab",
  "uss_id": "https://sdacs-mokpo.example.com",
  "aircraft": {
    "type": "ROTORCRAFT",
    "swarm_count": 1,
    "mtow_kg": 8.5,
    "registration_ids": ["HL-D5001"]
  }
}
```

## 8. SDACS 통합

### `ws_bridge` 연동

| `ws_bridge` 이벤트 | OperationalIntent 매핑 |
|-------------------|----------------------|
| 드론 이륙 | `INTENT_CREATE` + state: Accepted → Activated |
| 경로 변경 | `INTENT_UPDATE` (volumes 갱신) |
| 임무 완료 | `INTENT_UPDATE` state: Activated → Ended |
| 비상 RTL | `INTENT_UPDATE` state → Contingent |
| CPA 위반 | `CONFLICT_ALERT` 트리거 |

### `AirspaceController` 연동

- 1Hz 틱마다 활성 OperationalIntent 목록 갱신
- 인접 인스턴스의 의도와 충돌 검사
- 충돌 시 우선순위 비교 후 ResolutionAdvisory 발행

### 보안 (Phase 421 연계)

- 전송: HTTPS + mTLS (상호 인증서 검증)
- 인증: JWT Bearer 토큰 (인스턴스 간)
- 무결성: HMAC-SHA256 메시지 서명
- 감사: 모든 교환 기록 불변 로그 (Phase 429 연계)

---

*ODYSSEY Phase 422 완료 — 운영 의도(Operational Intent) 교환 포맷 사양 (2026-06-18)*
