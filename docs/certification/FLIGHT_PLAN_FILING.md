# 🛩 비행계획 신고 양식 자동 생성 (GENESIS Phase 303)

*Created: 2026-06-14 · 근거: 「항공안전법」 §127(초경량비행장치 비행승인), 시행규칙 §308, 드론 원스톱 민원서비스(drone.onestop.go.kr)*
*면책: 본 문서·모듈은 시뮬레이션 파라미터로부터 신청서 초안을 결정적으로 생성하는 보조 도구이며, 실 운영자는 최신 고시·국토부 공지와 실제 원스톱 시스템 제출을 따라야 한다.*

---

## 1. 목적

SDACS 시뮬레이션의 비행 파라미터(구역·고도·일시·방식·기체)를 입력받아, 한국
드론 원스톱 비행승인 신청서 데이터를 결정적으로 구성하고 **비행승인 / 특별비행승인 /
기체신고** 필요 여부를 자동 판정한다. 외부 API 호출 없이 입력 검증과 양식 export(JSON·텍스트)만 수행한다.

구현: [`simulation/flight_plan_filing.py`](../../simulation/flight_plan_filing.py)
테스트: [`tests/test_flight_plan_filing.py`](../../tests/test_flight_plan_filing.py) — **18건 PASS**

## 2. 판정 임계값

| 항목 | 임계값 | 근거 | 모듈 상수 |
|---|---|---|---|
| 관제권 진입 | 공항 표점 반경 9.3 km 이내 | 시행규칙 별표 23 | `CONTROL_ZONE_RADIUS_M` |
| 고도 초과 | 지표/수면 150 m AGL 초과 | §127, 시행규칙 §308 | `MAX_ALTITUDE_AGL_M` |
| 비행금지구역 | P-구역(예: P-73/P-518) 내부 | 공역 고시 | `ControlZone.is_prohibited` |
| 특별비행승인 | 비가시권(BVLOS) 또는 야간 비행 | §129, 특별비행승인 고시 | `FlightPlan.is_bvlos/is_night` |
| 기체 신고 | 사업용 전 기체 / 비사업 자체중량 12 kg 초과 | §122, §125 | `WEIGHT_REPORT_THRESHOLD_KG` |

관제권/금지구역 진입은 비행 반경과 구역 경계의 겹침(`haversine 거리 − 비행반경 ≤ 구역반경`)으로 판정한다.

## 3. 입력 데이터 모델

| dataclass | 핵심 필드 |
|---|---|
| `FlightPlanApplicant` | 성명·연락처·주소·사업자 여부·사업자등록번호 |
| `FlightPlanAircraft` | 모델·신고번호·자체중량·최대이륙중량·목적 |
| `ControlZone` | 명칭·중심좌표·반경(기본 9.3 km)·금지구역 여부 |
| `FlightPlan` | 구역명·중심좌표·반경·최대고도(AGL)·시작/종료·BVLOS·야간 |

## 4. API

```python
from datetime import datetime
from simulation.flight_plan_filing import (
    FlightPlan, FlightPlanAircraft, FlightPlanApplicant, ControlZone,
    build_filing, export_text, export_json,
)

filing = build_filing(
    FlightPlan("한강공원", 37.5, 127.0, 300.0, 180.0,
               datetime(2026, 7, 1, 9), datetime(2026, 7, 1, 11)),
    FlightPlanAircraft("SDACS-Quad-X", "UAS-2026-0001", 2.5, 4.0),
    FlightPlanApplicant("홍길동", "010-1234-5678", "서울 강남구"),
    control_zones=[ControlZone("김포공항", 37.56, 126.79)],
)
print(export_text(filing))   # 사람이 읽는 한국어 신청서
print(export_json(filing))   # 기계 처리용 JSON
```

- `build_filing()` 는 필수 입력 검증 실패 시 `ValueError` 를 발생시킨다(시스템 경계 검증).
- `assess_filing()` 만 단독 호출하면 판정 결과(`FilingDecision`)만 얻는다.
- 동일 입력 → 동일 출력(결정성). 재현성 테스트 `test_build_filing_structure_and_determinism` 로 보장.

## 5. 5계층 안전망 연계

본 모듈은 **Layer 0(사전 규제 적합)** 에 해당한다 — 비행 전 승인 요건을 자동 분류하여
운영자가 원스톱 제출 전 누락 항목을 인지하게 한다. SORA 계산기(Phase 302)와 함께
`docs/certification/` 규제 적합 자산을 구성한다.
