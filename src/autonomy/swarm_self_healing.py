"""Phase 367: 스웜 자가 치유 — 결손 드론 임무 자동 재분배.

결손(통신 두절·모터 페일·배터리 소진)으로 이탈한 드론의 진행 중 임무를
가용한 건강 드론에게 **결정적으로** 재분배한다. CBS 재계획의 상위 의사결정
계층에 해당하며, 어떤 임무를 어느 드론으로 옮길지(혹은 옮길 수 없어 드롭할지)를
계산한다. 실제 경로 재계획은 하위 계획기(`simulation/cbs_planner`)에 위임한다.

재분배 전략: 우선순위 높은 임무부터, 최근접 + 부하 균형 그리디.
RNG 미사용 — 동일 입력은 항상 동일 결과(재현성·검증 용이).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class Task:
    """재분배 대상 임무. 위치와 우선순위만 가진다(경로는 하위 계획기 소관)."""

    task_id: str
    position: Vec3
    priority: int = 5


@dataclass(frozen=True)
class Reassignment:
    """단일 임무 재분배 결과."""

    task_id: str
    from_drone: str
    to_drone: str
    distance_m: float


@dataclass(frozen=True)
class HealingReport:
    """결손 드론 1기 처리 결과 요약."""

    failed_drone: str
    reassignments: tuple[Reassignment, ...]
    dropped: tuple[str, ...]

    @property
    def healed_count(self) -> int:
        """재분배에 성공한 임무 수."""
        return len(self.reassignments)

    @property
    def is_fully_healed(self) -> bool:
        """드롭 없이 모든 임무를 재분배했는지 여부."""
        return len(self.dropped) == 0


@dataclass
class _Drone:
    """내부 드론 상태(가변)."""

    drone_id: str
    position: Vec3
    healthy: bool = True
    tasks: dict[str, Task] = field(default_factory=dict)


def _distance(a: Vec3, b: Vec3) -> float:
    """3D 유클리드 거리."""
    return math.sqrt(
        (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
    )


class SwarmSelfHealer:
    """결손 드론의 임무를 가용 드론에게 재분배하는 자가 치유 컨트롤러.

    드론당 최대 임무 수(`max_tasks_per_drone`)로 과부하를 방지한다.
    수용 가능한 후보가 없으면 해당 임무는 드롭되어 재계획 큐로 반환된다.
    """

    def __init__(self, max_tasks_per_drone: int = 5) -> None:
        """인스턴스를 초기화한다."""
        if max_tasks_per_drone < 1:
            raise ValueError("max_tasks_per_drone는 1 이상이어야 합니다")
        self._max_tasks = max_tasks_per_drone
        self._drones: dict[str, _Drone] = {}

    def add_drone(self, drone_id: str, position: Vec3) -> None:
        """드론을 등록한다(건강 상태로 시작)."""
        if drone_id in self._drones:
            raise ValueError(f"이미 등록된 드론입니다: {drone_id}")
        self._drones[drone_id] = _Drone(drone_id=drone_id, position=position)

    def assign_task(self, task: Task, drone_id: str) -> bool:
        """임무를 드론에 할당한다. 미등록·결손·용량초과 시 False."""
        drone = self._drones.get(drone_id)
        if drone is None or not drone.healthy:
            return False
        if len(drone.tasks) >= self._max_tasks:
            return False
        drone.tasks[task.task_id] = task
        return True

    def available_drones(self) -> list[str]:
        """여유 용량이 있는 건강 드론 ID 목록(정렬)."""
        return sorted(
            d.drone_id
            for d in self._drones.values()
            if d.healthy and len(d.tasks) < self._max_tasks
        )

    def mark_failed(self, drone_id: str) -> HealingReport:
        """드론을 결손 처리하고 그 임무를 재분배한 결과를 반환한다.

        미등록·이미 결손 드론은 빈 리포트를 반환한다(idempotent).
        """
        drone = self._drones.get(drone_id)
        if drone is None or not drone.healthy:
            return HealingReport(failed_drone=drone_id, reassignments=(), dropped=())

        orphan_tasks = list(drone.tasks.values())
        drone.healthy = False
        drone.tasks = {}

        # 우선순위 내림차순, 동률은 task_id 오름차순으로 결정적 처리.
        orphan_tasks.sort(key=lambda t: (-t.priority, t.task_id))

        reassignments: list[Reassignment] = []
        dropped: list[str] = []
        for task in orphan_tasks:
            target = self._select_target(task)
            if target is None:
                dropped.append(task.task_id)
                continue
            self._drones[target].tasks[task.task_id] = task
            reassignments.append(
                Reassignment(
                    task_id=task.task_id,
                    from_drone=drone_id,
                    to_drone=target,
                    distance_m=_distance(task.position, self._drones[target].position),
                )
            )
        return HealingReport(
            failed_drone=drone_id,
            reassignments=tuple(reassignments),
            dropped=tuple(dropped),
        )

    def _select_target(self, task: Task) -> str | None:
        """임무 1건의 수용 드론을 선택한다.

        선택 기준(결정적): (1) 거리 오름차순 (2) 현재 부하 오름차순
        (3) drone_id 오름차순(사전순/lexicographic — 숫자 접미 ID는 자연
        순서와 다를 수 있음). 여유 용량이 없으면 None.
        """
        candidates = [
            d
            for d in self._drones.values()
            if d.healthy and len(d.tasks) < self._max_tasks
        ]
        if not candidates:
            return None
        best = min(
            candidates,
            key=lambda d: (
                _distance(task.position, d.position),
                len(d.tasks),
                d.drone_id,
            ),
        )
        return best.drone_id

    def drone_load(self, drone_id: str) -> int:
        """드론의 현재 임무 수. 결손 드론은 -2, 미등록 드론은 -1.

        결손 드론은 `tasks`가 비워지므로 단순 길이만으로는 유휴(0)와
        구분되지 않는다 → 결손은 별도 센티넬 -2로 구분한다.
        """
        drone = self._drones.get(drone_id)
        if drone is None:
            return -1
        if not drone.healthy:
            return -2
        return len(drone.tasks)

    def summary(self) -> dict:
        """현재 스웜 상태 요약."""
        healthy = [d for d in self._drones.values() if d.healthy]
        return {
            "total_drones": len(self._drones),
            "healthy_drones": len(healthy),
            "failed_drones": len(self._drones) - len(healthy),
            "assigned_tasks": sum(len(d.tasks) for d in healthy),
        }


def heal_swarm(
    healer: SwarmSelfHealer, failed_drone_ids: list[str]
) -> list[HealingReport]:
    """다수 드론 동시 결손을 순차 재분배한다(ID 순서대로 결정적 처리)."""
    return [healer.mark_failed(did) for did in sorted(failed_drone_ids)]
