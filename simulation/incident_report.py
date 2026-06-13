"""GENESIS Phase 307 + ODYSSEY Phase 467 — 사고 보고 / 사고조사 데이터 표준.

시뮬레이션 이벤트 로그(`SimulationMetrics.event_log`)에서 안전 사건을 추출해
두 가지 산출물로 변환한다:

- **GENESIS 307**: 항공·철도 사고조사위원회(항철위) 양식에 준하는 마크다운 보고서
  (`accident_report`). 시뮬 사고 로그를 사람이 읽는 보고 양식으로 자동 작성.
- **ODYSSEY 467**: 기관 간 교환을 위한 **표준 사고조사 레코드**
  (`to_investigation_record` / `investigation_dataset`). ICAO ADREP 의 최소
  필드(occurrence class·event type·involved aircraft)를 본떠 JSON 직렬화 가능한
  결정적 스키마(`sdacs.incident.v1`)로 출력.

면책: 본 변환기는 시뮬레이션 데이터를 표준 양식으로 정리하는 개발 도구이며,
실제 사고 발생 시 법정 보고 의무(항공안전법 §132 등)를 갈음하지 않는다.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Sequence

# 사건 유형 → 항철위 분류(사고/준사고/이벤트)
SEVERITY_BY_TYPE: dict[str, str] = {
    "collision": "accident",          # 사고
    "near_miss": "serious_incident",  # 준사고
    "battery_depleted": "incident",   # 이벤트
    "gps_loss": "incident",
    "motor_failure": "incident",
    "comm_loss": "incident",
}

SEVERITY_LABEL_KO: dict[str, str] = {
    "accident": "사고",
    "serious_incident": "준사고",
    "incident": "이벤트",
}

# 메타 키 — 관련 기체 식별에 쓰지 않는 필드
_META_KEYS = {"t", "type"}
_DRONE_KEYS = ("drone_a", "drone_b", "drone_id")


@dataclass(frozen=True)
class Incident:
    """단일 안전 사건."""

    time_s: float
    event_type: str
    severity: str
    drones: tuple[str, ...]
    detail: dict = field(default_factory=dict)


def _extract_drones(event: dict) -> tuple[str, ...]:
    drones: list[str] = []
    for key in _DRONE_KEYS:
        val = event.get(key)
        if val is not None and val not in drones:
            drones.append(str(val))
    return tuple(drones)


def extract_incidents(event_log: Sequence[dict]) -> list[Incident]:
    """이벤트 로그에서 안전 사건만 추출해 시간순 정렬한다."""
    incidents: list[Incident] = []
    for event in event_log:
        etype = event.get("type")
        if etype not in SEVERITY_BY_TYPE:
            continue
        detail = {k: v for k, v in event.items() if k not in _META_KEYS}
        incidents.append(
            Incident(
                time_s=float(event.get("t", 0.0)),
                event_type=etype,
                severity=SEVERITY_BY_TYPE[etype],
                drones=_extract_drones(event),
                detail=detail,
            )
        )
    incidents.sort(key=lambda i: i.time_s)
    return incidents


def _occurrence_id(sim_id: str, incident: Incident) -> str:
    """sim_id + 사건 식별 정보로 결정적 occurrence id 생성."""
    raw = f"{sim_id}|{incident.time_s}|{incident.event_type}|{','.join(incident.drones)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]  # noqa: S324


def to_investigation_record(incident: Incident, *, sim_id: str) -> dict:
    """ODYSSEY 467 — 표준 사고조사 교환 레코드(JSON 직렬화 가능).

    스키마 ``sdacs.incident.v1`` — ICAO ADREP 최소 필드 정렬.
    """
    return {
        "schema": "sdacs.incident.v1",
        "occurrence_id": _occurrence_id(sim_id, incident),
        "sim_id": sim_id,
        "occurrence_class": incident.severity,
        "occurrence_class_ko": SEVERITY_LABEL_KO[incident.severity],
        "event_type": incident.event_type,
        "time_offset_s": incident.time_s,
        "involved_uas": list(incident.drones),
        "detail": dict(incident.detail),
    }


def investigation_dataset(event_log: Sequence[dict], *, sim_id: str) -> list[dict]:
    """ODYSSEY 467 — 한 런의 모든 사건을 표준 레코드 리스트로 일괄 변환."""
    return [
        to_investigation_record(inc, sim_id=sim_id)
        for inc in extract_incidents(event_log)
    ]


def accident_report(
    incidents: Sequence[Incident],
    *,
    sim_id: str,
    scenario: str | None = None,
) -> str:
    """GENESIS 307 — 항철위 양식 사고 보고서(마크다운).

    ``incidents`` 는 ``extract_incidents`` 결과를 받는다.
    """
    counts = {"accident": 0, "serious_incident": 0, "incident": 0}
    for inc in incidents:
        counts[inc.severity] += 1

    lines = [
        "# 항공 사고·준사고 조사 보고서 (시뮬레이션 자동 생성)",
        "",
        f"- 시뮬레이션 ID: `{sim_id}`",
        f"- 시나리오: {scenario or '미지정'}",
        f"- 발생 개요: 사고 {counts['accident']}건 · "
        f"준사고 {counts['serious_incident']}건 · 이벤트 {counts['incident']}건",
        "",
    ]

    if not incidents:
        lines.append("본 시뮬레이션 런에서 보고 대상 안전 사건은 **없음**.")
        return "\n".join(lines)

    lines += [
        "## 발생 사건 일람",
        "",
        "| # | 발생시각(s) | 분류 | 유형 | 관련 기체 | 상세 |",
        "|:-:|:-:|:-:|---|---|---|",
    ]
    for idx, inc in enumerate(incidents, start=1):
        drones = ", ".join(inc.drones) if inc.drones else "—"
        detail = ", ".join(f"{k}={v}" for k, v in inc.detail.items()
                           if k not in _DRONE_KEYS) or "—"
        lines.append(
            f"| {idx} | {inc.time_s:.1f} | {SEVERITY_LABEL_KO[inc.severity]} "
            f"| {inc.event_type} | {drones} | {detail} |"
        )

    lines += [
        "",
        "## 조치 사항",
        "- 사고(충돌): 5계층 안전망 로그 검토 → L3 CPA·L1 APF 파라미터 점검 권고",
        "- 준사고(근접): 최소 이격거리 위반 구간 재시뮬 권고",
        "- 이벤트: 장애 주입(INJ) 시나리오 재현성 확인 권고",
    ]
    return "\n".join(lines)
