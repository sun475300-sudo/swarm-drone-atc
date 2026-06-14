# 🛟 사고 보고 양식 자동 작성 (GENESIS Phase 307)

*Created: 2026-06-14 · 근거: 「항공·철도 사고조사에 관한 법률」, 「항공안전법」 §2(정의)·§62(사고 보고), ICAO Annex 13*
*면책: 본 문서·모듈은 시뮬레이션 사고 로그로부터 보고서 초안을 결정적으로 생성하는 보조 도구이며, 실 사고 시에는 항공·철도사고조사위원회(ARAIB)·국토교통부의 최신 고시와 실제 보고 절차를 따라야 한다.*

---

## 1. 목적

SDACS 시뮬레이션의 사고 로그(드론 간 분리거리 시계열·충돌 여부·인명/물적 피해)를
입력받아, 항공·철도사고조사위원회(ARAIB) 표준 사고 보고서 데이터를 결정적으로
구성하고 **사고 / 준사고 / 안전장애** 등급을 자동 분류한다. 외부 API 호출 없이
사건 분류 + 보고서 구성 + export(JSON·텍스트)만 수행한다.

구현: [`simulation/accident_report.py`](../../simulation/accident_report.py)
테스트: [`tests/test_accident_report.py`](../../tests/test_accident_report.py) — **19건 PASS**

## 2. 사건 분류 기준

| 등급 | 조건 | 보고 의무 |
|---|---|:-:|
| **초경량비행장치사고** | 물리적 충돌(분리 ≤ 5 m) 또는 인명 피해 또는 기체 중대/전파 손상 | 대상 |
| **항공기준사고** | 충돌은 없으나 분리거리 < 10 m (근접) | 대상 |
| **항공안전장애** | 그 외 보고된 안전 저해 사건 (분리 ≥ 10 m) | 비대상 |

임계값은 `config/default_simulation.yaml`의 `separation_standards`(`near_miss_lateral_m: 10`)와
정렬되며, 모듈 상수 `CONTACT_SEPARATION_M`(5 m)·`NEAR_MISS_SEPARATION_M`(10 m)로 노출된다.
손상 등급은 `DamageLevel`(없음/경미/중대/전파, ICAO Annex 13 정렬)로 표현한다.

## 3. 입력 데이터 모델

| dataclass / enum | 핵심 필드 |
|---|---|
| `InvolvedDrone` | 드론 ID·모델·운영자·신고번호 |
| `OccurrenceRecord` | 식별번호·일시·좌표·고도·관련 기체·최소분리·접촉여부·피해·경위·시계열·기여요인 |
| `OccurrenceCategory` | 사고 / 준사고 / 안전장애 |
| `DamageLevel` | 없음 / 경미 / 중대 / 전파 |

## 4. API

```python
from datetime import datetime
from simulation.accident_report import (
    InvolvedDrone, DamageLevel, occurrence_from_log,
    classify_occurrence, build_report, export_text, export_json,
)

drones = (
    InvolvedDrone("d1", "SDACS-Quad-X", "동강대 SDACS팀", "UAS-2026-0001"),
    InvolvedDrone("d2", "SDACS-Quad-X", "동강대 SDACS팀"),
)
# 시뮬 분리거리 로그 → 사건 기록 (최소분리·접촉여부 자동 도출)
record = occurrence_from_log(
    "OCC-001", datetime(2026, 7, 1, 14, 30), 34.79, 126.39, 80.0,
    drones, separation_log=[30.0, 12.0, 3.5, 18.0],
    narrative="순항 중 경로 교차로 충돌",
)
report = build_report(record, reporter="SDACS 관제 시스템")
print(export_text(report))   # 사람이 읽는 한국어 보고서
print(export_json(report))   # 기계 처리용 JSON
```

- `occurrence_from_log()` 는 분리거리 시계열의 최소값으로 접촉(충돌) 여부를 도출한다.
- `build_report()` 는 보고자 누락·관련 기체 부재 등 검증 실패 시 `ValueError` 를 발생시킨다.
- `classify_occurrence()` 만 단독 호출하면 분류 결과(`OccurrenceClassification`)만 얻는다.
- 동일 입력 → 동일 출력(결정성). 재현성 테스트 `test_build_report_structure_and_determinism` 로 보장.

## 5. 안전권고 자동 생성

분류 등급별 결정적 안전권고를 포함한다 — 예: 사고 시 "5계층 안전망 Layer 4(긴급 회피)
로그 재현 분석", 준사고 시 "CPA 예측 선행시간 상향 조정 타당성 평가". 사고 조사
재발 방지 권고를 표준화한다.

## 6. 5계층 안전망 연계

본 모듈은 **사후(Post-occurrence) 규제 보고** 계층에 해당한다 — 사고/준사고 발생 시
ARAIB 표준 양식으로 자동 분류·문서화하여 조사·보고 의무를 보조한다. 비행 전
규제 적합(Phase 302 SORA·Phase 303 비행계획 신고)과 함께 `docs/certification/`
규제 적합 자산의 사고 대응 축을 구성한다.
