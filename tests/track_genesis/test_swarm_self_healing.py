"""Phase 367: 스웜 자가 치유 — 결손 드론 임무 자동 재분배 검증."""
from __future__ import annotations

import pytest

from src.autonomy.swarm_self_healing import (
    SwarmSelfHealer,
    Task,
    heal_swarm,
)


def _healer(max_tasks: int = 5) -> SwarmSelfHealer:
    healer = SwarmSelfHealer(max_tasks_per_drone=max_tasks)
    healer.add_drone("A", (0.0, 0.0, 0.0))
    healer.add_drone("B", (100.0, 0.0, 0.0))
    healer.add_drone("C", (200.0, 0.0, 0.0))
    return healer


def test_reassigns_orphan_task_to_nearest_drone() -> None:
    """결손 드론의 임무는 가장 가까운 건강 드론으로 재분배된다."""
    # Arrange
    healer = _healer()
    healer.add_drone("D", (10.0, 0.0, 0.0))  # A에서 가장 가까움
    task = Task(task_id="t1", position=(5.0, 0.0, 0.0))
    healer.assign_task(task, "A")

    # Act
    report = healer.mark_failed("A")

    # Assert
    assert report.healed_count == 1
    assert report.is_fully_healed
    assert report.reassignments[0].to_drone == "D"
    assert report.reassignments[0].from_drone == "A"
    assert report.dropped == ()


def test_failed_drone_is_no_longer_available() -> None:
    """결손 처리된 드론은 가용 목록에서 빠진다."""
    healer = _healer()
    healer.mark_failed("A")
    assert "A" not in healer.available_drones()
    assert healer.summary()["failed_drones"] == 1


def test_task_dropped_when_no_capacity() -> None:
    """모든 건강 드론이 포화면 임무는 드롭되어 재계획 큐로 반환된다."""
    # Arrange: max 1 task/drone, B·C를 미리 채움
    healer = _healer(max_tasks=1)
    healer.assign_task(Task("b1", (100.0, 0.0, 0.0)), "B")
    healer.assign_task(Task("c1", (200.0, 0.0, 0.0)), "C")
    healer.assign_task(Task("a1", (0.0, 0.0, 0.0)), "A")

    # Act
    report = healer.mark_failed("A")

    # Assert
    assert report.healed_count == 0
    assert report.dropped == ("a1",)
    assert not report.is_fully_healed


def test_higher_priority_task_reassigned_first() -> None:
    """용량이 1건만 남으면 우선순위 높은 임무가 먼저 재분배된다."""
    # Arrange: 용량 2, A는 임무 2건 보유. B는 1건 선점되어 여유 슬롯 1개만 남음.
    healer = SwarmSelfHealer(max_tasks_per_drone=2)
    healer.add_drone("A", (0.0, 0.0, 0.0))
    healer.add_drone("B", (1.0, 0.0, 0.0))
    healer.assign_task(Task("b_pre", (1.0, 0.0, 0.0)), "B")
    healer.assign_task(Task("low", (0.0, 0.0, 0.0), priority=1), "A")
    healer.assign_task(Task("high", (0.0, 0.0, 0.0), priority=9), "A")

    # Act
    report = healer.mark_failed("A")

    # Assert
    assert report.reassignments[0].task_id == "high"
    assert report.dropped == ("low",)


def test_load_balancing_prefers_least_loaded_at_equal_distance() -> None:
    """거리가 같으면 부하가 적은 드론을 선택한다."""
    # Arrange: B·C 동일 위치, B에 임무 1건 선점
    healer = SwarmSelfHealer(max_tasks_per_drone=5)
    healer.add_drone("A", (0.0, 0.0, 0.0))
    healer.add_drone("B", (50.0, 0.0, 0.0))
    healer.add_drone("C", (50.0, 0.0, 0.0))
    healer.assign_task(Task("pre", (50.0, 0.0, 0.0)), "B")
    healer.assign_task(Task("orphan", (50.0, 0.0, 0.0)), "A")

    # Act
    report = healer.mark_failed("A")

    # Assert: 거리 동률 → 부하 적은 C 선택
    assert report.reassignments[0].to_drone == "C"


def test_mark_failed_is_idempotent() -> None:
    """이미 결손된 드론을 다시 처리해도 빈 리포트(부작용 없음)."""
    healer = _healer()
    healer.assign_task(Task("t1", (0.0, 0.0, 0.0)), "A")
    first = healer.mark_failed("A")
    second = healer.mark_failed("A")
    assert first.healed_count == 1
    assert second.healed_count == 0
    assert second.reassignments == ()


def test_mark_failed_unknown_drone_returns_empty_report() -> None:
    """미등록 드론 결손 처리는 빈 리포트."""
    healer = _healer()
    report = healer.mark_failed("ZZZ")
    assert report.failed_drone == "ZZZ"
    assert report.healed_count == 0
    assert report.dropped == ()


def test_assign_rejects_overloaded_or_failed_drone() -> None:
    """용량 초과·결손 드론·미등록 드론 할당은 거부된다."""
    healer = SwarmSelfHealer(max_tasks_per_drone=1)
    healer.add_drone("A", (0.0, 0.0, 0.0))
    assert healer.assign_task(Task("t1", (0.0, 0.0, 0.0)), "A") is True
    assert healer.assign_task(Task("t2", (0.0, 0.0, 0.0)), "A") is False  # 포화
    assert healer.assign_task(Task("t3", (0.0, 0.0, 0.0)), "ghost") is False  # 미등록
    healer.mark_failed("A")
    assert healer.assign_task(Task("t4", (0.0, 0.0, 0.0)), "A") is False  # 결손


def test_heal_swarm_handles_multiple_failures_deterministically() -> None:
    """다수 동시 결손을 ID 순서로 결정적으로 재분배한다."""
    healer = _healer()
    healer.assign_task(Task("ta", (0.0, 0.0, 0.0)), "A")
    healer.assign_task(Task("tb", (100.0, 0.0, 0.0)), "B")

    reports = heal_swarm(healer, ["B", "A"])

    # 정렬되어 A 먼저 처리
    assert [r.failed_drone for r in reports] == ["A", "B"]
    # 모든 임무가 유일 생존 드론 C로 흡수
    assert healer.drone_load("C") == 2
    assert all(r.is_fully_healed for r in reports)


def test_rejects_invalid_capacity() -> None:
    """max_tasks_per_drone < 1 은 거부된다."""
    with pytest.raises(ValueError):
        SwarmSelfHealer(max_tasks_per_drone=0)


def test_duplicate_drone_registration_rejected() -> None:
    """동일 ID 중복 등록은 거부된다."""
    healer = SwarmSelfHealer()
    healer.add_drone("A", (0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        healer.add_drone("A", (1.0, 1.0, 1.0))
