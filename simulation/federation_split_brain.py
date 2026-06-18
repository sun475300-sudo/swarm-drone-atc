"""ODYSSEY Phase 430 (Federation): 분할 뇌(split-brain) 안전 강하 정책.

연합(다중 SDACS 인스턴스)에서 인스턴스 간 통신이 끊겨 네트워크가 분할되면
(split-brain), 두 분파가 같은 드론에 모순된 명령을 내릴 위험이 생긴다. 이 모듈은
연합 단절 상황에서 드론을 **결정적으로** 안전한 상태로 유도하는 정책을 제공한다.
외부 네트워크·랜덤 없이 동작하며, 동일한 입력 시퀀스는 항상 동일한 결정 로그를
만든다(재현성).

Phase 423 :class:`~simulation.federation_handover.HandoverCoordinator` 가 커버리지
상실 시 ``CONTINGENT`` 로만 표시하고 미룬 **안전 강하(safe descent)** 책임을 여기서
구체화한다.

연결성 입력은 인스턴스 간 양방향 링크 집합으로 주어지고, :class:`PartitionSnapshot`
이 이를 연결 요소(connected component)로 분해한다. **과반(majority)** 분파 — 전체
인스턴스의 절반을 초과해 포함하는 요소 — 만이 단독 관제 권위를 주장할 수 있다.
과반이 없으면(예: 2-2 균등 분할) 어떤 분파도 권위를 확신할 수 없다.

드론 한 대의 한 평가 틱마다 4단계 안전 행동 사다리:

- **NOMINAL** — 관제 인스턴스가 과반 분파에 있고 드론이 커버됨 → 정상 운항.
- **HOLD** — 커버되지만 관제권이 소수/무과반 분파에 고립 → 위치 유지(loiter).
  다른 분파의 모순 명령 가능성이 있어 새 명령을 받지 않는다.
- **DESCEND** — 커버리지 상실(``CONTINGENT``), 또는 HOLD 가 ``hold_limit`` 틱을
  초과해 지속 → 통제된 안전 고도 강하.
- **LAND** — 관제권이 아예 없거나(고아), 강하가 ``descend_limit`` 틱을 초과해
  지속 → 안전 착륙.

NOMINAL 로 복귀하면 누적 카운터가 초기화되어 일시적 단절에서 과잉 강하를 막는다
(이력현상). 모든 결정은 불변 :class:`SafetyDecision` 으로 기록된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 안전 행동 사다리 (보수성 오름차순·고정).
NOMINAL = "NOMINAL"
HOLD = "HOLD"
DESCEND = "DESCEND"
LAND = "LAND"


@dataclass(frozen=True)
class PartitionSnapshot:
    """인스턴스 간 연결성의 불변 스냅샷 — 양방향 링크를 연결 요소로 분해한다."""

    instances: tuple[str, ...]
    links: frozenset[tuple[str, str]]

    def __post_init__(self) -> None:
        known = set(self.instances)
        if len(known) != len(self.instances):
            raise ValueError("instances에 중복 id가 있음")
        for a, b in self.links:
            if a == b:
                raise ValueError(f"자기 자신 링크는 무의미: {a}")
            if a not in known or b not in known:
                raise KeyError(f"미등록 인스턴스 링크: ({a}, {b})")

    def _component_of(self, instance: str) -> frozenset[str]:
        """인스턴스가 속한 연결 요소를 결정적으로 계산한다 (정렬 BFS)."""
        if instance not in set(self.instances):
            raise KeyError(f"미등록 인스턴스: {instance}")
        adjacency: dict[str, set[str]] = {i: set() for i in self.instances}
        for a, b in self.links:
            adjacency[a].add(b)
            adjacency[b].add(a)
        seen = {instance}
        frontier = [instance]
        while frontier:
            node = frontier.pop()
            for nxt in sorted(adjacency[node]):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        return frozenset(seen)

    def majority_component(self) -> frozenset[str]:
        """과반 인스턴스를 포함하는 연결 요소 (없으면 빈 frozenset)."""
        n = len(self.instances)
        seen: set[frozenset[str]] = set()
        for instance in self.instances:
            component = self._component_of(instance)
            if component in seen:
                continue  # 같은 요소를 BFS로 재계산하지 않는다.
            seen.add(component)
            if len(component) * 2 > n:
                return component
        return frozenset()

    def in_majority(self, instance: str) -> bool:
        """인스턴스가 과반 분파에 속하는지 — 단독 관제 권위 주장 가능 여부.

        미등록 인스턴스면 ``KeyError`` (경계에서 조기 실패).
        """
        if instance not in set(self.instances):
            raise KeyError(f"미등록 인스턴스: {instance}")
        return instance in self.majority_component()


@dataclass(frozen=True)
class SafetyDecision:
    """단일 평가 틱의 안전 행동 결정에 대한 불변 기록 (감사 로그 1행)."""

    seq: int
    drone_id: str
    instance_id: str | None
    action: str
    reason: str
    isolated_ticks: int
    descend_ticks: int


@dataclass
class SafeDescentPolicy:
    """연합 단절 시 드론을 안전 상태로 유도하는 결정적 정책 엔진.

    ``hold_limit`` 틱을 초과해 고립이 지속되면 HOLD→DESCEND 로, ``descend_limit``
    틱을 초과해 강하가 지속되면 DESCEND→LAND 로 단계 상승한다.
    """

    hold_limit: int = 3
    descend_limit: int = 3
    _isolated_ticks: dict[str, int] = field(default_factory=dict)
    _descend_ticks: dict[str, int] = field(default_factory=dict)
    _log: list[SafetyDecision] = field(default_factory=list)
    _seq: int = 0

    def __post_init__(self) -> None:
        if self.hold_limit < 0 or self.descend_limit < 0:
            raise ValueError("hold_limit·descend_limit은 음수일 수 없음")

    def evaluate(
        self,
        drone_id: str,
        controller: str | None,
        covered: bool,
        partition: PartitionSnapshot,
    ) -> SafetyDecision:
        """드론의 현 상태를 반영해 안전 행동을 결정하고 기록한다.

        빈 ``drone_id`` 는 ``ValueError``. 등록된 ``controller`` 는 ``partition`` 에
        존재해야 하며, 아니면 ``KeyError``.
        """
        if not drone_id:
            raise ValueError("drone_id가 비어 있음")
        if controller is not None and controller not in set(partition.instances):
            raise KeyError(f"미등록 관제 인스턴스: {controller}")

        if controller is None:
            # 관제 권위 부재 — 누구도 명령할 수 없으므로 즉시 안전 착륙.
            self._isolated_ticks[drone_id] = 0
            self._descend_ticks[drone_id] = 0
            return self._record(drone_id, controller, LAND, "orphaned")

        if not covered:
            # 커버리지 상실(CONTINGENT) — 통제 강하, 지속되면 착륙으로 상승.
            self._isolated_ticks[drone_id] = 0
            self._descend_ticks[drone_id] = self._descend_ticks.get(drone_id, 0) + 1
            if self._descend_ticks[drone_id] > self.descend_limit:
                return self._record(drone_id, controller, LAND, "coverage_lost_persistent")
            return self._record(drone_id, controller, DESCEND, "coverage_lost")

        if not partition.in_majority(controller):
            # split-brain — 관제권이 소수/무과반 분파에 고립.
            self._isolated_ticks[drone_id] = self._isolated_ticks.get(drone_id, 0) + 1
            if self._isolated_ticks[drone_id] > self.hold_limit:
                self._descend_ticks[drone_id] = self._descend_ticks.get(drone_id, 0) + 1
                if self._descend_ticks[drone_id] > self.descend_limit:
                    return self._record(drone_id, controller, LAND, "isolation_persistent")
                return self._record(drone_id, controller, DESCEND, "isolation_escalated")
            return self._record(drone_id, controller, HOLD, "split_brain_isolated")

        # 정상 — 과반 분파 관제·커버 확보. 누적 카운터 초기화(이력현상).
        self._isolated_ticks[drone_id] = 0
        self._descend_ticks[drone_id] = 0
        return self._record(drone_id, controller, NOMINAL, "nominal")

    def _record(self, drone_id: str, controller: str | None, action: str, reason: str) -> SafetyDecision:
        self._seq += 1
        decision = SafetyDecision(
            seq=self._seq,
            drone_id=drone_id,
            instance_id=controller,
            action=action,
            reason=reason,
            isolated_ticks=self._isolated_ticks.get(drone_id, 0),
            descend_ticks=self._descend_ticks.get(drone_id, 0),
        )
        self._log.append(decision)
        return decision

    def log(self) -> tuple[SafetyDecision, ...]:
        """기록된 모든 안전 결정을 발생 순서대로 반환한다 (불변 사본)."""
        return tuple(self._log)

    def action_counts(self) -> dict[str, int]:
        """행동별 누적 횟수 요약 (NOMINAL·HOLD·DESCEND·LAND)."""
        counts = {NOMINAL: 0, HOLD: 0, DESCEND: 0, LAND: 0}
        for decision in self._log:
            counts[decision.action] += 1
        return counts
