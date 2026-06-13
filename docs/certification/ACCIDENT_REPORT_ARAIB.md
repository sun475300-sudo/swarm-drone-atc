# 🏭 사고 보고 양식(항철위/ARAIB) 자동 작성 (GENESIS Phase 307)

*Created: 2026-06-13 · 근거: 항공안전법 §134(사고 보고 의무) · 항공·철도 사고조사에 관한 법률*
*면책: 본 도구는 보고 양식 작성을 보조하는 **개발자 참고 자료**이며, 운영자의 법적 보고 의무를 갈음하지 않는다. 실 보고는 항철위(ARAIB)·국토교통부 절차를 따라야 한다.*

---

## 1. 모듈

`src/certification/accident_report.py` — 시뮬레이션 장애 주입 로그(INJ Phase 6) → 표준 사고 보고서 변환.

| 구성 | 설명 |
|---|---|
| `EventType` | 충돌·NFZ 진입·모터 고장·GPS 손실·통신 두절·배터리 위급 (INJ 유형 정렬) |
| `Weather` | 풍속·시정 (음수 거부) |
| `IncidentEvent` | 단일 사건(일시·좌표·고도·기체·유형·비행단계·피해·기상·경위). 음수 피해 거부 |
| `Severity` | 사고 / 준사고 / 경미한 사고 |
| `classify_severity()` | 사망·부상·손상으로 심각도 결정적 분류 |
| `build_accident_report()` | 사건 → `AccidentReport` (심각도 + 즉시보고 의무 판정) |
| `from_sim_log()` | 시뮬 로그(dict 목록) → `IncidentEvent` 목록 (미지 유형 거부) |

출력: `to_dict()`(JSON 직렬화 가능 한국어 라벨) · `to_text()`(제출용 평문).

## 2. 심각도 분류 규칙

`classify_severity()`는 다음 우선순위로 결정적 분류한다.

| 우선순위 | 조건 | 구분 |
|:-:|---|---|
| 1 | 사망 > 0 또는 부상 > 0 | **사고** (ACCIDENT) |
| 2 | 충돌(COLLISION) 또는 재산피해 > 1천만원 | **준사고** (SERIOUS_INCIDENT) |
| 3 | 그 외 (배터리·GPS·통신 등 경미) | **경미한 사고** (INCIDENT) |

임계값: `SERIOUS_PROPERTY_DAMAGE_KRW = 10,000,000`.

**즉시 보고 의무**: 심각도가 사고이거나 유형이 충돌인 경우 `immediate_report_required = True`.

## 3. 사용 예

```python
from src.certification.accident_report import (
    EventType, IncidentEvent, Weather,
    build_accident_report, from_sim_log,
)

# 시뮬 장애 로그 → 사건 목록
events = from_sim_log(sim_injection_log)        # list[dict] → list[IncidentEvent]
report = build_accident_report(events[0])
print(report.to_text())                         # ARAIB 평문 양식
print(report.severity, report.immediate_report_required)
```

데모: `python src/certification/accident_report.py`

## 4. 테스트

`tests/test_accident_report.py` — 18건 (심각도·경계값·NFZ 준사고·보고서 구성·즉시보고 의무 2종·JSON 직렬화·입력 검증·좌표·시뮬 로그 변환).

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — §131의2 SMS / 사고 보고 매핑 (GENESIS 301)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 Phase 307
- [`FLIGHT_PLAN_SUBMISSION.md`](FLIGHT_PLAN_SUBMISSION.md) — 비행계획 신청서 (GENESIS 303)
