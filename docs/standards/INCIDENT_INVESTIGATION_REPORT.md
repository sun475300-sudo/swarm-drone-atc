# 🛰 사고 조사 데이터 표준 변환기 (ODYSSEY Phase 467)

*Created: 2026-06-14 · 근거: ICAO Annex 13 (Aircraft Accident and Incident Investigation), ICAO ADREP/ECCAIRS 발생 분류 택소노미*
*면책: 본 문서·모듈은 시뮬레이션 안전 사건 로그를 표준 조사 양식으로 결정적으로 변환하는 보조 도구이며, 실 사고 조사는 관할 조사기관(국토부 항공·철도사고조사위원회 등)의 절차를 따라야 한다.*

---

## 1. 목적

SDACS 시뮬레이션이 기록한 안전 사건(충돌·근접·충돌징후·시스템 고장·공역 침범)을
**ICAO Annex 13** 구조의 표준 사고 조사 양식으로 결정적으로 변환한다. Phase 466
(텔레메트리 JSON Schema 표준)이 *운항 단계* 데이터 교환 표준을 제공했다면, 본 Phase는
*조사 단계* 데이터 교환 표준을 제공한다. 외부 API 호출 없이 입력 검증과 양식 export(JSON·텍스트)만 수행한다.

구현: [`simulation/incident_investigation_report.py`](../../simulation/incident_investigation_report.py)
테스트: [`tests/test_incident_investigation_report.py`](../../tests/test_incident_investigation_report.py) — **25건 PASS**

## 2. 발생 등급 분류 (ICAO Annex 13 §1)

| 등급 | 정의 | 시뮬 매핑 | 모듈 상수 |
|---|---|---|---|
| **Accident(사고)** | 기체 손상/멸실 또는 인명 피해 | 실 충돌(COLLISION) | `CLASS_ACCIDENT` |
| **Serious Incident(준사고)** | 사고 발생 개연성 높은 사건 | 안전 이격(<5 m) 근접, 추진/항법계 고장 | `CLASS_SERIOUS_INCIDENT` |
| **Incident(이상)** | 운항 안전에 영향을 준 사건 | 해소된 충돌징후, 공역 침범, 완화된 근접(≥5 m) | `CLASS_INCIDENT` |

전체 발생 등급은 사건 중 **가장 중대한 등급**을 채택한다. 근접 사건은
이격거리 임계값(`SERIOUS_SEPARATION_M = 5.0 m`) 기준으로 준사고/이상을 자동 조정한다.

## 3. 발생 분류 코드 (ICAO ADREP)

| 사건 유형 | ADREP 코드 | 의미 |
|---|---|---|
| COLLISION · NEAR_MISS · CONFLICT | `MAC` | Midair Collision / AIRPROX |
| MOTOR_FAILURE · BATTERY_CRITICAL | `SCF-PP` | System/Component Failure – Powerplant |
| GPS_LOSS · COMM_LOSS | `SCF-NP` | System/Component Failure – Non-Powerplant |
| NFZ_INTRUSION | `AIRSPACE` | 공역 침범(Airspace infringement) |

## 4. 입력 데이터 모델

| dataclass | 핵심 필드 |
|---|---|
| `SafetyOccurrence` | 사건 ID·시각(t)·유형·관련 드론 ID·최소 이격거리·상세 |
| `OperationMeta` | 운항 ID·장소·일자·드론 수·시나리오 |
| `ClassifiedOccurrence` | 원 사건 + 부여된 등급 + 분류 코드 + 소견 |

## 5. 출력 구조 (ICAO Annex 13 절 구성)

```
standard                    : "ICAO Annex 13"
occurrence_classification   : 전체 발생 등급 (최중대)
operation                   : 운항 개요
factual_information         : 사건 시간순 목록 (사실 정보)
analysis                    : 등급별·코드별 집계
conclusions                 : 소견(findings) + 최중대 등급
safety_recommendations      : 등장 분류 코드별 결정적 안전 권고
```

## 6. API

```python
from simulation.incident_investigation_report import (
    SafetyOccurrence, OperationMeta, build_investigation_report,
    export_json, export_text,
)

occurrences = [
    SafetyOccurrence("E1", t=10.0, occurrence_type="COLLISION", drone_ids=("D1", "D2")),
    SafetyOccurrence("E2", t=5.0, occurrence_type="NEAR_MISS", separation_m=2.0),
]
meta = OperationMeta("OP-2026-001", "목포 해역", "2026-06-14", drone_count=12)

report = build_investigation_report(occurrences, meta)  # 검증 실패 시 ValueError
print(export_text(report))   # 한국어 보고서
json_str = export_json(report)
```

## 7. 입력 검증 (시스템 경계)

`build_investigation_report` 는 다음을 검증하고 위반 시 `ValueError` 를 발생시킨다:
운항 식별자 공백, 드론 수 ≤ 0, 빈 사건 목록, 미지의 사건 유형, 음수 시각/이격거리,
사건 식별자 중복.

## 8. 5계층 안전망 연계

본 변환기는 안전망 **사후(post-hoc) 분석 계층**에 위치한다. Layer 0(규제·계획)의
[비행계획 신고](../certification/FLIGHT_PLAN_FILING.md)와 대비되며, 운항 중 Layer 1-4가
탐지·기록한 사건을 표준 조사 양식으로 환원해 재발 방지(안전 권고)로 환류한다.
물리적 근본원인 재구성은 [`simulation/collision_forensics.py`](../../simulation/collision_forensics.py)가
담당하며, 본 모듈은 그 결과를 **표준 데이터 교환 양식**으로 정규화하는 책임만 갖는다.
