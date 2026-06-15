"""ODYSSEY Phase 425 — 연합 NOTAM 전파 단위 테스트.

외부 의존성 0(순수 결정적). Phase 421 디스커버리 서비스 위에서 동작한다.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_notam import (
    DELIVERED,
    DUPLICATE,
    REVOKED,
    FederationNotamBroadcaster,
)


def _three_instance_service() -> FederationDiscoveryService:
    """x축으로 늘어선 세 인스턴스: 서[0,1000)·중[1000,2000)·동[2000,3000)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("WEST", Volume4D(0, 1000, 0, 1000, 0, 120, 0, 600))
    svc.register("MID", Volume4D(1000, 2000, 0, 1000, 0, 120, 0, 600))
    svc.register("EAST", Volume4D(2000, 3000, 0, 1000, 0, 120, 0, 600))
    return svc


def _nfz(x_min: float, x_max: float) -> Volume4D:
    """전 고도·전 시간 창을 덮는, x축으로만 구분되는 NFZ 볼륨."""
    return Volume4D(x_min, x_max, 0, 1000, 0, 120, 0, 600)


# --- 발효·전파 기본 ---------------------------------------------------------


def test_issue_delivers_only_to_overlapping_neighbors() -> None:
    # Arrange — WEST가 [900,1100) NFZ 발효 → MID와만 겹침(EAST 비겹침).
    bc = FederationNotamBroadcaster(_three_instance_service())

    # Act
    events = bc.issue("WEST", "N1", _nfz(900, 1100))

    # Assert
    assert [e.decision for e in events] == [DELIVERED]
    assert events[0].target == "MID"
    assert [n.notam_id for n in bc.inbox("MID")] == ["N1"]
    assert bc.inbox("EAST") == ()
    # 발효 인스턴스 자신은 인박스에 담지 않는다.
    assert bc.inbox("WEST") == ()


def test_issue_to_multiple_overlapping_neighbors_sorted() -> None:
    # Arrange — 중앙을 넓게 덮어 WEST·EAST 모두와 겹침.
    bc = FederationNotamBroadcaster(_three_instance_service())

    # Act — MID가 [500,2500) 발효 → WEST·EAST 둘 다 겹침.
    events = bc.issue("MID", "N1", _nfz(500, 2500))

    # Assert — 대상이 사전순(EAST < WEST)으로 정렬돼 전달된다.
    assert [e.target for e in events] == ["EAST", "WEST"]
    assert all(e.decision == DELIVERED for e in events)


def test_issue_unregistered_origin_raises() -> None:
    bc = FederationNotamBroadcaster(_three_instance_service())
    with pytest.raises(ValueError):
        bc.issue("GHOST", "N1", _nfz(900, 1100))


def test_issue_empty_notam_id_raises() -> None:
    bc = FederationNotamBroadcaster(_three_instance_service())
    with pytest.raises(ValueError):
        bc.issue("WEST", "", _nfz(900, 1100))


def test_issue_conflicting_origin_for_same_id_raises() -> None:
    # Arrange — N1을 WEST가 발효한 뒤 EAST가 같은 id 재발효 시도.
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("WEST", "N1", _nfz(900, 1100))

    # Act / Assert
    with pytest.raises(ValueError):
        bc.issue("EAST", "N1", _nfz(2400, 2600))


# --- 재방송 멱등성 (DUPLICATE) ---------------------------------------------


def test_rebroadcast_same_version_is_duplicate() -> None:
    # Arrange
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("WEST", "N1", _nfz(900, 1100))

    # Act — 같은 개정 재방송.
    events = bc.rebroadcast("N1")

    # Assert — 이미 같은 버전을 보유한 MID는 DUPLICATE.
    assert [e.decision for e in events] == [DUPLICATE]
    assert events[0].target == "MID"


def test_rebroadcast_unknown_notam_raises() -> None:
    bc = FederationNotamBroadcaster(_three_instance_service())
    with pytest.raises(KeyError):
        bc.rebroadcast("NOPE")


# --- 재발효(개정) 버전 증가 -------------------------------------------------


def test_reissue_bumps_version_and_redelivers() -> None:
    # Arrange
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("WEST", "N1", _nfz(900, 1100))

    # Act — 같은 NFZ 재발효(개정).
    events = bc.issue("WEST", "N1", _nfz(900, 1100))

    # Assert — 새 버전(2)으로 DELIVERED.
    assert [e.decision for e in events] == [DELIVERED]
    assert events[0].version == 2
    assert bc.inbox("MID")[0].version == 2


# --- 동적 NFZ 이동 → stale 회수 (REVOKED) ----------------------------------


def test_nfz_moving_out_of_neighbor_revokes_stale() -> None:
    # Arrange — 처음 [900,1100): MID와 겹침.
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("WEST", "N1", _nfz(900, 1100))
    assert [n.notam_id for n in bc.inbox("MID")] == ["N1"]

    # Act — NFZ가 WEST 내부 [100,300)로 이동 → MID와 더는 겹치지 않음.
    events = bc.issue("WEST", "N1", _nfz(100, 300))

    # Assert — MID 인박스에서 회수, 결정은 REVOKED.
    assert REVOKED in [e.decision for e in events]
    assert bc.inbox("MID") == ()


def test_nfz_moving_to_new_neighbor_delivers_there() -> None:
    # Arrange — 처음 MID와 겹침.
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("MID", "N1", _nfz(1400, 1600))
    assert bc.inbox("WEST") == ()
    assert bc.inbox("EAST") == ()

    # Act — [900,2100)로 확장 → WEST·EAST 둘 다 겹침.
    bc.issue("MID", "N1", _nfz(900, 2100))

    # Assert
    assert [n.notam_id for n in bc.inbox("WEST")] == ["N1"]
    assert [n.notam_id for n in bc.inbox("EAST")] == ["N1"]


# --- 철회 (revoke) ----------------------------------------------------------


def test_revoke_removes_from_all_holders() -> None:
    # Arrange — WEST·EAST 둘 다 보유.
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("MID", "N1", _nfz(500, 2500))
    assert bc.inbox("WEST") and bc.inbox("EAST")

    # Act
    events = bc.revoke("N1")

    # Assert — 보유 이웃에서 모두 회수(사전순), 활성 NOTAM 0.
    assert [e.decision for e in events] == [REVOKED, REVOKED]
    assert [e.target for e in events] == ["EAST", "WEST"]
    assert bc.inbox("WEST") == () and bc.inbox("EAST") == ()
    assert bc.summary()["active_notams"] == 0


def test_revoke_unknown_notam_raises() -> None:
    bc = FederationNotamBroadcaster(_three_instance_service())
    with pytest.raises(KeyError):
        bc.revoke("NOPE")


# --- 소비측 헬퍼 active_volumes --------------------------------------------


def test_active_volumes_returns_held_nfz() -> None:
    # Arrange
    bc = FederationNotamBroadcaster(_three_instance_service())
    vol = _nfz(900, 1100)
    bc.issue("WEST", "N1", vol)

    # Act
    vols = bc.active_volumes("MID")

    # Assert — MID가 회피해야 할 외부 NFZ 볼륨이 그대로 노출된다.
    assert vols == (vol,)


# --- 감사 로그·요약 결정성 --------------------------------------------------


def test_audit_log_is_ordered_and_sequential() -> None:
    # Arrange
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("MID", "N1", _nfz(500, 2500))
    bc.revoke("N1")

    # Act
    log = bc.audit_log()

    # Assert — seq가 1부터 빈틈없이 증가.
    assert [e.seq for e in log] == list(range(1, len(log) + 1))


def test_summary_counts_are_deterministic() -> None:
    # Arrange
    bc = FederationNotamBroadcaster(_three_instance_service())
    bc.issue("MID", "N1", _nfz(500, 2500))

    # Act / Assert
    summary = bc.summary()
    assert summary["active_notams"] == 1
    assert summary["holder_instances"] == 2
    assert summary["events"] == 2


def test_run_is_fully_reproducible() -> None:
    # Arrange — 동일 시퀀스를 두 번 돌려 로그가 완전히 일치하는지 확인.
    def run() -> list[tuple[int, str, str, int, str]]:
        bc = FederationNotamBroadcaster(_three_instance_service())
        bc.issue("MID", "N1", _nfz(500, 2500))
        bc.issue("WEST", "N2", _nfz(900, 1100))
        bc.rebroadcast("N1")
        bc.revoke("N2")
        return [
            (e.seq, e.notam_id, e.target, e.version, e.decision)
            for e in bc.audit_log()
        ]

    # Act / Assert
    assert run() == run()
