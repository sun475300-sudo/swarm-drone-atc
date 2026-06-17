# 🚨 사고 보고 양식 자동 작성 (GENESIS Phase 307)

*Created: 2026-06-17 · 근거 법령: 항공안전법(법률 제20183호) §59(항공안전 의무보고), 항공·철도 사고조사에 관한 법률(법률 제18424호)*
*면책: 본 문서는 시뮬레이션 사고 로그와 항철위 보고 양식 필드 간 매핑을 정리한 **개발자 참고 자료**이며, 운영자의 법적 보고 의무를 갈음하지 않습니다. 실 운영 시 항공·철도사고조사위원회(ARAIB) 최신 양식과 국토교통부 고시를 반드시 확인해야 합니다.*

---

## 1. 사고 분류 체계

항공안전법 §2 및 항공·철도 사고조사에 관한 법률 §2에 따른 사고 분류와 SDACS 시뮬레이션 이벤트의 매핑입니다.

| 분류 | 법적 정의 (요약) | SDACS 시뮬레이션 이벤트 | 트리거 모듈 |
|---|---|---|---|
| **항공사고** (Accident) | 사망·중상·기체 파손 | `collision` (실제 충돌 — `separation_m ≤ 0`) | `collision_predictor.py` → `conflict_events` |
| **항공준사고** (Serious Incident) | 공중충돌 위험, 지상 충돌 위험 | `near_miss` (이격거리 위반 — 수평 <10m 또는 수직 <3m) | `collision_predictor.py` CPA 경보 |
| **항공안전장애** (Occurrence) | 경미한 이상, 시스템 고장 | `fault_injection` (배터리·모터·GPS 장애) | `failsafe_manager.py` |

> **참고**: SDACS 시뮬레이션은 무인항공기 군집 환경이므로, 「항공안전법」 §59 ①항의 초경량비행장치/무인비행장치 사고 보고 요건에 준하여 분류합니다.

## 2. 항철위 보고 양식 필드 ↔ SDACS 데이터 매핑

항공·철도사고조사위원회 표준 보고 양식의 각 필드와 SDACS 시뮬레이션 데이터 소스의 매핑입니다.

| # | 보고 양식 필드 | SDACS 데이터 소스 | DB 테이블 / 모듈 |
|:-:|---|---|---|
| 1 | **발생 일시** | SimPy `env.now` → ISO 8601 타임스탬프 변환 | `drone_telemetry.time` |
| 2 | **발생 장소 (좌표)** | 사고 시점 드론 위치 `(lat, lon, alt)` | `drone_telemetry.lat/lon/alt` |
| 3 | **기체 정보** (형식·등록번호) | `DroneAgent.drone_id`, 기체 유형·성능 속성 | `simulation/drone_agent.py` DroneAgent |
| 4 | **운영자 정보** | 시뮬레이션 구성 파일의 운영자 메타데이터 | `config/default_simulation.yaml` |
| 5 | **사고 경위** | ATC 명령 로그 + 충돌 예측 이벤트 시퀀스 | `conflict_events` + ATC advisory 로그 |
| 6 | **기상 조건** | 사고 시점 `WindModel` 상태 (풍속·풍향·난류) | `simulation/weather.py` WindModel |
| 7 | **피해 상황** | 충돌 횟수, 이격거리, 피해 평가 | `conflict_events.separation_m`, `collision_count` |
| 8 | **조치 사항** | ATC 발령 어드바이저리 목록 | `resolution_advisory.py` AdvisoryType |
| 9 | **목격자/관제 기록** | ATC 로그 패널 데이터 (시간순 명령 이력) | `airspace_controller.py` advisory 이력 |
| 10 | **첨부 자료** | 3D 시각화 스냅샷, 텔레메트리 CSV | `visualization/simulator_3d.py` |

### 2.1 ATC 어드바이저리 유형 (조치 사항 세부)

사고 보고서의 「조치 사항」 필드에 기록되는 SDACS ATC 어드바이저리 목록입니다.

| AdvisoryType | 설명 | 기록 형식 |
|---|---|---|
| `CLIMB` | 고도 상승 회피 (기본 +20m) | `CLIMB +{delta_m}m at T={sim_time}s` |
| `DESCEND` | 고도 하강 회피 | `DESCEND -{delta_m}m at T={sim_time}s` |
| `TURN_LEFT` | 좌선회 회피 | `TURN_LEFT {deg}° at T={sim_time}s` |
| `TURN_RIGHT` | 우선회 회피 | `TURN_RIGHT {deg}° at T={sim_time}s` |
| `HOLD` | 현 위치 선회 대기 | `HOLD {loiter_s}s at T={sim_time}s` |
| `EVADE_APF` | APF 기반 긴급 회피 (NFZ 침입 등) | `EVADE_APF at T={sim_time}s` |
| `RESUME` | 대기 해제, 정상 비행 복귀 | `RESUME at T={sim_time}s` |

## 3. 자동 변환 파이프라인

시뮬레이션 사고 로그를 항철위 표준 보고서로 변환하는 5단계 파이프라인입니다.

```
[Step 1] 이벤트 감지
    │  collision_predictor.py  →  collision / near_miss 감지
    │  failsafe_manager.py     →  fault_injection 감지
    ▼
[Step 2] 텔레메트리 수집
    │  drone_telemetry (TimescaleDB) 또는 CSV export
    │  사고 전후 ±30초 윈도우의 10Hz 위치·상태 데이터
    ▼
[Step 3] 기상 데이터 스냅샷
    │  weather.py WindModel 상태 캡처
    │  풍속(m/s), 풍향(°), 난류 강도, APF 모드 (NORMAL/WINDY)
    ▼
[Step 4] ATC 명령 로그 추출
    │  airspace_controller.py advisory 이력
    │  resolution_advisory.py 발령 기록 (시간순)
    ▼
[Step 5] 보고서 생성
    │  JSON (기계 판독용) / Markdown (검토용) / PDF (제출용)
    └─→ accident_report_{timestamp}_{drone_id}.{json|md|pdf}
```

### 3.1 이벤트 감지 기준

| 이벤트 | 감지 조건 | 설정 파라미터 |
|---|---|---|
| `collision` | 두 드론 간 실제 접촉 (`separation_m ≤ 0`) | — |
| `near_miss` | 수평 이격 <10m 또는 수직 이격 <3m | `near_miss_lateral_m`, `near_miss_vertical_m` (`default_simulation.yaml`) |
| `fault_injection` | FailsafeManager 장애 주입 이벤트 발생 | `failsafe_manager.py` 설정 |

## 4. 보고서 JSON Schema

보고서의 기계 판독용 JSON 구조를 정의합니다. (`accident_report.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SDACS Accident Report (ARAIB Format)",
  "type": "object",
  "required": [
    "report_id", "classification", "datetime_utc",
    "location", "aircraft_info", "incident_summary"
  ],
  "properties": {
    "report_id": {
      "type": "string",
      "description": "고유 보고서 ID (형식: SDACS-RPT-{YYYYMMDD}-{seq})"
    },
    "classification": {
      "type": "string",
      "enum": ["accident", "serious_incident", "occurrence"],
      "description": "사고 분류 (항공사고 / 항공준사고 / 항공안전장애)"
    },
    "datetime_utc": {
      "type": "string",
      "format": "date-time",
      "description": "발생 일시 (ISO 8601, UTC)"
    },
    "location": {
      "type": "object",
      "properties": {
        "lat": { "type": "number", "description": "위도 (degrees)" },
        "lon": { "type": "number", "description": "경도 (degrees)" },
        "alt_m": { "type": "number", "description": "고도 (meters AGL)" }
      },
      "required": ["lat", "lon", "alt_m"]
    },
    "aircraft_info": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "drone_id": { "type": "string" },
          "type": { "type": "string", "description": "기체 유형" },
          "battery_pct": { "type": "integer", "description": "사고 시점 배터리 잔량" },
          "speed_mps": { "type": "number", "description": "사고 시점 속도 (m/s)" },
          "heading_deg": { "type": "number", "description": "사고 시점 방위각" }
        },
        "required": ["drone_id"]
      },
      "description": "관련 기체 정보 목록"
    },
    "weather": {
      "type": "object",
      "properties": {
        "wind_speed_mps": { "type": "number", "description": "풍속 (m/s)" },
        "wind_direction_deg": { "type": "number", "description": "풍향 (degrees)" },
        "turbulence_intensity": { "type": "number", "description": "난류 강도 (0.0-1.0)" },
        "apf_mode": { "type": "string", "enum": ["NORMAL", "WINDY"] }
      },
      "description": "사고 시점 기상 조건 (WindModel 스냅샷)"
    },
    "incident_summary": {
      "type": "string",
      "description": "사고 경위 서술 (자동 생성)"
    },
    "separation_m": {
      "type": "number",
      "description": "감지 시점 최소 이격거리 (m)"
    },
    "damage_assessment": {
      "type": "object",
      "properties": {
        "collision_count": { "type": "integer" },
        "drones_affected": { "type": "integer" },
        "resolved": { "type": "boolean" },
        "resolution_type": { "type": "string", "description": "avoidance / atc_command" }
      },
      "description": "피해 상황 평가"
    },
    "atc_advisories": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sim_time_s": { "type": "number" },
          "advisory_type": {
            "type": "string",
            "enum": ["CLIMB", "DESCEND", "TURN_LEFT", "TURN_RIGHT", "HOLD", "EVADE_APF", "RESUME"]
          },
          "target_drone_id": { "type": "string" },
          "detail": { "type": "string" }
        },
        "required": ["sim_time_s", "advisory_type", "target_drone_id"]
      },
      "description": "발령된 ATC 어드바이저리 목록 (시간순)"
    },
    "telemetry_window": {
      "type": "object",
      "properties": {
        "start_time_utc": { "type": "string", "format": "date-time" },
        "end_time_utc": { "type": "string", "format": "date-time" },
        "sample_count": { "type": "integer" },
        "export_path": { "type": "string", "description": "텔레메트리 CSV 파일 경로" }
      },
      "description": "사고 전후 텔레메트리 수집 윈도우 (±30초)"
    },
    "attachments": {
      "type": "array",
      "items": { "type": "string" },
      "description": "첨부 파일 경로 목록 (3D 시각화 스냅샷, CSV 등)"
    }
  }
}
```

## 5. 보고 시한

항공안전법 §59 및 항공·철도 사고조사에 관한 법률 §17에 따른 법적 보고 시한입니다.

| 분류 | 보고 시한 | 보고 대상 | SDACS 자동화 |
|---|:-:|---|---|
| **항공사고** (Accident) | **즉시** | 국토교통부 + 항철위 | 이벤트 감지 즉시 JSON 생성 → 알림 |
| **항공준사고** (Serious Incident) | **72시간** 이내 | 국토교통부 + 항철위 | 이벤트 큐잉 → 일괄 보고서 생성 |
| **항공안전장애** (Occurrence) | **96시간** 이내 | 국토교통부 | 이벤트 큐잉 → 주기적 보고서 생성 |

> **참고**: 시뮬레이션 환경에서는 실제 보고 제출이 아닌, 보고서 양식의 자동 생성까지를 범위로 합니다. 실 운영 시 항공안전 의무보고 시스템(KAIRS)을 통한 제출이 필요합니다.

## 6. 생성 파일 명명 규칙

```
accident_report_{YYYYMMDD}T{HHmmss}_{drone_id}.json     # 기계 판독용
accident_report_{YYYYMMDD}T{HHmmss}_{drone_id}.md       # 검토용
accident_report_{YYYYMMDD}T{HHmmss}_{drone_id}.pdf      # 제출용
```

예시: `accident_report_20260617T143022_drone_007.json`

## 7. 격차 및 향후 과제

| 영역 | 현 상태 | 격차 | 비고 |
|---|---|---|---|
| JSON 보고서 생성기 | 스키마 정의 완료 | 구현 필요 | 파이프라인 Step 5 |
| PDF 렌더링 | 미구현 | WeasyPrint / ReportLab 선정 필요 | GENESIS 307 후속 |
| KAIRS 연동 | 해당 없음 (시뮬레이션) | 실 운영 시 API 연동 필요 | ODYSSEY Track |
| 다중 드론 복합 사고 | 쌍별(pairwise) 기록만 가능 | N-체 동시 사고 시나리오 보고서 병합 로직 | 추후 확장 |

## 🔗 관련

- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 항공안전법·드론활용촉진법 적합성 매트릭스 (Phase 301)
- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 5계층 안전망 요구사항 추적 매트릭스 (Phase 306)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 인증 Phase 301-320
- `simulation/collision_predictor.py` — 충돌 예측 모듈
- `simulation/failsafe_manager.py` — 장애 주입/안전장치 관리
- `simulation/weather.py` — WindModel 기상 모델
- `src/airspace_control/avoidance/resolution_advisory.py` — ATC 어드바이저리 정의
- `db/migrations/001_initial_schema.sql` — 텔레메트리·충돌 이벤트 DB 스키마
