"""
드론 그룹 관리
==============
그룹 생성/해체 + 그룹별 명령 + 상태 집계.

사용법:
    gm = DroneGroupManager()
    gm.create_group("alpha", ["d1", "d2", "d3"])
    gm.set_group_command("alpha", "RTL")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DroneGroup:
    """드론 그룹"""
    group_id: str
    members: list[str] = field(default_factory=list)
    command: str = ""
    leader: str = ""
    mission: str = ""
    active: bool = True


class DroneGroupManager:
    """드론 그룹 관리."""

    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self._groups: dict[str, DroneGroup] = {}
        self._drone_to_group: dict[str, str] = {}

    def create_group(
        self,
        group_id: str,
        members: list[str],
        leader: str = "",
        mission: str = "",
    ) -> DroneGroup:
        """`group` 결과를 생성한다."""
        group = DroneGroup(
            group_id=group_id,
            members=list(members),
            leader=leader or (members[0] if members else ""),
            mission=mission,
        )
        self._groups[group_id] = group
        for m in members:
            self._drone_to_group[m] = group_id
        return group

    def dissolve_group(self, group_id: str) -> bool:
        """``dissolve_group`` 동작을 수행한다."""
        group = self._groups.get(group_id)
        if not group:
            return False
        group.active = False
        for m in group.members:
            self._drone_to_group.pop(m, None)
        return True

    def add_member(self, group_id: str, drone_id: str) -> bool:
        """`member` 항목을 추가한다."""
        group = self._groups.get(group_id)
        if not group or not group.active:
            return False
        if drone_id not in group.members:
            group.members.append(drone_id)
            self._drone_to_group[drone_id] = group_id
        return True

    def remove_member(self, group_id: str, drone_id: str) -> bool:
        """`member` 상태를 정리한다."""
        group = self._groups.get(group_id)
        if not group:
            return False
        if drone_id in group.members:
            group.members.remove(drone_id)
            self._drone_to_group.pop(drone_id, None)
            return True
        return False

    def set_group_command(self, group_id: str, command: str) -> bool:
        """`group command` 상태를 갱신한다."""
        group = self._groups.get(group_id)
        if not group or not group.active:
            return False
        group.command = command
        return True

    def get_drone_group(self, drone_id: str) -> str | None:
        """`drone group` 정보를 조회한다."""
        return self._drone_to_group.get(drone_id)

    def get_group(self, group_id: str) -> DroneGroup | None:
        """`group` 정보를 조회한다."""
        return self._groups.get(group_id)

    def active_groups(self) -> list[DroneGroup]:
        """``active_groups`` 동작을 수행한다."""
        return [g for g in self._groups.values() if g.active]

    def group_size(self, group_id: str) -> int:
        """``group_size`` 동작을 수행한다."""
        group = self._groups.get(group_id)
        return len(group.members) if group else 0

    def merge_groups(self, group_a: str, group_b: str, new_id: str = "") -> DroneGroup | None:
        """``merge_groups`` 동작을 수행한다."""
        ga = self._groups.get(group_a)
        gb = self._groups.get(group_b)
        if not ga or not gb:
            return None
        merged_id = new_id or f"{group_a}_{group_b}"
        members = list(set(ga.members + gb.members))
        self.dissolve_group(group_a)
        self.dissolve_group(group_b)
        return self.create_group(merged_id, members, leader=ga.leader)

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        active = self.active_groups()
        return {
            "total_groups": len(self._groups),
            "active_groups": len(active),
            "total_members": sum(len(g.members) for g in active),
            "avg_size": round(
                sum(len(g.members) for g in active) / max(len(active), 1), 1
            ),
        }
