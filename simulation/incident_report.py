"""Phase 307 (GENESIS): 사고 보고 양식 자동 작성 — 시뮬 사고 로그 → 항철위 표준 보고서.

한국 「항공·철도 사고조사에 관한 법률」 및 「항공안전법」 제59조(항공안전 의무보고)에
따른 항공·철도사고조사위원회(ARAIB) 표준 발생 보고 양식을, 시뮬레이션 사고 로그로부터
결정적으로 생성한다. 외부 API 호출 없이 발생 등급 분류 + 의무보고 판정 +
JSON/텍스트 양식 export 만 수행한다 (production 등급의 결정적 구현).

발생 등급(분류 근거 — 항공안전법 시행규칙 별표):
  - 사고(ACCIDENT): 사망/중상자 발생, 기체 파괴, 또는 중대 물적 피해를 동반한 충돌
  - 준사고(SERIOUS_INCIDENT): 충돌, 복구되지 않은 통제 상실 등 사고로 이어질 뻔한 상황
  - 항공안전장애(OCCURRENCE): GPS 상실·통신 두절·배터리 임계 등 경미한 안전 영향 사항

의무보고 시한:
  - 사고/준사고: 인지 즉시 보고
  - 항공안전장애: 발생 후 72시간 이내 보고
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# 발생 등급 식별자
ACCIDENT = "사고"
SERIOUS_INCIDENT = "준사고"
OCCURRENCE = "항공안전장애"

# 사고 등급 격상을 일으키는 물적 피해 임계값 (원)
SUBSTANTIAL_DAMAGE_KRW = 10_000_000.0

# 의무보고 시한 (시간)
ACCIDENT_REPORT_DEADLINE_H = 0  # 즉시
OCCURRENCE_REPORT_DEADLINE_H = 72

# 사고 로그 이벤트 유형 라벨
EVENT_TYPE_LABELS: dict[str, str] = {
    "collision": "공중/지상 충돌",
    "loss_of_control": "통제 상실",
    "forced_landing": "비상 착륙",
    "near_miss": "근접(분리 최저치 미달)",
    "gps_loss": "GPS 신호 상실",
    "comm_loss": "통신 두절",
    "battery_critical": "배터리 임계 방전",
    "geofence_breach": "비행구역 이탈",
}


@dataclass(frozen=True)
class IncidentEvent:
    """시뮬레이션이 기록한 단일 사고/장애 이벤트."""

    timestamp: datetime
    drone_id: str
    event_type: str
    lat: float
    lon: float
    altitude_agl_m: float
    description: str = ""
    casualties: int = 0  # 사망/중상자 수
    is_aircraft_destroyed: bool = False
    recovered: bool = True  # 자동 복구(안전망) 성공 여부
    property_damage_krw: float = 0.0


@dataclass(frozen=True)
class Operator:
    """보고 의무자(운영자/사용사업자) 정보."""

    name: str
    contact: str
    organization: str = ""


@dataclass(frozen=True)
class OccurrenceAssessment:
    """발생 등급 분류 결과."""

    occurrence_class: str
    is_mandatory_report: bool
    report_deadline_h: int
    reasons: tuple[str, ...] = ()


def classify_occurrence(event: IncidentEvent) -> OccurrenceAssessment:
    """사고 로그 이벤트의 발생 등급(사고/준사고/안전장애)을 결정적으로 분류한다."""
    reasons: list[str] = []

    is_accident = False
    is_serious = False

    if event.casualties > 0:
        is_accident = True
        reasons.append(f"인명 피해(사망/중상) {event.casualties}명 발생")
    if event.is_aircraft_destroyed:
        is_accident = True
        reasons.append("기체 파괴")
    if event.property_damage_krw >= SUBSTANTIAL_DAMAGE_KRW:
        is_accident = True
        reasons.append(
            f"중대 물적 피해 {event.property_damage_krw:,.0f}원"
            f" (≥ {SUBSTANTIAL_DAMAGE_KRW:,.0f}원)"
        )

    if event.event_type == "collision":
        if is_accident:
            reasons.append("충돌 + 사고 요건 동반")
        else:
            is_serious = True
            reasons.append("충돌 발생 — 준사고 요건")
    elif event.event_type in ("loss_of_control", "forced_landing"):
        if not event.recovered:
            is_serious = True
            label = EVENT_TYPE_LABELS[event.event_type]
            reasons.append(f"{label} 후 미복구 — 준사고 요건")
        else:
            reasons.append(
                f"{EVENT_TYPE_LABELS[event.event_type]} 발생 후 안전망 복구"
            )

    if is_accident:
        occurrence_class = ACCIDENT
    elif is_serious:
        occurrence_class = SERIOUS_INCIDENT
    else:
        occurrence_class = OCCURRENCE
        if not reasons:
            label = EVENT_TYPE_LABELS.get(event.event_type, event.event_type)
            reasons.append(f"{label} — 항공안전장애 분류")

    mandatory = occurrence_class in (ACCIDENT, SERIOUS_INCIDENT)
    deadline = (
        ACCIDENT_REPORT_DEADLINE_H if mandatory else OCCURRENCE_REPORT_DEADLINE_H
    )
    return OccurrenceAssessment(
        occurrence_class=occurrence_class,
        is_mandatory_report=mandatory,
        report_deadline_h=deadline,
        reasons=tuple(reasons),
    )


def _report_no(event: IncidentEvent) -> str:
    """타임스탬프와 기체 ID로 결정적 보고번호를 생성한다."""
    return f"ARAIB-{event.timestamp:%Y%m%d-%H%M%S}-{event.drone_id}"


def _validate(event: IncidentEvent, operator: Operator) -> list[str]:
    """필수 입력값을 검증하고 누락/오류 목록을 반환한다."""
    errors: list[str] = []
    if not event.drone_id:
        errors.append("기체 ID가 비어 있음")
    if event.event_type not in EVENT_TYPE_LABELS:
        errors.append(f"알 수 없는 이벤트 유형: {event.event_type}")
    if event.casualties < 0:
        errors.append("인명 피해 수는 음수가 될 수 없음")
    if event.property_damage_krw < 0:
        errors.append("물적 피해액은 음수가 될 수 없음")
    if not operator.name:
        errors.append("보고 의무자 성명이 비어 있음")
    if not operator.contact:
        errors.append("보고 의무자 연락처가 비어 있음")
    return errors


def build_report(event: IncidentEvent, operator: Operator) -> dict[str, Any]:
    """ARAIB 표준 발생 보고 양식 데이터를 결정적으로 구성한다.

    검증 오류가 있으면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    errors = _validate(event, operator)
    if errors:
        raise ValueError("사고 보고 양식 검증 실패: " + "; ".join(errors))

    assessment = classify_occurrence(event)
    return {
        "form_type": "araib_occurrence_report",
        "report_no": _report_no(event),
        "operator": {
            "name": operator.name,
            "contact": operator.contact,
            "organization": operator.organization,
        },
        "occurrence": {
            "timestamp": event.timestamp.isoformat(),
            "drone_id": event.drone_id,
            "event_type": event.event_type,
            "event_label": EVENT_TYPE_LABELS[event.event_type],
            "location": [round(event.lat, 6), round(event.lon, 6)],
            "altitude_agl_m": round(event.altitude_agl_m, 1),
            "description": event.description,
            "casualties": event.casualties,
            "is_aircraft_destroyed": event.is_aircraft_destroyed,
            "recovered": event.recovered,
            "property_damage_krw": round(event.property_damage_krw, 0),
        },
        "assessment": {
            "occurrence_class": assessment.occurrence_class,
            "is_mandatory_report": assessment.is_mandatory_report,
            "report_deadline_h": assessment.report_deadline_h,
            "reasons": list(assessment.reasons),
        },
    }


def summarize_log(events: list[IncidentEvent]) -> dict[str, Any]:
    """사고 로그 전체를 발생 등급별로 집계하고 의무보고 건수를 반환한다."""
    counts = {ACCIDENT: 0, SERIOUS_INCIDENT: 0, OCCURRENCE: 0}
    mandatory = 0
    for event in events:
        assessment = classify_occurrence(event)
        counts[assessment.occurrence_class] += 1
        if assessment.is_mandatory_report:
            mandatory += 1
    return {
        "total": len(events),
        "by_class": counts,
        "mandatory_reports": mandatory,
    }


def export_json(report: dict[str, Any]) -> str:
    """보고서 데이터를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(report: dict[str, Any]) -> str:
    """보고서 데이터를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    op = report["operator"]
    oc = report["occurrence"]
    asm = report["assessment"]
    deadline = (
        "인지 즉시"
        if asm["report_deadline_h"] == 0
        else f"{asm['report_deadline_h']}시간 이내"
    )
    lines = [
        "═══ 항공·철도사고조사위원회(ARAIB) 발생 보고서 ═══",
        "",
        f"보고번호: {report['report_no']}",
        "",
        "[보고 의무자]",
        f"  성명/업체: {op['name']}",
        f"  연락처:    {op['contact']}",
    ]
    if op["organization"]:
        lines.append(f"  소속:      {op['organization']}")
    lines += [
        "",
        "[발생 개요]",
        f"  일시:      {oc['timestamp']}",
        f"  기체:      {oc['drone_id']}",
        f"  유형:      {oc['event_label']} ({oc['event_type']})",
        f"  위치:      {oc['location'][0]}, {oc['location'][1]}"
        f" / 고도 {oc['altitude_agl_m']} m AGL",
        f"  인명피해:  {oc['casualties']}명",
        f"  기체파괴:  {'예' if oc['is_aircraft_destroyed'] else '아니오'}",
        f"  복구여부:  {'복구됨' if oc['recovered'] else '미복구'}",
        f"  물적피해:  {oc['property_damage_krw']:,.0f}원",
    ]
    if oc["description"]:
        lines.append(f"  경위:      {oc['description']}")
    lines += [
        "",
        "[판정]",
        f"  발생 등급: {asm['occurrence_class']}",
        f"  의무보고:  {'대상' if asm['is_mandatory_report'] else '비대상'}",
        f"  보고 시한: {deadline}",
    ]
    if asm["reasons"]:
        lines.append("  분류 사유:")
        lines += [f"   - {r}" for r in asm["reasons"]]
    return "\n".join(lines)
