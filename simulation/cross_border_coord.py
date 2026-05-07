"""Phase 695: 국경 간 비행 조율 시스템."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class HandoffStatus(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"


@dataclass
class AirspaceAuthority:
    code: str
    name: str
    contact_endpoint: str = ""
    required_docs: List[str] = field(default_factory=list)


@dataclass
class BorderCrossing:
    crossing_id: str
    callsign: str
    from_authority: str
    to_authority: str
    crossing_point: Tuple[float, float]
    scheduled_time: float
    altitude: float
    status: HandoffStatus = HandoffStatus.PROPOSED
    documents: Dict[str, bool] = field(default_factory=dict)


class CrossBorderCoordinator:
    """두 공역 당국 사이의 핸드오프/서류 교환을 관리."""

    def __init__(self) -> None:
        self.authorities: Dict[str, AirspaceAuthority] = {}
        self.crossings: Dict[str, BorderCrossing] = {}
        self._next_id = 0

    def register_authority(self, authority: AirspaceAuthority) -> None:
        self.authorities[authority.code] = authority

    def propose_crossing(
        self,
        callsign: str,
        from_code: str,
        to_code: str,
        crossing_point: Tuple[float, float],
        scheduled_time: float,
        altitude: float,
    ) -> Optional[str]:
        if from_code not in self.authorities or to_code not in self.authorities:
            return None
        if from_code == to_code:
            return None
        self._next_id += 1
        cid = f"BC-{self._next_id:05d}"
        dest = self.authorities[to_code]
        docs = {doc: False for doc in dest.required_docs}
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
        return cid

    def submit_document(self, crossing_id: str, doc_name: str) -> bool:
        bc = self.crossings.get(crossing_id)
        if bc is None or doc_name not in bc.documents:
            return False
        bc.documents[doc_name] = True
        return True

    def all_documents_ready(self, crossing_id: str) -> bool:
        bc = self.crossings.get(crossing_id)
        if bc is None:
            return False
        return all(bc.documents.values())

    def accept_handoff(self, crossing_id: str) -> bool:
        bc = self.crossings.get(crossing_id)
        if bc is None or bc.status != HandoffStatus.PROPOSED:
            return False
        if not self.all_documents_ready(crossing_id):
            return False
        bc.status = HandoffStatus.ACCEPTED
        return True

    def reject_handoff(self, crossing_id: str, reason: str = "") -> bool:
        bc = self.crossings.get(crossing_id)
        if bc is None:
            return False
        bc.status = HandoffStatus.REJECTED
        return True

    def complete_handoff(self, crossing_id: str) -> bool:
        bc = self.crossings.get(crossing_id)
        if bc is None or bc.status != HandoffStatus.ACCEPTED:
            return False
        bc.status = HandoffStatus.COMPLETED
        return True

    def pending_crossings(self) -> List[BorderCrossing]:
        return [c for c in self.crossings.values() if c.status == HandoffStatus.PROPOSED]

    def get_stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for c in self.crossings.values():
            counts[c.status.value] = counts.get(c.status.value, 0) + 1
        return {
            "authorities": len(self.authorities),
            "crossings": len(self.crossings),
            "by_status": counts,
        }
