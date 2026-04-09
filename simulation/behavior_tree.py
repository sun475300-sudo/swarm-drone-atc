"""
Phase 661: Behavior Tree for Drone Agent Decision Making

BurnySc2/monorepo의 behavior_tree.py 패턴을 참고하여
드론 자율 비행 의사결정 트리를 구현.

Reference: https://github.com/BurnySc2/monorepo (MIT License)

Behavior Tree 노드 유형:
- Sequence: 모든 자식 SUCCESS 시 SUCCESS (AND)
- Selector: 하나라도 SUCCESS 시 SUCCESS (OR)
- Condition: 상태 확인 (SUCCESS/FAIL)
- Action: 실행 (SUCCESS/FAIL/RUNNING)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class NodeStatus(Enum):
    """행동 트리 노드 실행 결과."""
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3


@dataclass
class BTNode:
    """행동 트리 기본 노드."""
    name: str = ""
    children: list[BTNode] = field(default_factory=list)

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        return NodeStatus.SUCCESS


@dataclass
class SequenceNode(BTNode):
    """Sequence: 모든 자식이 SUCCESS여야 SUCCESS (AND 로직)."""

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        for child in self.children:
            status = child.tick(context)
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            if status == NodeStatus.FAILURE:
                return NodeStatus.FAILURE
        return NodeStatus.SUCCESS


@dataclass
class SelectorNode(BTNode):
    """Selector: 하나라도 SUCCESS면 SUCCESS (OR 로직)."""

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        for child in self.children:
            status = child.tick(context)
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            if status == NodeStatus.SUCCESS:
                return NodeStatus.SUCCESS
        return NodeStatus.FAILURE


@dataclass
class ConditionNode(BTNode):
    """조건 확인 노드. predicate가 True면 SUCCESS."""
    predicate: Optional[Callable[[dict[str, Any]], bool]] = None

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        if self.predicate is None:
            return NodeStatus.SUCCESS
        return NodeStatus.SUCCESS if self.predicate(context) else NodeStatus.FAILURE


@dataclass
class ActionNode(BTNode):
    """실행 노드. action 함수를 호출하여 결과를 반환."""
    action: Optional[Callable[[dict[str, Any]], NodeStatus]] = None

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        if self.action is None:
            return NodeStatus.SUCCESS
        return self.action(context)


@dataclass
class InverterNode(BTNode):
    """데코레이터: 자식 결과를 반전 (SUCCESS ↔ FAILURE)."""
    child: Optional[BTNode] = None

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        if self.child is None:
            return NodeStatus.FAILURE
        status = self.child.tick(context)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        if status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return NodeStatus.RUNNING


@dataclass
class RepeatUntilSuccess(BTNode):
    """데코레이터: 자식이 SUCCESS될 때까지 반복 (max_repeats 제한)."""
    child: Optional[BTNode] = None
    max_repeats: int = 10

    def tick(self, context: dict[str, Any]) -> NodeStatus:
        if self.child is None:
            return NodeStatus.FAILURE
        for _ in range(self.max_repeats):
            status = self.child.tick(context)
            if status == NodeStatus.SUCCESS:
                return NodeStatus.SUCCESS
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
        return NodeStatus.FAILURE


# ── 드론 전용 조건/액션 팩토리 ──────────────────────────────────────

def is_battery_low(context: dict[str, Any]) -> bool:
    """배터리가 위기 수준(5%) 이하인지 확인."""
    return context.get("battery_pct", 100) <= context.get("battery_critical", 5.0)


def is_battery_warning(context: dict[str, Any]) -> bool:
    """배터리가 경고 수준(20%) 이하인지 확인."""
    return context.get("battery_pct", 100) <= 20.0


def has_conflict(context: dict[str, Any]) -> bool:
    """충돌 위협이 존재하는지 확인."""
    return context.get("conflict_detected", False)


def has_advisory(context: dict[str, Any]) -> bool:
    """회피 어드바이저리가 할당되었는지 확인."""
    return context.get("advisory", None) is not None


def is_at_waypoint(context: dict[str, Any]) -> bool:
    """현재 웨이포인트에 도달했는지 확인."""
    return context.get("distance_to_waypoint", float("inf")) <= context.get("waypoint_tol", 80.0)


def is_comms_lost(context: dict[str, Any]) -> bool:
    """통신 두절 상태인지 확인."""
    return context.get("comms_lost", False)


def is_wind_strong(context: dict[str, Any]) -> bool:
    """강풍 조건인지 확인 (>10 m/s)."""
    return context.get("wind_speed", 0) > 10.0


def action_emergency_land(context: dict[str, Any]) -> NodeStatus:
    """긴급 착륙 실행."""
    context["command"] = "EMERGENCY_LAND"
    return NodeStatus.SUCCESS


def action_execute_advisory(context: dict[str, Any]) -> NodeStatus:
    """어드바이저리 회피 기동 실행."""
    advisory = context.get("advisory")
    if advisory:
        context["command"] = f"EXECUTE_{advisory}"
        return NodeStatus.SUCCESS
    return NodeStatus.FAILURE


def action_evade_apf(context: dict[str, Any]) -> NodeStatus:
    """APF 엔진으로 긴급 회피."""
    context["command"] = "EVADE_APF"
    return NodeStatus.RUNNING


def action_hold_position(context: dict[str, Any]) -> NodeStatus:
    """현재 위치 선회 대기."""
    context["command"] = "HOLD"
    return NodeStatus.RUNNING


def action_navigate_waypoint(context: dict[str, Any]) -> NodeStatus:
    """다음 웨이포인트로 비행."""
    context["command"] = "NAVIGATE"
    return NodeStatus.RUNNING


def action_rtl(context: dict[str, Any]) -> NodeStatus:
    """RTL (Return to Launch) 실행."""
    context["command"] = "RTL"
    return NodeStatus.RUNNING


def action_next_waypoint(context: dict[str, Any]) -> NodeStatus:
    """다음 웨이포인트로 전진."""
    wp_idx = context.get("waypoint_index", 0)
    total = context.get("total_waypoints", 0)
    if wp_idx + 1 < total:
        context["waypoint_index"] = wp_idx + 1
        context["command"] = "NEXT_WAYPOINT"
        return NodeStatus.SUCCESS
    context["command"] = "MISSION_COMPLETE"
    return NodeStatus.SUCCESS


# ── 드론 비행 BT 빌더 ────────────────────────────────────────────

def build_drone_flight_bt() -> BTNode:
    """
    드론 자율 비행을 위한 기본 행동 트리를 구성합니다.

    우선순위 (Selector, 위→아래):
    1. 배터리 위기 → 긴급 착륙
    2. 통신 두절 → RTL 프로토콜
    3. 충돌 위협 + 어드바이저리 → 회피 기동
    4. 충돌 위협 (어드바이저리 없음) → APF 긴급 회피
    5. 웨이포인트 도달 → 다음 웨이포인트
    6. 기본 → 웨이포인트 항법
    """
    return SelectorNode(
        name="DroneFlightRoot",
        children=[
            # 1. 배터리 위기 → 긴급 착륙
            SequenceNode(name="EmergencyBattery", children=[
                ConditionNode(name="IsBatteryLow", predicate=is_battery_low),
                ActionNode(name="EmergencyLand", action=action_emergency_land),
            ]),
            # 2. 통신 두절 → RTL
            SequenceNode(name="CommsLostProtocol", children=[
                ConditionNode(name="IsCommsLost", predicate=is_comms_lost),
                ActionNode(name="ReturnToLaunch", action=action_rtl),
            ]),
            # 3. 충돌 위협 + 어드바이저리 → 회피
            SequenceNode(name="ConflictWithAdvisory", children=[
                ConditionNode(name="HasConflict", predicate=has_conflict),
                ConditionNode(name="HasAdvisory", predicate=has_advisory),
                ActionNode(name="ExecuteAdvisory", action=action_execute_advisory),
            ]),
            # 4. 충돌 위협 (어드바이저리 없음) → APF
            SequenceNode(name="ConflictAPF", children=[
                ConditionNode(name="HasConflict2", predicate=has_conflict),
                ActionNode(name="EvadeAPF", action=action_evade_apf),
            ]),
            # 5. 웨이포인트 도달 → 다음
            SequenceNode(name="WaypointReached", children=[
                ConditionNode(name="AtWaypoint", predicate=is_at_waypoint),
                ActionNode(name="NextWaypoint", action=action_next_waypoint),
            ]),
            # 6. 기본 항법
            ActionNode(name="Navigate", action=action_navigate_waypoint),
        ],
    )
