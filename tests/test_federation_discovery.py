"""ODYSSEY Phase 421 (Federation): 인스턴스 간 디스커버리 프로토콜 테스트.

DSS 유사 디스커버리·동기화 서비스의 4D 교차 판정·셀 인덱싱·결정성을 검증한다.
"""

import pytest

from simulation.federation_discovery import (
    DEFAULT_CELL_SIZE_M,
    FederationDiscoveryService,
    Subscription,
    Volume4D,
)


def _vol(
    x0: float = 0.0,
    x1: float = 100.0,
    y0: float = 0.0,
    y1: float = 100.0,
    z0: float = 0.0,
    z1: float = 120.0,
    t0: float = 0.0,
    t1: float = 600.0,
) -> Volume4D:
    return Volume4D(x0, x1, y0, y1, z0, z1, t0, t1)


# ── Volume4D 검증 ──────────────────────────────────────────────


def test_volume_rejects_degenerate_axis():
    # Arrange / Act / Assert: max <= min 인 축은 ValueError
    with pytest.raises(ValueError):
        _vol(x0=100.0, x1=100.0)
    with pytest.raises(ValueError):
        _vol(t0=600.0, t1=0.0)


def test_overlap_is_symmetric_and_excludes_touching_boundary():
    # Arrange
    a = _vol(x0=0.0, x1=100.0)
    b = _vol(x0=100.0, x1=200.0)  # x로 경계만 접촉
    c = _vol(x0=50.0, x1=150.0)  # x로 실제 겹침

    # Act / Assert: 경계 접촉은 비교차, 실제 겹침은 양방향 대칭
    assert a.overlaps(b) is False
    assert b.overlaps(a) is False
    assert a.overlaps(c) is True
    assert c.overlaps(a) is True


def test_overlap_requires_all_four_axes():
    # Arrange: x·y·z 는 겹치되 시간 창만 분리
    a = _vol(t0=0.0, t1=300.0)
    b = _vol(t0=400.0, t1=700.0)

    # Act / Assert: 한 축이라도 분리되면 비교차
    assert a.overlaps(b) is False


# ── 등록·디스커버리 ────────────────────────────────────────────


def test_register_returns_neighbors_for_overlapping_instances():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol(x0=0.0, x1=200.0))

    # Act: 겹치는 볼륨으로 두 번째 인스턴스 등록
    sub = svc.register("uss-b", _vol(x0=100.0, x1=300.0))

    # Assert
    assert isinstance(sub, Subscription)
    assert sub.neighbors == ("uss-a",)
    assert sub.version == 2


def test_register_returns_no_neighbor_for_disjoint_volume():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol(x0=0.0, x1=100.0))

    # Act: 공간적으로 멀리 떨어진(다른 셀) 볼륨
    sub = svc.register("uss-b", _vol(x0=5000.0, x1=5100.0))

    # Assert
    assert sub.neighbors == ()


def test_query_returns_sorted_overlapping_instances():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-c", _vol(x0=0.0, x1=300.0))
    svc.register("uss-a", _vol(x0=100.0, x1=400.0))
    svc.register("uss-b", _vol(x0=200.0, x1=500.0))

    # Act
    result = svc.query(_vol(x0=150.0, x1=250.0))

    # Assert: 정렬된 결과
    assert result == ("uss-a", "uss-b", "uss-c")


def test_query_excludes_self():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol())

    # Act
    result = svc.query(_vol(), exclude="uss-a")

    # Assert
    assert result == ()


# ── 갱신·제거·동기화 ───────────────────────────────────────────


def test_reregister_updates_volume_and_clears_stale_neighbors():
    # Arrange: a·b 가 겹쳐 있다가 b 가 멀리 이동
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol(x0=0.0, x1=200.0))
    svc.register("uss-b", _vol(x0=100.0, x1=300.0))
    assert svc.synchronization_targets("uss-a") == ("uss-b",)

    # Act: b 를 분리된 영역으로 재등록(갱신)
    svc.register("uss-b", _vol(x0=9000.0, x1=9100.0))

    # Assert: a 의 동기화 대상에서 b 가 사라짐, 인스턴스 수는 그대로
    assert svc.synchronization_targets("uss-a") == ()
    assert svc.instances() == ("uss-a", "uss-b")


def test_remove_unregisters_instance_and_unknown_raises():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol())

    # Act
    svc.remove("uss-a")

    # Assert
    assert svc.instances() == ()
    with pytest.raises(KeyError):
        svc.remove("uss-a")


def test_synchronization_targets_is_mutual():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol(x0=0.0, x1=200.0))
    svc.register("uss-b", _vol(x0=100.0, x1=300.0))

    # Act / Assert: 동기화 관계는 상호적
    assert svc.synchronization_targets("uss-a") == ("uss-b",)
    assert svc.synchronization_targets("uss-b") == ("uss-a",)


# ── 결정성·요약·검증 ───────────────────────────────────────────


def test_summary_tracks_state_deterministically():
    # Arrange
    svc = FederationDiscoveryService()
    svc.register("uss-a", _vol(x0=0.0, x1=100.0))
    svc.register("uss-b", _vol(x0=2000.0, x1=2100.0))

    # Act
    summary = svc.summary()

    # Assert
    assert summary["instances"] == 2
    assert summary["version"] == 2
    assert summary["occupied_cells"] >= 2


def test_results_are_order_independent():
    # Arrange: 등록 순서를 바꿔도 동일한 디스커버리 결과
    svc1 = FederationDiscoveryService()
    svc2 = FederationDiscoveryService()
    vols = {
        "x": _vol(x0=0.0, x1=300.0),
        "y": _vol(x0=100.0, x1=400.0),
        "z": _vol(x0=200.0, x1=500.0),
    }
    for iid in ("x", "y", "z"):
        svc1.register(iid, vols[iid])
    for iid in ("z", "y", "x"):
        svc2.register(iid, vols[iid])

    # Act / Assert
    probe = _vol(x0=150.0, x1=250.0)
    assert svc1.query(probe) == svc2.query(probe) == ("x", "y", "z")


def test_invalid_cell_size_rejected():
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        FederationDiscoveryService(cell_size_m=0.0)
    with pytest.raises(ValueError):
        FederationDiscoveryService(cell_size_m=-100.0)
    assert DEFAULT_CELL_SIZE_M > 0


def test_discovery_works_across_negative_enu_coordinates():
    # Arrange: 원점 중심 ENU 프레임의 음수 좌표(셀 인덱스 내림 정확성)
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("uss-a", _vol(x0=-300.0, x1=-100.0, y0=-300.0, y1=-100.0))

    # Act: 음수 영역에서 겹치는 볼륨과 분리된 볼륨
    overlapping = svc.register("uss-b", _vol(x0=-200.0, x1=200.0, y0=-200.0, y1=200.0))
    disjoint = svc.query(_vol(x0=-5000.0, x1=-4900.0, y0=-5000.0, y1=-4900.0))

    # Assert
    assert overlapping.neighbors == ("uss-a",)
    assert disjoint == ()
