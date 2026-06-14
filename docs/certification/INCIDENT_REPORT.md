# 🚨 사고 보고 양식 자동 작성 (GENESIS Phase 307)

*Created: 2026-06-14 · 근거: 「항공·철도 사고조사에 관한 법률」, 「항공안전법」 §59(항공안전 의무보고), 시행규칙 별표(항공기사고·준사고·항공안전장애 범위)*
*면책: 본 문서·모듈은 시뮬레이션 사고 로그로부터 발생 보고서 초안을 결정적으로 생성하는 보조 도구이며, 실 운영자는 최신 고시와 국토교통부 항공·철도사고조사위원회(ARAIB)의 실제 보고 절차를 따라야 한다.*

---

## 1. 목적

SDACS 시뮬레이션이 기록한 사고/장애 이벤트(충돌·통제 상실·GPS 상실·통신 두절·배터리 임계 등)를
입력받아, ARAIB 표준 발생 보고서 데이터를 결정적으로 구성하고 **사고 / 준사고 / 항공안전장애**
발생 등급과 **의무보고 대상 여부·보고 시한**을 자동 판정한다. 외부 API 호출 없이 입력 검증과
양식 export(JSON·텍스트)만 수행한다.

구현: [`simulation/incident_report.py`](../../simulation/incident_report.py)
테스트: [`tests/test_incident_report.py`](../../tests/test_incident_report.py) — **19건 PASS**

## 2. 발생 등급 분류 규칙

| 등급 | 식별자 | 조건 | 보고 시한 |
|---|---|---|---|
| 사고 | `ACCIDENT` | 사망/중상자 발생, 기체 파괴, 또는 중대 물적 피해(≥ 1,000만원) 동반 | 인지 즉시 |
| 준사고 | `SERIOUS_INCIDENT` | 충돌, 복구되지 않은 통제 상실·비상 착륙 | 인지 즉시 |
| 항공안전장애 | `OCCURRENCE` | GPS 상실·통신 두절·배터리 임계·근접·구역 이탈 등 경미한 안전 영향 | 발생 후 72시간 이내 |

분류는 `classify_occurrence()` 가 결정적으로 수행한다. 인명/기체/물적 요건이 충족되면
이벤트 유형과 무관하게 **사고**로 격상되고, 충돌·미복구 통제 상실은 **준사고**, 그 외는
**항공안전장애**로 분류된다.

## 3. 이벤트 유형

`collision`(충돌) · `loss_of_control`(통제 상실) · `forced_landing`(비상 착륙) ·
`near_miss`(근접) · `gps_loss`(GPS 상실) · `comm_loss`(통신 두절) ·
`battery_critical`(배터리 임계) · `geofence_breach`(구역 이탈)

## 4. API

| 함수 | 반환 | 설명 |
|---|---|---|
| `classify_occurrence(event)` | `OccurrenceAssessment` | 발생 등급·의무보고·보고 시한·사유 |
| `build_report(event, operator)` | `dict` | ARAIB 표준 보고서 데이터(결정적, 입력 검증 `ValueError`) |
| `summarize_log(events)` | `dict` | 로그 전체 등급별 집계 + 의무보고 건수 |
| `export_json(report)` | `str` | UTF-8 JSON 직렬화 |
| `export_text(report)` | `str` | 한국어 양식 텍스트 |

보고번호는 `ARAIB-{YYYYMMDD-HHMMSS}-{drone_id}` 형식으로 결정적으로 생성된다.

## 5. 5계층 안전망 연계

`recovered` 플래그는 SDACS 5계층 안전망(예측·회피·격리·복구·보고)이 사고를 **복구**했는지를
나타낸다. 안전망이 통제 상실을 복구하면 준사고에서 항공안전장애로 등급이 낮아지며, 보고서의
`reasons` 에 "안전망 복구"가 기록된다 — 시뮬레이션의 안전망 성능이 규제 보고 부담에 직접
연결됨을 보여준다. `summarize_log()` 는 시나리오 1회 실행의 전체 사고 로그를 등급별로 집계해
의무보고 건수를 산출한다.
