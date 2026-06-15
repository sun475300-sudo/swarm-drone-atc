"""ODYSSEY Phase 423 (Federation): 지역 간 관제권 핸드오버.

드론이 한 SDACS 인스턴스(USS)가 관리하는 공역을 벗어나 인접 인스턴스의 공역으로
진입할 때, 관제권을 **결정적으로** 이양(handover)하는 in-process 모델이다.

Phase 421 :class:`~simulation.federation_discovery.FederationDiscoveryService`의
점 커버리지(``covering``)를 1차 입력으로 사용한다. 외부 네트워크·랜덤 없이 동작하며,
동일한 입력 시퀀스는 항상 동일한 핸드오버 로그를 만든다(재현성).

결정 규약 (드론의 한 위치 표본마다):

- 현재 관제 인스턴스가 그 점을 여전히 포함하면 **RETAINED** — 핸드오버 없음.
  중첩(overlap) 구역에서도 현 관제권을 유지해 경계에서의 진동(flapping)을 막는다
  (이력현상/hysteresis).
- 현재 관제권이 점을 벗어났고 다른 인스턴스가 점을 포함하면 **HANDOVER** — 후보 중
  id 사전순 최소 인스턴스로 이양한다(결정적; 우선순위 협상은 Phase 424 범위).
- 아직 관제권이 없던 드론이 처음으로 포함 인스턴스를 만나면 **ACQUIRED** — 최초
  관제권 획득. 인스턴스 간 이양(HANDOVER)과 구분해 기록한다(``from_instance`` 가
  None 인 HANDOVER 로 위장하지 않음 → Phase 429 감사 로그 무결성).
- 어떤 인스턴스도 점을 포함하지 않으면 **CONTINGENT** — 커버리지 상실. 현 관제권을
  고아로 만들지 않고 보유한 채 비상(contingency) 플래그만 세운다(안전 강하 정책은
  상위 계층/Phase 430 책임).

모든 결정은 불변 :class:`HandoverEvent` 로 기록되어 순서가 보존된 감사 로그가 된다
(Phase 429 관제권 이양 불변 기록의 기반).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.federation_discovery import FederationDiscoveryService

# 핸드오버 결정 종류 (정렬·고정).
RETAINED = "RETAINED"
ACQUIRED = "ACQUIRED"
HANDOVER = "HANDOVER"
CONTINGENT = "CONTINGENT"


@dataclass(frozen=True)
class HandoverEvent:
    """단일 위치 표본에 대한 관제권 결정의 불변 기록 (감사 로그 1행)."""

    seq: int
    drone_id: str
    point: tuple[float, float, float, float]  # (x, y, z, t)
    decision: str
    from_instance: str | None
    to_instance: str | None
    candidates: tuple[str, ...]


@dataclass
class HandoverCoordinator:
    """Phase 421 디스커버리 위에서 드론별 관제권을 추적·이양하는 결정적 조정자."""

    discovery: FederationDiscoveryService
    _controllers: dict[str, str] = field(default_factory=dict)
    _log: list[HandoverEvent] = field(default_factory=list)
    _seq: int = 0

    def assign(self, drone_id: str, instance_id: str) -> None:
        """드론의 초기 관제 인스턴스를 지정한다.

        빈 ``drone_id`` 는 ``ValueError``, 미등록 인스턴스는 ``KeyError``.
        """
        if not drone_id:
            raise ValueError("drone_id가 비어 있음")
        if instance_id not in self.discovery.instances():
            raise KeyError(f"미등록 인스턴스: {instance_id}")
        self._controllers[drone_id] = instance_id

    def controller_of(self, drone_id: str) -> str | None:
        """드론의 현재 관제 인스턴스 (미배정이면 None)."""
        return self._controllers.get(drone_id)

    def update(
        self, drone_id: str, x: float, y: float, z: float, t: float
    ) -> HandoverEvent:
        """드론의 새 위치 표본을 반영해 관제권 결정을 내리고 기록한다.

        빈 ``drone_id`` 는 ``ValueError``.
        """
        if not drone_id:
            raise ValueError("drone_id가 비어 있음")

        covering = self.discovery.covering(x, y, z, t)
        current = self._controllers.get(drone_id)

        if current is not None and current in covering:
            decision, to_instance = RETAINED, current
        elif covering:
            to_instance = covering[0]
            # 최초 획득(current None)과 인스턴스 간 이양을 구분 기록한다.
            decision = ACQUIRED if current is None else HANDOVER
            self._controllers[drone_id] = to_instance
        else:
            # 커버리지 상실 — 관제권은 보유한 채 비상만 표시(고아 방지).
            decision, to_instance = CONTINGENT, None

        self._seq += 1
        event = HandoverEvent(
            seq=self._seq,
            drone_id=drone_id,
            point=(x, y, z, t),
            decision=decision,
            from_instance=current,
            to_instance=to_instance,
            candidates=covering,
        )
        self._log.append(event)
        return event

    def log(self) -> tuple[HandoverEvent, ...]:
        """기록된 모든 핸드오버 이벤트를 발생 순서대로 반환한다 (불변 사본)."""
        return tuple(self._log)

    def handover_count(self) -> int:
        """실제 관제권 이양(HANDOVER)이 일어난 횟수."""
        return sum(1 for e in self._log if e.decision == HANDOVER)
