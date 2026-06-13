# 🏭 비행계획 신고/승인 신청서 자동 생성 (GENESIS Phase 303)

*Created: 2026-06-13 · 근거: 항공안전법 §127(비행승인) · 시행규칙 §306(비행계획 제출, Drone One-Stop)*
*면책: 본 도구는 신청서 필드 구성을 보조하는 **개발자 참고 자료**이며, 운영자의 법적 신고 의무를 갈음하지 않는다. 실 신청은 Drone One-Stop(drone.onestop.go.kr)을 통해야 한다.*

---

## 1. 모듈

`src/certification/flight_plan_submission.py` — 결정적(deterministic) 양식 생성기.

| 구성 | 설명 |
|---|---|
| `Applicant` | 신청인(성명·기관·주소·연락처) |
| `Aircraft` | 비행장치(신고번호·형식·자체중량·용도). 음수 중량 거부 |
| `FlightPlan` | 비행 일시·중심좌표·반경·최대고도·방식·목적. 좌표/반경/고도 범위 검증 |
| `Pilot` | 조종자(성명·1~4종 자격·비행경력). 자격 범위 검증 |
| `FlightMethod` | 주간/야간 × 가시권(VLOS)/비가시권(BVLOS) |
| `ApprovalRequirement` | 추가 승인·인증 요건 enum |
| `build_flight_plan_submission()` | 검증된 입력 → `FlightPlanSubmission` |

출력: `to_dict()`(JSON 직렬화 가능 한국어 라벨) · `to_text()`(제출용 평문).

## 2. 승인 요건 자동 판정

`build_flight_plan_submission()`는 입력에서 추가 요건을 결정적으로 도출한다.

| 조건 | 도출 요건 | 임계값 |
|---|---|---|
| 최대고도 > 150m | `ALTITUDE_OVER_150M` (비행승인) | `MAX_VISUAL_ALTITUDE_M = 150.0` |
| 야간 또는 비가시(BVLOS) | `SPECIAL_FLIGHT_APPROVAL` (특별비행승인) | `FlightMethod.is_night`/`is_bvlos` |
| 자체중량 > 25kg | `SAFETY_CERTIFICATION` (안전성 인증) | `SAFETY_CERT_WEIGHT_KG = 25.0` |

경량(≤25kg)·주간·가시권·150m 이하 비행은 추가 요건 없음으로 판정된다.

## 3. 사용 예

```python
from src.certification.flight_plan_submission import (
    Aircraft, Applicant, FlightMethod, FlightPlan, Pilot,
    build_flight_plan_submission,
)

sub = build_flight_plan_submission(
    Applicant("홍길동", "SDACS 드론팀", "서울 강남구 테헤란로 1", "010-1234-5678"),
    Aircraft("K-2026-0001", "SDACS-Q4", 4.2, "연구·실증"),
    FlightPlan("2026-07-01T09:00", "2026-07-01T11:00",
               37.5665, 126.9780, 300.0, 120.0,
               FlightMethod.VISUAL_DAY, "군집 비행 실증"),
    Pilot("홍길동", 2, 150.0),
)
print(sub.to_text())       # 제출용 평문 양식
form = sub.to_dict()       # JSON 직렬화 가능 dict
```

데모: `python src/certification/flight_plan_submission.py`

## 4. 테스트

`tests/test_flight_plan_submission.py` — 14건 (양식 구성·라벨·승인 요건 4종·경계값 2종·입력 검증·시각 역전·JSON 직렬화).

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 시행규칙 §306 매핑 (GENESIS 301)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 Phase 303
- [`ACCIDENT_REPORT_ARAIB.md`](ACCIDENT_REPORT_ARAIB.md) — 사고 보고 양식 (GENESIS 307)
