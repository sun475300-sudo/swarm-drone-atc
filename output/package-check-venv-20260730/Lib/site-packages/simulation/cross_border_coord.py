"""Phase 695: 국경 간 비행 조율 시스템."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HandoffStatus(Enum):
    """``HandoffStatus`` 관련 기능을 제공한다."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"


@dataclass
class AirspaceAuthority:
    """``AirspaceAuthority`` 관련 기능을 제공한다."""
    code: str
    name: str
    contact_endpoint: str = ""
    required_docs: list[str] = field(default_factory=list)


@dataclass
class BorderCrossing:
    """``BorderCrossing`` 관련 기능을 제공한다."""
    crossing_id: str
    callsign: str
    from_authority: str
    to_authority: str
    crossing_point: tuple[float, float]
    scheduled_time: float
    altitude: float
    status: HandoffStatus = HandoffStatus.PROPOSED
    documents: dict[str, bool] = field(default_factory=dict)
    rejection_reason: str = ""


_DEFAULT_CROSSING_CAP = 10_000


class CrossBorderCoordinator:
    """두 공역 당국 사이의 핸드오프/서류 교환을 관리."""

    def __init__(self, max_crossings: int = _DEFAULT_CROSSING_CAP) -> None:
        """인스턴스를 초기화한다."""
        if max_crossings <= 0:
            raise ValueError("max_crossings must be positive")
        self.authorities: dict[str, AirspaceAuthority] = {}
        self.crossings: dict[str, BorderCrossing] = {}
        self.max_crossings = max_crossings
        self._next_id = 0

    def register_authority(self, authority: AirspaceAuthority) -> None:
        """`authority` 항목을 추가한다."""
        if authority.code in self.authorities:
            raise ValueError(
                f"authority code {authority.code!r} is already registered; "
                "use update_authority() to replace it intentionally"
            )
        # Defensive copy of required_docs to prevent external mutation
        # altering document requirements for future crossings
        stored_docs = list(authority.required_docs)
        from dataclasses import replace
        self.authorities[authority.code] = replace(authority, required_docs=stored_docs)

    def update_authority(self, authority: AirspaceAuthority) -> None:
        """Replace an existing authority record. Use when updating contact info or docs."""
        stored_docs = list(authority.required_docs)
        from dataclasses import replace
        self.authorities[authority.code] = replace(authority, required_docs=stored_docs)

    def propose_crossing(
        self,
        callsign: str,
        from_code: str,
        to_code: str,
        crossing_point: tuple[float, float],
        scheduled_time: float,
        altitude: float,
    ) -> str | None:
        """``propose_crossing`` 동작을 수행한다."""
        if from_code not in self.authorities or to_code not in self.authorities:
            return None
        if from_code == to_code:
            return None
        if len(crossing_point) != 2:
            raise ValueError(
                f"crossing_point must be a 2-element (lat, lon) tuple, "
                f"got {len(crossing_point)} elements"
            )
        if not math.isfinite(crossing_point[0]) or not math.isfinite(crossing_point[1]):
            raise ValueError(
                f"crossing_point coordinates must be finite, got {crossing_point}"
            )
        if not math.isfinite(scheduled_time) or scheduled_time < 0:
            raise ValueError(
                f"scheduled_time must be a finite non-negative number, got {scheduled_time}"
            )
        if not math.isfinite(altitude) or altitude < 0:
            raise ValueError(
                f"altitude must be a finite non-negative number, got {altitude}"
            )
        self._next_id += 1
        cid = f"BC-{self._next_id:05d}"
        dest = self.authorities[to_code]
        docs = dict.fromkeys(dest.required_docs, False)
        self.crossings[cid] = BorderCrossing(
            crossing_id=cid,
            callsign=callsign,
            from_authority=from_code,
            to_authority=to_code,
            crossing_point=crossing_point,
            scheduled_time=scheduled_time,
            altitude=altitude,
            documents=docs,
        )
        # max_crossings 초과 시 종료 상태 레코드 자동 제거
        if len(self.crossings) > self.max_crossings:
            self.purge_terminal()
        # 제거 후에도 초과 중이면 가장 오래된 항목 강제 제거
        if len(self.crossings) > self.max_crossings:
            oldest = next(iter(self.crossings))
            del self.crossings[oldest]
        return cid

    def submit_document(self, crossing_id: str, doc_name: str) -> bool:
        """``submit_document`` 동작을 수행한다."""
        bc = self.crossings.get(crossing_id)
        if bc is None or doc_name not in bc.documents:
            return False
        bc.documents[doc_name] = True
        return True

    def all_documents_ready(self, crossing_id: str) -> bool:
        """``all_documents_ready`` 동작을 수행한다."""
        bc = self.crossings.get(crossing_id)
        if bc is None:
            return False
        return all(bc.documents.values())

    def accept_handoff(self, crossing_id: str) -> bool:
        """``accept_handoff`` 동작을 수행한다."""
        bc = self.crossings.get(crossing_id)
        if bc is None or bc.status != HandoffStatus.PROPOSED:
            return False
        if not self.all_documents_ready(crossing_id):
            return False
        bc.status = HandoffStatus.ACCEPTED
        return True

    def reject_handoff(self, crossing_id: str, reason: str = "") -> bool:
        """``reject_handoff`` 동작을 수행한다."""
        bc = self.crossings.get(crossing_id)
        # PROPOSED 상태만 거부 가능 — ACCEPTED 이후 소급 거부 방지
        if bc is None or bc.status != HandoffStatus.PROPOSED:
            return False
        bc.status = HandoffStatus.REJECTED
        bc.rejection_reason = reason
        return True

    def purge_terminal(self) -> int:
        """COMPLETED/REJECTED 크로싱을 제거해 메모리를 회수한다.

        반환값: 제거된 레코드 수.
        """
        terminal = {
            k for k, v in self.crossings.items()
            if v.status in (HandoffStatus.COMPLETED, HandoffStatus.REJECTED)
        }
        for k in terminal:
            del self.crossings[k]
        return len(terminal)

    def complete_handoff(self, crossing_id: str) -> bool:
        """``complete_handoff`` 동작을 수행한다."""
        bc = self.crossings.get(crossing_id)
        if bc is None or bc.status != HandoffStatus.ACCEPTED:
            return False
        bc.status = HandoffStatus.COMPLETED
        return True

    def get(self, crossing_id: str) -> BorderCrossing | None:
        """Return the BorderCrossing record for the given ID, or None if not found."""
        return self.crossings.get(crossing_id)

    def pending_crossings(self) -> list[BorderCrossing]:
        """``pending_crossings`` 동작을 수행한다."""
        return [c for c in self.crossings.values() if c.status == HandoffStatus.PROPOSED]

    def get_stats(self) -> dict[str, Any]:
        """`stats` 정보를 조회한다."""
        counts: dict[str, int] = {}
        for c in self.crossings.values():
            counts[c.status.value] = counts.get(c.status.value, 0) + 1
        return {
            "authorities": len(self.authorities),
            "crossings": len(self.crossings),
            "by_status": counts,
        }
