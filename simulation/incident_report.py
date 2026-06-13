"""사고 보고서 자동 생성 (GENESIS Phase 307).

시뮬레이션 분석 이벤트(``SimulationAnalytics.events``)를 항공·철도사고조사위원회
(ARAIB) 사건 분류 체계에 따라 정리한 사고 보고서 초안을 생성한다. 항공안전법
시행규칙의 사건 등급 — 항공기사고 / 항공기준사고 / 항공안전장애 — 에 매핑한다.

매핑 근거:
- ``COLLISION``            → 항공기사고     (기체 충돌·파손)
- ``NEAR_MISS``            → 항공기준사고   (위험 근접·분리 상실)
- ``FAILURE_INJECTED``     → 항공안전장애   (기체/시스템 고장)
- ``COMMS_LOSS_INJECTED``  → 항공안전장애   (통신 두절·Lost-link)

``CONFLICT``·``ADVISORY_ISSUED`` 등 정상 운영 중 발생하는 충돌 예측·조정 이벤트는
보고 대상이 아니므로 제외한다.

주의: 본 보고서는 시뮬레이션 로그에서 자동 추출한 *초안*이며, 실제 사건 조사나
법정 보고를 대체하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class IncidentCategory(Enum):
    """항철위 사건 등급. 값은 보고서 표기용 한국어 명칭."""

    ACCIDENT = "항공기사고"
    SERIOUS_INCIDENT = "항공기준사고"
    SAFETY_OCCURRENCE = "항공안전장애"


# 이벤트 유형 → 사건 등급. 미수록 유형은 보고 대상이 아니다(정상 운영 이벤트).
_EVENT_CLASSIFICATION: dict[str, IncidentCategory] = {
    "COLLISION": IncidentCategory.ACCIDENT,
    "NEAR_MISS": IncidentCategory.SERIOUS_INCIDENT,
    "FAILURE_INJECTED": IncidentCategory.SAFETY_OCCURRENCE,
    "COMMS_LOSS_INJECTED": IncidentCategory.SAFETY_OCCURRENCE,
}

# 보고서 표기 시 등급 출력 순서 (중대도 내림차순)
_CATEGORY_ORDER: tuple[IncidentCategory, ...] = (
    IncidentCategory.ACCIDENT,
    IncidentCategory.SERIOUS_INCIDENT,
    IncidentCategory.SAFETY_OCCURRENCE,
)


def classify_event(event_type: str) -> IncidentCategory | None:
    """이벤트 유형을 항철위 사건 등급으로 분류한다(보고 대상이 아니면 ``None``)."""
    return _EVENT_CLASSIFICATION.get(event_type)


@dataclass(frozen=True)
class IncidentRecord:
    """보고서의 사건 1건."""

    sequence: int  # 사건 일련번호 (시간순 1-based)
    time_s: float  # 발생 시각 (시뮬레이션 경과 초)
    category: IncidentCategory
    event_type: str
    involved: tuple[str, ...]  # 관련 드론 ID
    summary: str  # 한 줄 경위
    detail: dict  # 원본 이벤트 메타데이터

    def to_dict(self) -> dict:
        """직렬화용 사전으로 변환한다."""
        return {
            "sequence": self.sequence,
            "time_s": self.time_s,
            "category": self.category.value,
            "event_type": self.event_type,
            "involved": list(self.involved),
            "summary": self.summary,
            "detail": self.detail,
        }


def _summarize(event: dict) -> tuple[tuple[str, ...], str]:
    """이벤트에서 (관련 드론 튜플, 한 줄 경위)를 추출한다."""
    etype = event["type"]

    if etype == "COLLISION":
        a, b = event.get("drone_a", "?"), event.get("drone_b", "?")
        dist = float(event.get("dist_m", 0.0))
        alt_a = float(event.get("alt_a_m", 0.0))
        alt_b = float(event.get("alt_b_m", 0.0))
        phase_a = event.get("phase_a", "?")
        phase_b = event.get("phase_b", "?")
        summary = (
            f"{a}·{b} 충돌 (이격 {dist:.1f} m, 고도 {alt_a:.0f}/{alt_b:.0f} m, "
            f"단계 {phase_a}/{phase_b})"
        )
        return (a, b), summary

    if etype == "NEAR_MISS":
        a, b = event.get("drone_a", "?"), event.get("drone_b", "?")
        dist = float(event.get("dist_m", 0.0))
        return (a, b), f"{a}·{b} 위험 근접 (이격 {dist:.1f} m)"

    if etype == "FAILURE_INJECTED":
        did = event.get("drone_id", "?")
        ftype = event.get("failure_type", "UNKNOWN")
        return (did,), f"{did} 기체 고장 ({ftype})"

    if etype == "COMMS_LOSS_INJECTED":
        did = event.get("drone_id", "?")
        return (did,), f"{did} 통신 두절 (Lost-link)"

    # 분류표에 있으나 위에서 처리되지 않은 유형 — 방어적 일반 경위
    did = event.get("drone_id", "?")
    return (did,), f"{did} {etype}"


@dataclass(frozen=True)
class IncidentReport:
    """사고 보고서 초안 (시간순 정렬된 사건 목록 + 메타데이터)."""

    scenario: str
    seed: int
    duration_s: float
    records: tuple[IncidentRecord, ...]
    generated_at: str

    @property
    def category_counts(self) -> dict[IncidentCategory, int]:
        """등급별 사건 수 (0건 등급도 포함)."""
        counts = {cat: 0 for cat in _CATEGORY_ORDER}
        for rec in self.records:
            counts[rec.category] += 1
        return counts

    def to_dict(self) -> dict:
        """직렬화용 사전으로 변환한다."""
        return {
            "scenario": self.scenario,
            "seed": self.seed,
            "duration_s": self.duration_s,
            "generated_at": self.generated_at,
            "category_counts": {
                cat.value: cnt for cat, cnt in self.category_counts.items()
            },
            "records": [rec.to_dict() for rec in self.records],
        }

    def to_markdown(self) -> str:
        """항철위 보고서 양식 기반 Markdown 문서를 생성한다."""
        lines: list[str] = [
            "# 무인비행장치 사고 보고서 (초안)",
            "",
            "> 본 보고서는 SDACS 시뮬레이션 로그에서 자동 추출한 **초안**이며, "
            "실제 사건 조사·법정 보고(항공안전법 제59조·제62조)를 대체하지 않습니다.",
            "",
            "## 1. 개요",
            "",
            "| 항목 | 값 |",
            "|---|---|",
            f"| 시나리오 | {self.scenario} |",
            f"| 시드 | {self.seed} |",
            f"| 시뮬레이션 시간 | {self.duration_s:.0f} s |",
            f"| 작성 시각 | {self.generated_at} |",
            f"| 총 보고 대상 사건 | {len(self.records)} 건 |",
            "",
            "## 2. 사건 등급 요약 (항철위 분류)",
            "",
            "| 등급 | 건수 |",
            "|---|---|",
        ]
        counts = self.category_counts
        for cat in _CATEGORY_ORDER:
            lines.append(f"| {cat.value} | {counts[cat]} |")
        lines.append("")

        if not self.records:
            lines.append("## 3. 사건 상세")
            lines.append("")
            lines.append("보고 대상 사건 없음 — 시뮬레이션 중 충돌·준사고·안전장애 미발생.")
            lines.append("")
            return "\n".join(lines)

        lines.append("## 3. 사건 상세")
        lines.append("")
        for cat in _CATEGORY_ORDER:
            cat_records = [r for r in self.records if r.category == cat]
            if not cat_records:
                continue
            lines.append(f"### {cat.value} ({len(cat_records)}건)")
            lines.append("")
            lines.append("| 순번 | 시각(s) | 관련 드론 | 경위 |")
            lines.append("|---|---|---|---|")
            for rec in cat_records:
                involved = ", ".join(rec.involved)
                lines.append(
                    f"| {rec.sequence} | {rec.time_s:.1f} | {involved} | {rec.summary} |"
                )
            lines.append("")
        return "\n".join(lines)


def build_incident_report(
    events: list[dict],
    *,
    scenario: str = "default",
    seed: int = 0,
    duration_s: float = 0.0,
    generated_at: str | None = None,
) -> IncidentReport:
    """분석 이벤트 목록에서 사고 보고서 초안을 생성한다.

    보고 대상 이벤트만 추려 발생 시각 순으로 정렬하고, 1-based 일련번호를 부여한다.
    """
    reportable = [ev for ev in events if classify_event(ev.get("type", "")) is not None]
    reportable.sort(key=lambda ev: float(ev.get("t", 0.0)))

    records: list[IncidentRecord] = []
    for seq, ev in enumerate(reportable, start=1):
        category = classify_event(ev["type"])
        assert category is not None  # reportable 필터로 보장됨
        involved, summary = _summarize(ev)
        records.append(
            IncidentRecord(
                sequence=seq,
                time_s=float(ev.get("t", 0.0)),
                category=category,
                event_type=ev["type"],
                involved=involved,
                summary=summary,
                detail={k: v for k, v in ev.items() if k != "type"},
            )
        )

    return IncidentReport(
        scenario=scenario,
        seed=seed,
        duration_s=duration_s,
        records=tuple(records),
        generated_at=generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
