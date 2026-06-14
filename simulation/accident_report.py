"""Phase 307 (GENESIS): 사고 보고 양식 자동 작성 — 시뮬 사고 로그 → ARAIB 표준 보고서.

한국 「항공·철도 사고조사에 관한 법률」 및 「항공안전법」 §2(정의)·§62(사고 보고)에 따른
항공·철도사고조사위원회(ARAIB) 표준 사고 보고 양식을, SDACS 시뮬레이션의 사고 로그
(드론 간 분리거리·충돌 여부·피해)로부터 결정적으로 생성한다. 외부 API 호출 없이
사건 분류(사고/준사고/안전장애) + 보고서 구성 + JSON/텍스트 export 만 수행한다.

분류 근거(결정적):
  - 충돌 접촉(분리거리 ≤ 5 m) 또는 인명 피해 또는 기체 중대/전파 손상 → 초경량비행장치사고
  - 충돌은 없으나 분리거리 < 10 m (근접) → 항공기준사고(준사고)
  - 그 외 보고된 안전 저해 사건 → 항공안전장애
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# 분류 임계값 (config/default_simulation.yaml separation_standards 정렬)
CONTACT_SEPARATION_M = 5.0  # 이 거리 이하 = 물리적 충돌(접촉)로 간주
NEAR_MISS_SEPARATION_M = 10.0  # 충돌은 아니나 근접(준사고) 판정 임계


class OccurrenceCategory(Enum):
    """ARAIB 사건 분류 (항공안전법 §2 정의 기반)."""

    ACCIDENT = "초경량비행장치사고"
    SERIOUS_INCIDENT = "항공기준사고"
    SAFETY_OCCURRENCE = "항공안전장애"


class DamageLevel(Enum):
    """기체 손상 등급 (ICAO Annex 13 정렬)."""

    NONE = "없음"
    MINOR = "경미"
    SUBSTANTIAL = "중대"
    DESTROYED = "전파"


@dataclass(frozen=True)
class InvolvedDrone:
    """사고에 관련된 기체."""

    drone_id: str
    model: str
    operator: str
    registration_no: str = ""  # 신고번호 (미신고 시 빈 문자열)


@dataclass(frozen=True)
class OccurrenceRecord:
    """시뮬레이션 사고 로그로부터 구성된 사건 기록.

    ``min_separation_m`` 은 사건 시점의 최소 분리거리, ``made_contact`` 는 물리적
    접촉(충돌) 여부다. 둘 중 하나만 주어지면 다른 하나는 임계값으로부터 보정된다.
    """

    occurrence_id: str
    timestamp: datetime
    lat: float
    lon: float
    altitude_m: float
    drones: tuple[InvolvedDrone, ...]
    min_separation_m: float
    made_contact: bool = False
    injuries: int = 0
    damage: DamageLevel = DamageLevel.NONE
    narrative: str = ""
    contributing_factors: tuple[str, ...] = ()
    sequence: tuple[str, ...] = field(default_factory=tuple)  # 시계열 사실 정보


@dataclass(frozen=True)
class OccurrenceClassification:
    """사건 분류 판정 결과."""

    category: OccurrenceCategory
    is_reportable: bool  # 국토부 보고 의무 대상 여부
    reasons: tuple[str, ...] = ()


def _is_contact(record: OccurrenceRecord) -> bool:
    """명시적 접촉 플래그 또는 분리거리 임계값으로 충돌 접촉 여부를 판정한다."""
    return record.made_contact or record.min_separation_m <= CONTACT_SEPARATION_M


def classify_occurrence(record: OccurrenceRecord) -> OccurrenceClassification:
    """사건을 사고/준사고/안전장애로 결정적으로 분류한다.

    충돌 접촉·인명 피해·기체 손상 등급·최소 분리거리를 종합한다.
    """
    reasons: list[str] = []
    contact = _is_contact(record)
    severe_damage = record.damage in (DamageLevel.SUBSTANTIAL, DamageLevel.DESTROYED)

    if contact or record.injuries > 0 or severe_damage:
        category = OccurrenceCategory.ACCIDENT
        if contact:
            reasons.append(
                f"물리적 충돌 접촉 (최소 분리 {record.min_separation_m:.1f} m)"
            )
        if record.injuries > 0:
            reasons.append(f"인명 피해 {record.injuries}명")
        if severe_damage:
            reasons.append(f"기체 손상 등급 '{record.damage.value}'")
    elif record.min_separation_m < NEAR_MISS_SEPARATION_M:
        category = OccurrenceCategory.SERIOUS_INCIDENT
        reasons.append(
            f"근접(준사고) — 최소 분리 {record.min_separation_m:.1f} m가 "
            f"{NEAR_MISS_SEPARATION_M:.0f} m 미만"
        )
    else:
        category = OccurrenceCategory.SAFETY_OCCURRENCE
        reasons.append(
            f"안전장애 — 최소 분리 {record.min_separation_m:.1f} m (충돌·근접 아님)"
        )

    # 사고·준사고는 국토부 보고 의무 대상
    is_reportable = category in (
        OccurrenceCategory.ACCIDENT,
        OccurrenceCategory.SERIOUS_INCIDENT,
    )
    return OccurrenceClassification(
        category=category,
        is_reportable=is_reportable,
        reasons=tuple(reasons),
    )


def occurrence_from_log(
    occurrence_id: str,
    timestamp: datetime,
    lat: float,
    lon: float,
    altitude_m: float,
    drones: tuple[InvolvedDrone, ...],
    separation_log: list[float],
    *,
    injuries: int = 0,
    damage: DamageLevel = DamageLevel.NONE,
    narrative: str = "",
    contributing_factors: tuple[str, ...] = (),
) -> OccurrenceRecord:
    """시뮬 분리거리 시계열 로그로부터 사건 기록을 구성한다.

    ``separation_log`` 의 최소값으로 최소 분리거리와 접촉 여부를 도출한다.
    """
    if not separation_log:
        raise ValueError("분리거리 로그가 비어 있음")
    min_sep = min(separation_log)
    return OccurrenceRecord(
        occurrence_id=occurrence_id,
        timestamp=timestamp,
        lat=lat,
        lon=lon,
        altitude_m=altitude_m,
        drones=drones,
        min_separation_m=min_sep,
        made_contact=min_sep <= CONTACT_SEPARATION_M,
        injuries=injuries,
        damage=damage,
        narrative=narrative,
        contributing_factors=contributing_factors,
    )


def _validate(record: OccurrenceRecord) -> list[str]:
    """필수 입력값을 검증하고 누락/오류 목록을 반환한다."""
    errors: list[str] = []
    if not record.occurrence_id:
        errors.append("사건 식별번호가 비어 있음")
    if not record.drones:
        errors.append("관련 기체가 하나 이상 필요함")
    if record.min_separation_m < 0:
        errors.append("최소 분리거리는 음수일 수 없음")
    if record.altitude_m < 0:
        errors.append("고도는 음수일 수 없음")
    if record.injuries < 0:
        errors.append("인명 피해 수는 음수일 수 없음")
    return errors


def _safety_recommendations(category: OccurrenceCategory) -> tuple[str, ...]:
    """분류 등급에 따른 결정적 안전권고를 반환한다."""
    if category is OccurrenceCategory.ACCIDENT:
        return (
            "사고 기체 비행 중지 및 정비/원인 규명 완료 전 재투입 금지",
            "5계층 안전망 Layer 4(긴급 회피) 로그 재현 분석 수행",
            "동일 시나리오 회귀 테스트 추가로 재발 방지 검증",
        )
    if category is OccurrenceCategory.SERIOUS_INCIDENT:
        return (
            "분리거리 최소기준(측면 50 m) 위반 구간 경로 재계획 검토",
            "CPA 예측 선행시간(lookahead) 상향 조정 타당성 평가",
        )
    return (
        "운영 절차 점검 및 관제 로그 정기 검토",
    )


def build_report(
    record: OccurrenceRecord,
    *,
    reporter: str,
    report_no: str = "",
) -> dict[str, Any]:
    """ARAIB 표준 사고 보고서 데이터를 결정적으로 구성한다.

    검증 오류가 있으면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    if not reporter:
        raise ValueError("보고자(reporter)가 비어 있음")
    errors = _validate(record)
    if errors:
        raise ValueError("사고 보고서 검증 실패: " + "; ".join(errors))

    classification = classify_occurrence(record)
    return {
        "form_type": "araib_occurrence_report",
        "report_no": report_no or f"SDACS-{record.occurrence_id}",
        "reporter": reporter,
        "classification": {
            "category": classification.category.value,
            "is_reportable": classification.is_reportable,
            "reasons": list(classification.reasons),
        },
        "occurrence": {
            "id": record.occurrence_id,
            "timestamp": record.timestamp.isoformat(),
            "location": [round(record.lat, 6), round(record.lon, 6)],
            "altitude_m": round(record.altitude_m, 1),
            "min_separation_m": round(record.min_separation_m, 2),
            "made_contact": _is_contact(record),
        },
        "damage_and_injury": {
            "injuries": record.injuries,
            "damage": record.damage.value,
        },
        "involved": [
            {
                "drone_id": d.drone_id,
                "model": d.model,
                "operator": d.operator,
                "registration_no": d.registration_no or "(미신고)",
            }
            for d in record.drones
        ],
        "factual": {
            "narrative": record.narrative,
            "sequence": list(record.sequence),
            "contributing_factors": list(record.contributing_factors),
        },
        "recommendations": list(_safety_recommendations(classification.category)),
    }


def export_json(report: dict[str, Any]) -> str:
    """보고서 데이터를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(report: dict[str, Any]) -> str:
    """보고서 데이터를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    c = report["classification"]
    o = report["occurrence"]
    di = report["damage_and_injury"]
    f = report["factual"]
    lines = [
        "═══ 항공·철도사고조사위원회(ARAIB) 사고 보고서 ═══",
        "",
        f"  보고번호:  {report['report_no']}",
        f"  보고자:    {report['reporter']}",
        "",
        "[분류]",
        f"  사건 등급: {c['category']}",
        f"  보고 의무: {'대상' if c['is_reportable'] else '비대상'}",
    ]
    if c["reasons"]:
        lines.append("  판정 사유:")
        lines += [f"   - {r}" for r in c["reasons"]]
    lines += [
        "",
        "[사건 개요]",
        f"  식별번호:  {o['id']}",
        f"  일시:      {o['timestamp']}",
        f"  위치:      {o['location'][0]}, {o['location'][1]} / 고도 {o['altitude_m']} m",
        f"  최소분리:  {o['min_separation_m']} m (접촉 {'예' if o['made_contact'] else '아니오'})",
        "",
        "[피해]",
        f"  인명:      {di['injuries']}명",
        f"  기체손상:  {di['damage']}",
        "",
        "[관련 기체]",
    ]
    for d in report["involved"]:
        lines.append(
            f"   - {d['drone_id']} ({d['model']}, 운영 {d['operator']}, "
            f"신고 {d['registration_no']})"
        )
    lines += ["", "[사실 정보]"]
    if f["narrative"]:
        lines.append(f"  경위:      {f['narrative']}")
    if f["sequence"]:
        lines.append("  시계열:")
        lines += [f"   - {s}" for s in f["sequence"]]
    if f["contributing_factors"]:
        lines.append("  기여요인:")
        lines += [f"   - {cf}" for cf in f["contributing_factors"]]
    lines += ["", "[안전권고]"]
    lines += [f"   - {r}" for r in report["recommendations"]]
    return "\n".join(lines)
