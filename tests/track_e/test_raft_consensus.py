"""P741 Raft 합의 루프(선거·quorum 복제·페일오버) 검증.

기존 `test_raft.py`가 RPC 핸들러 단위를 검증한다면, 본 파일은
인메모리 클러스터(`RaftCluster`) 위에서 실제 합의 동작을 검증한다.
네트워크 대신 결정적(deterministic) 인메모리 전송을 사용해 타이밍
플레이키니스 없이 선거·복제·페일오버를 재현한다.
"""
from __future__ import annotations

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    LogEntry,
    NodeRole,
    RaftCluster,
)


def test_cluster_elects_single_leader() -> None:
    """3-노드 클러스터에서 선거 후 정확히 1명의 리더."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    assert leader is not None
    assert leader.is_leader()
    leaders = [n for n in cluster.nodes.values() if n.is_leader()]
    assert len(leaders) == 1


def test_election_increments_term_and_self_votes() -> None:
    """후보가 되면 term 증가 + 자기 자신에게 투표."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    node = cluster.nodes["ctrl-1"]
    won = node.become_candidate()
    assert won is True
    assert node.state.current_term == 1
    assert node.state.voted_for == "ctrl-1"


def test_leader_replicates_to_quorum_and_commits() -> None:
    """리더가 명령을 복제하면 과반 ack 시 커밋된다."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    ok = leader.replicate({"type": "advisory", "drone_id": "DR-007"})
    assert ok is True
    assert leader.state.commit_index == leader.state.log[-1].index
    # 팔로워들도 동일 엔트리를 받았는지
    for node in cluster.nodes.values():
        assert node.state.log[-1].command["drone_id"] == "DR-007"


def test_replicate_fails_without_quorum() -> None:
    """과반 노드가 죽으면 복제 실패(커밋 안 됨)."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    # 리더 외 2개 모두 실패 → 과반 ack 불가
    for nid in cluster.nodes:
        if nid != leader.node_id:
            cluster.fail(nid)
    ok = leader.replicate({"type": "rtl"})
    assert ok is False
    # 로그에는 append 되지만 commit_index는 진행 안 됨
    assert leader.state.commit_index < leader.state.log[-1].index


def test_failover_elects_new_leader_after_leader_dies() -> None:
    """리더 장애 시 살아있는 노드 중 새 리더 선출."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    old = cluster.elect_leader()
    old_term = old.state.current_term
    cluster.fail(old.node_id)
    new = cluster.elect_leader()
    assert new is not None
    assert new.node_id != old.node_id
    assert new.is_leader()
    assert new.state.current_term > old_term


def test_append_entries_rejects_log_inconsistency() -> None:
    """prev_log 불일치 시 AppendEntries 거부 (Raft §5.3)."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    # 팔로워 로그는 비어있는데 리더가 index=1 부터 보내려 함 → 거부
    entry = LogEntry(term=1, index=1, command={"type": "advisory"})
    ok = node.on_append_entries(
        "ctrl-2", term=1, entries=[entry], commit_index=1,
        prev_log_index=0, prev_log_term=1,
    )
    assert ok is False
    assert len(node.state.log) == 0


def test_append_entries_accepts_matching_prev_log() -> None:
    """prev_log 일치 시 엔트리 수용."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.state.log = [LogEntry(term=1, index=0, command={"type": "init"})]
    entry = LogEntry(term=1, index=1, command={"type": "advisory"})
    ok = node.on_append_entries(
        "ctrl-2", term=1, entries=[entry], commit_index=1,
        prev_log_index=0, prev_log_term=1,
    )
    assert ok is True
    assert len(node.state.log) == 2


def test_failed_node_does_not_vote() -> None:
    """실패한 노드는 투표에 참여하지 않아 quorum 계산에서 제외."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    cluster.fail("ctrl-3")
    leader = cluster.elect_leader()
    # 살아있는 2/3 노드로 여전히 과반(2 > 1) 달성 가능
    assert leader is not None
    assert leader.is_leader()


def test_stale_leader_steps_down_on_higher_term() -> None:
    """더 높은 term의 AppendEntries 수신 시 리더가 팔로워로 강등."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    leader.on_append_entries(
        "ctrl-9", term=leader.state.current_term + 5, entries=[], commit_index=0,
    )
    assert leader.state.role == NodeRole.FOLLOWER
    assert leader.state.leader_id == "ctrl-9"
