"""Phase 467 (ODYSSEY · Track 🏛 표준): 사고 조사 데이터 표준 변환기.

시뮬레이션이 기록한 안전 사건(충돌·근접·충돌징후·시스템 고장)을 ICAO Annex 13
(Aircraft Accident and Incident Investigation) 구조의 표준 사고 조사 양식으로
결정적으로 변환한다. Phase 466(텔레메트리 JSON Schema 표준)의 후속으로,
조사 단계의 데이터 교환 표준을 제공한다.

외부 API 호출 없이 입력 검증 + 사건 분류 + 표준 양식 export 만 수행한다.

분류 근거 (ICAO Annex 13 §1 정의):
  - **Accident(사고)**: 실 충돌(기체 손상/멸실) → 최상위 등급
  - **Serious Incident(준사고)**: 안전 이격거리 미만 근접(AIRPROX) 또는
    추진계/항법계 고장 → 사고 발생 개연성 높음
  - **Incident(이상)**: 해소된 충돌징후·공역 침범 등 운항 안전 영향 사건

사건 유형 → ICAO ADREP 발생 분류 코드 매핑:
  COLLISION/NEAR_MISS/CONFLICT → MAC(Midair Collision/AIRPROX)
  MOTOR_FAILURE/BATTERY_CRITICAL → SCF-PP(추진계 고장)
  GPS_LOSS/COMM_LOSS → SCF-NP(비추진계 고장)
  NFZ_INTRUSION → AIRSPACE(공역 침범)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# ICAO Annex 13 발생 등급 (심각도 내림차순)
CLASS_ACCIDENT = "ACCIDENT"
CLASS_SERIOUS_INCIDENT = "SERIOUS_INCIDENT"
CLASS_INCIDENT = "INCIDENT"

# 심각도 순위 (높을수록 중대)
_CLASS_RANK = {
    CLASS_INCIDENT: 1,
    CLASS_SERIOUS_INCIDENT: 2,
    CLASS_ACCIDENT: 3,
}

# 근접 사건이 준사고로 격상되는 이격거리 임계값 (m)
SERIOUS_SEPARATION_M = 5.0

# 사건 유형 → (기본 등급, ADREP 발생 분류 코드)
_OCCURRENCE_TYPES: dict[str, tuple[str, str]] = {
    "COLLISION": (CLASS_ACCIDENT, "MAC"),
    "NEAR_MISS": (CLASS_SERIOUS_INCIDENT, "MAC"),
    "CONFLICT": (CLASS_INCIDENT, "MAC"),
    "MOTOR_FAILURE": (CLASS_SERIOUS_INCIDENT, "SCF-PP"),
    "BATTERY_CRITICAL": (CLASS_SERIOUS_INCIDENT, "SCF-PP"),
    "GPS_LOSS": (CLASS_SERIOUS_INCIDENT, "SCF-NP"),
    "COMM_LOSS": (CLASS_SERIOUS_INCIDENT, "SCF-NP"),
    "NFZ_INTRUSION": (CLASS_INCIDENT, "AIRSPACE"),
}

# 발생 분류 코드 → 표준 안전 권고 (결정적)
_RECOMMENDATIONS: dict[str, str] = {
    "MAC": "충돌 회피 5계층 안전망 임계값·CBS 재계획 주기 재검토",
    "SCF-PP": "추진계·배터리 사전 점검 절차 및 RTB 트리거 전압 상향 검토",
    "SCF-NP": "항법·통신 이중화(GNSS 다중·통신 릴레이) 및 페일세이프 강하 정책 점검",
    "AIRSPACE": "비행금지구역 지오펜스 마진 확대 및 사전 비행계획 검증 강화",
}


@dataclass(frozen=True)
class SafetyOccurrence:
    """시뮬레이션이 기록한 단일 안전 사건."""

    occurrence_id: str
    t: float  # 시뮬 시각 (s)
    occurrence_type: str  # _OCCURRENCE_TYPES 의 키
    drone_ids: tuple[str, ...] = ()
    separation_m: float | None = None  # 근접/충돌 시 최소 이격거리
    detail: str = ""


@dataclass(frozen=True)
class OperationMeta:
    """사건이 발생한 운항(시뮬 시나리오) 메타데이터."""

    operation_id: str
    location: str
    date: str  # ISO 8601 (YYYY-MM-DD)
    drone_count: int
    scenario: str = ""


@dataclass(frozen=True)
class ClassifiedOccurrence:
    """등급·분류 코드가 부여된 사건."""

    occurrence: SafetyOccurrence
    occurrence_class: str
    category_code: str
    findings: tuple[str, ...] = field(default_factory=tuple)


def classify_occurrence(occurrence: SafetyOccurrence) -> ClassifiedOccurrence:
    """단일 사건을 ICAO Annex 13 등급 + ADREP 분류 코드로 결정적 분류한다.

    미지의 사건 유형이면 ``ValueError`` 를 발생시킨다(함수 단독 호출 시에도 안전).
    """
    if occurrence.occurrence_type not in _OCCURRENCE_TYPES:
        raise ValueError(f"알 수 없는 사건 유형: '{occurrence.occurrence_type}'")
    default_class, code = _OCCURRENCE_TYPES[occurrence.occurrence_type]
    occurrence_class = default_class

    findings: list[str] = []
    # 근접 사건은 이격거리에 따라 등급 조정 (임계값 이상이면 이상으로 완화)
    if occurrence.occurrence_type == "NEAR_MISS":
        if occurrence.separation_m is None:
            findings.append("이격 거리 미측정 — 기본값 준사고(Serious Incident) 유지")
        elif occurrence.separation_m >= SERIOUS_SEPARATION_M:
            occurrence_class = CLASS_INCIDENT
            findings.append(
                f"최소 이격 {occurrence.separation_m:.1f} m ≥ "
                f"{SERIOUS_SEPARATION_M:.0f} m → 이상(Incident)으로 분류"
            )
        else:
            findings.append(
                f"최소 이격 {occurrence.separation_m:.1f} m < "
                f"{SERIOUS_SEPARATION_M:.0f} m → 준사고(Serious Incident)"
            )
    if occurrence.occurrence_type == "COLLISION":
        findings.append("실 충돌 발생 — 기체 손상/멸실 가정, 사고(Accident)로 분류")

    return ClassifiedOccurrence(
        occurrence=occurrence,
        occurrence_class=occurrence_class,
        category_code=code,
        findings=tuple(findings),
    )


def _validate(
    occurrences: list[SafetyOccurrence], meta: OperationMeta
) -> list[str]:
    """입력값을 검증하고 오류 목록을 반환한다(시스템 경계 입력 검증)."""
    errors: list[str] = []
    if not meta.operation_id:
        errors.append("운항 식별자(operation_id)가 비어 있음")
    if meta.drone_count <= 0:
        errors.append("드론 수는 0보다 커야 함")
    if not occurrences:
        errors.append("사건 목록이 비어 있음")
    seen_ids: set[str] = set()
    for occ in occurrences:
        if not occ.occurrence_id:
            errors.append("사건 식별자(occurrence_id)가 비어 있음")
        if occ.occurrence_type not in _OCCURRENCE_TYPES:
            errors.append(f"알 수 없는 사건 유형: '{occ.occurrence_type}'")
        if occ.t < 0:
            errors.append(f"사건 시각은 음수일 수 없음: {occ.occurrence_id}")
        if occ.occurrence_id in seen_ids:
            errors.append(f"사건 식별자 중복: '{occ.occurrence_id}'")
        seen_ids.add(occ.occurrence_id)
        if occ.separation_m is not None and occ.separation_m < 0:
            errors.append(f"이격거리는 음수일 수 없음: {occ.occurrence_id}")
    return errors


def _overall_class(classified: list[ClassifiedOccurrence]) -> str:
    """가장 중대한 사건 등급을 전체 발생 등급으로 반환한다."""
    return max(
        (c.occurrence_class for c in classified),
        key=lambda cls: _CLASS_RANK[cls],
    )


def build_investigation_report(
    occurrences: list[SafetyOccurrence], meta: OperationMeta
) -> dict[str, Any]:
    """안전 사건 로그를 ICAO Annex 13 구조의 사고 조사 양식으로 변환한다.

    검증 오류가 있으면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    errors = _validate(occurrences, meta)
    if errors:
        raise ValueError("사고 조사 양식 검증 실패: " + "; ".join(errors))

    classified = [classify_occurrence(o) for o in occurrences]
    # 시각 오름차순(동시각은 식별자 순)으로 정렬한 사건 순서
    timeline = sorted(classified, key=lambda c: (c.occurrence.t, c.occurrence.occurrence_id))

    overall = _overall_class(classified)

    # 분류 코드별 집계
    category_counts: dict[str, int] = {}
    for c in classified:
        category_counts[c.category_code] = category_counts.get(c.category_code, 0) + 1

    # 결정적 안전 권고 (등장한 분류 코드 → 코드 사전순)
    recommendations = [
        _RECOMMENDATIONS[code] for code in sorted(category_counts) if code in _RECOMMENDATIONS
    ]

    return {
        "standard": "ICAO Annex 13",
        "occurrence_classification": overall,
        "operation": {
            "operation_id": meta.operation_id,
            "location": meta.location,
            "date": meta.date,
            "drone_count": meta.drone_count,
            "scenario": meta.scenario,
        },
        "factual_information": [
            {
                "occurrence_id": c.occurrence.occurrence_id,
                "t": round(c.occurrence.t, 3),
                "type": c.occurrence.occurrence_type,
                "category_code": c.category_code,
                "classification": c.occurrence_class,
                "drone_ids": list(c.occurrence.drone_ids),
                "separation_m": (
                    round(c.occurrence.separation_m, 2)
                    if c.occurrence.separation_m is not None
                    else None
                ),
                "detail": c.occurrence.detail,
            }
            for c in timeline
        ],
        "analysis": {
            "total_occurrences": len(classified),
            "by_category": dict(sorted(category_counts.items())),
            "by_classification": {
                cls: sum(1 for c in classified if c.occurrence_class == cls)
                for cls in (CLASS_ACCIDENT, CLASS_SERIOUS_INCIDENT, CLASS_INCIDENT)
            },
        },
        "conclusions": {
            "findings": [
                f"{c.occurrence.occurrence_id}: {finding}"
                for c in timeline
                for finding in c.findings
            ],
            "most_severe": overall,
        },
        "safety_recommendations": recommendations,
    }


def export_json(report: dict[str, Any]) -> str:
    """조사 양식을 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


_CLASS_LABEL_KO = {
    CLASS_ACCIDENT: "사고(Accident)",
    CLASS_SERIOUS_INCIDENT: "준사고(Serious Incident)",
    CLASS_INCIDENT: "이상(Incident)",
}


def export_text(report: dict[str, Any]) -> str:
    """조사 양식을 사람이 읽는 한국어 보고서 텍스트로 변환한다."""
    op = report["operation"]
    an = report["analysis"]
    lines = [
        "═══ ICAO Annex 13 사고 조사 보고서 ═══",
        "",
        f"[발생 등급] {_CLASS_LABEL_KO.get(report['occurrence_classification'], report['occurrence_classification'])}",
        "",
        "[운항 개요]",
        f"  운항 ID:  {op['operation_id']}",
        f"  장소:     {op['location']}",
        f"  일자:     {op['date']}",
        f"  드론 수:  {op['drone_count']}",
    ]
    if op["scenario"]:
        lines.append(f"  시나리오: {op['scenario']}")
    lines += [
        "",
        "[사실 정보 — 사건 순서]",
    ]
    for item in report["factual_information"]:
        sep = (
            f" / 이격 {item['separation_m']} m"
            if item["separation_m"] is not None
            else ""
        )
        drones = ", ".join(item["drone_ids"]) if item["drone_ids"] else "-"
        lines.append(
            f"  t={item['t']:>7.1f}s  {item['type']:<16} "
            f"[{item['category_code']}] {item['classification']}{sep}  ({drones})"
        )
    lines += [
        "",
        "[분석]",
        f"  총 사건:  {an['total_occurrences']}",
        f"  분류별:   {an['by_classification']}",
        f"  코드별:   {an['by_category']}",
        "",
        "[안전 권고]",
    ]
    if report["safety_recommendations"]:
        lines += [f"  - {r}" for r in report["safety_recommendations"]]
    else:
        lines.append("  - (없음)")
    return "\n".join(lines)
