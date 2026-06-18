"""ODYSSEY Phase 423 — 지역 간 관제권 핸드오버 단위 테스트.

외부 의존성 0(순수 결정적). Phase 421 디스커버리 서비스 위에서 동작한다.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_handover import (
    ACQUIRED,
    CONTINGENT,
    HANDOVER,
    RETAINED,
    HandoverCoordinator,
)


def _two_instance_service() -> FederationDiscoveryService:
    """경계를 공유하는 두 인스턴스: 서편[0,1000) · 동편[1000,2000) (x축)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("WEST", Volume4D(0, 1000, 0, 1000, 0, 120, 0, 600))
    svc.register("EAST", Volume4D(1000, 2000, 0, 1000, 0, 120, 0, 600))
    return svc


def test_assign_sets_initial_controller() -> None:
    # Arrange
    svc = _two_instance_service()
    coord = HandoverCoordinator(svc)

    # Act
    coord.assign("D1", "WEST")

    # Assert
    assert coord.controller_of("D1") == "WEST"


def test_assign_unknown_instance_raises() -> None:
    svc = _two_instance_service()
    coord = HandoverCoordinator(svc)
    with pytest.raises(KeyError):
        coord.assign("D1", "NOWHERE")


def test_assign_empty_drone_id_raises() -> None:
    svc = _two_instance_service()
    coord = HandoverCoordinator(svc)
    with pytest.raises(ValueError):
        coord.assign("", "WEST")


def test_retained_when_drone_stays_in_controller_volume() -> None:
    # Arrange
    coord = HandoverCoordinator(_two_instance_service())
    coord.assign("D1", "WEST")

    # Act — 서편 내부 점
    event = coord.update("D1", 500, 500, 60, 100)

    # Assert
    assert event.decision == RETAINED
    assert event.to_instance == "WEST"
    assert coord.controller_of("D1") == "WEST"
    assert coord.handover_count() == 0


def test_handover_when_crossing_boundary_into_neighbor() -> None:
    # Arrange
    coord = HandoverCoordinator(_two_instance_service())
    coord.assign("D1", "WEST")

    # Act — 동편으로 진입
    event = coord.update("D1", 1500, 500, 60, 100)

    # Assert
    assert event.decision == HANDOVER
    assert event.from_instance == "WEST"
    assert event.to_instance == "EAST"
    assert coord.controller_of("D1") == "EAST"
    assert coord.handover_count() == 1


def test_contingent_when_outside_all_coverage() -> None:
    # Arrange
    coord = HandoverCoordinator(_two_instance_service())
    coord.assign("D1", "WEST")

    # Act — 두 공역 모두 벗어난 점 (x ≥ 2000)
    event = coord.update("D1", 3000, 500, 60, 100)

    # Assert — 관제권은 보유, 비상만 표시
    assert event.decision == CONTINGENT
    assert event.to_instance is None
    assert event.from_instance == "WEST"
    assert coord.controller_of("D1") == "WEST"


def test_boundary_point_is_half_open_belongs_to_east() -> None:
    # 정확히 x=1000 경계: 반열린 구간 규약상 EAST 에만 귀속.
    coord = HandoverCoordinator(_two_instance_service())
    coord.assign("D1", "WEST")
    event = coord.update("D1", 1000, 500, 60, 100)
    assert event.candidates == ("EAST",)
    assert event.decision == HANDOVER
    assert event.to_instance == "EAST"


def test_hysteresis_retains_controller_in_overlap_zone() -> None:
    # 두 공역이 겹치는 구역에서는 현 관제권을 유지(진동 방지).
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("WEST", Volume4D(0, 1200, 0, 1000, 0, 120, 0, 600))
    svc.register("EAST", Volume4D(800, 2000, 0, 1000, 0, 120, 0, 600))
    coord = HandoverCoordinator(svc)
    coord.assign("D1", "EAST")

    # 중첩 구역(800~1200) 점 — 두 인스턴스 모두 포함하지만 EAST 유지
    event = coord.update("D1", 1000, 500, 60, 100)
    assert set(event.candidates) == {"EAST", "WEST"}
    assert event.decision == RETAINED
    assert coord.controller_of("D1") == "EAST"


def test_initial_acquisition_picks_lowest_id_deterministically() -> None:
    # 미배정 드론이 중첩 구역에서 처음 발견되면 id 사전순 최소로 결정적 이양.
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("BRAVO", Volume4D(0, 1200, 0, 1000, 0, 120, 0, 600))
    svc.register("ALFA", Volume4D(800, 2000, 0, 1000, 0, 120, 0, 600))
    coord = HandoverCoordinator(svc)

    event = coord.update("D1", 1000, 500, 60, 100)
    assert event.decision == ACQUIRED  # 최초 획득은 HANDOVER 와 구분
    assert event.from_instance is None
    assert event.to_instance == "ALFA"  # 사전순 최소


def test_audit_log_preserves_order_and_seq() -> None:
    coord = HandoverCoordinator(_two_instance_service())
    coord.assign("D1", "WEST")
    coord.update("D1", 500, 500, 60, 100)   # RETAINED
    coord.update("D1", 1500, 500, 60, 200)  # HANDOVER
    coord.update("D1", 3000, 500, 60, 300)  # CONTINGENT

    log = coord.log()
    assert [e.seq for e in log] == [1, 2, 3]
    assert [e.decision for e in log] == [RETAINED, HANDOVER, CONTINGENT]


def test_update_empty_drone_id_raises() -> None:
    coord = HandoverCoordinator(_two_instance_service())
    with pytest.raises(ValueError):
        coord.update("", 500, 500, 60, 100)


def test_update_unassigned_drone_acquires_control() -> None:
    # assign 없이 update — 커버하는 인스턴스가 있으면 None→해당 인스턴스 획득(ACQUIRED).
    coord = HandoverCoordinator(_two_instance_service())
    event = coord.update("D9", 500, 500, 60, 100)
    assert event.from_instance is None
    assert event.decision == ACQUIRED
    assert event.to_instance == "WEST"
    assert coord.controller_of("D9") == "WEST"
    assert coord.handover_count() == 0  # 획득은 인스턴스 간 이양이 아님


def test_unassigned_drone_outside_all_coverage_is_contingent() -> None:
    # 한 번도 배정된 적 없는 드론이 모든 커버리지 밖이면 CONTINGENT, from/to 모두 None.
    coord = HandoverCoordinator(_two_instance_service())
    event = coord.update("DX", 9999, 9999, 60, 100)
    assert event.decision == CONTINGENT
    assert event.from_instance is None
    assert event.to_instance is None
    assert coord.controller_of("DX") is None


def test_determinism_same_sequence_same_log() -> None:
    def run() -> list[tuple]:
        coord = HandoverCoordinator(_two_instance_service())
        coord.assign("D1", "WEST")
        path = [(500, 500, 60, 100), (1500, 500, 60, 200), (1500, 500, 60, 250)]
        for x, y, z, t in path:
            coord.update("D1", x, y, z, t)
        return [
            (e.seq, e.decision, e.from_instance, e.to_instance, e.candidates)
            for e in coord.log()
        ]

    assert run() == run()


def test_time_window_exit_is_contingent() -> None:
    # 시간 창(t<600) 밖이면 어떤 볼륨도 포함하지 않아 CONTINGENT.
    coord = HandoverCoordinator(_two_instance_service())
    coord.assign("D1", "WEST")
    event = coord.update("D1", 500, 500, 60, 999)
    assert event.decision == CONTINGENT
    assert event.candidates == ()


def test_covering_helper_on_discovery_service() -> None:
    # Phase 421 디스커버리에 추가된 점 커버리지 프리미티브 직접 검증.
    svc = _two_instance_service()
    assert svc.covering(500, 500, 60, 100) == ("WEST",)
    assert svc.covering(1500, 500, 60, 100) == ("EAST",)
    assert svc.covering(5000, 500, 60, 100) == ()
