"""P741 실제 Raft 합의 루프 검증 — 선거·quorum 복제·페일오버.

스캐폴드(`test_raft.py`)의 RPC 핸들러 단위 테스트와 달리,
여기서는 `RaftCluster` 인메모리 하니스로 다중 노드 합의를 결정론적으로 검증한다.
"""
from __future__ import annotations

from src.raft.airspace_controller_ha import NodeRole
from src.raft.cluster import RaftCluster


def test_cluster_elects_single_leader() -> None:
    """선거: 다중 노드에서 정확히 1명의 리더 선출."""
    cluster = RaftCluster(["n1", "n2", "n3"], seed=42)
    leader = cluster.run_until_leader()
    assert leader is not None
    leaders = [n for n in cluster.nodes.values() if n.is_leader()]
    assert len(leaders) == 1
    assert leader.state.role == NodeRole.LEADER


def test_followers_recognize_leader_term() -> None:
    """선거 후 팔로워들이 리더의 term을 인지."""
    cluster = RaftCluster(["n1", "n2", "n3"], seed=7)
    leader = cluster.run_until_leader()
    assert leader is not None
    for node in cluster.nodes.values():
        if node is leader:
            continue
        assert node.state.current_term == leader.state.current_term
        assert node.state.leader_id == leader.node_id


def test_replicate_commits_on_quorum() -> None:
    """quorum 복제: 리더 명령이 과반 노드에 복제되고 커밋."""
    cluster = RaftCluster(["n1", "n2", "n3"], seed=123)
    leader = cluster.run_until_leader()
    assert leader is not None

    assert leader.replicate({"type": "advisory", "drone_id": "DR-7"}) is True
    cluster.run(ticks=20)

    # 리더 commit_index가 0번 엔트리를 포함
    assert leader.state.commit_index >= 0
    # 과반(>=2/3) 노드가 해당 엔트리를 로그에 보유
    have_entry = sum(
        1 for n in cluster.nodes.values()
        if n.state.log and n.state.log[0].command.get("drone_id") == "DR-7"
    )
    assert have_entry >= 2


def test_leader_failover_elects_new_leader() -> None:
    """페일오버: 리더 정지 시 남은 노드가 새 리더 선출."""
    cluster = RaftCluster(["n1", "n2", "n3"], seed=99)
    old_leader = cluster.run_until_leader()
    assert old_leader is not None
    old_term = old_leader.state.current_term

    cluster.stop(old_leader.node_id)
    new_leader = cluster.run_until_leader(exclude={old_leader.node_id})

    assert new_leader is not None
    assert new_leader.node_id != old_leader.node_id
    assert new_leader.state.current_term > old_term


def test_committed_entry_survives_failover() -> None:
    """커밋된 엔트리는 페일오버 후에도 새 리더 로그에 보존."""
    cluster = RaftCluster(["n1", "n2", "n3"], seed=2024)
    leader = cluster.run_until_leader()
    assert leader is not None
    leader.replicate({"type": "rtl", "drone_id": "DR-X"})
    cluster.run(ticks=30)

    cluster.stop(leader.node_id)
    new_leader = cluster.run_until_leader(exclude={leader.node_id})
    assert new_leader is not None
    assert any(
        e.command.get("drone_id") == "DR-X" for e in new_leader.state.log
    )


def test_no_split_brain_after_partition_heal() -> None:
    """정지했던 구 리더 재가동 후에도 리더는 1명 (term 우선)."""
    cluster = RaftCluster(["n1", "n2", "n3"], seed=555)
    old_leader = cluster.run_until_leader()
    assert old_leader is not None
    cluster.stop(old_leader.node_id)
    cluster.run_until_leader(exclude={old_leader.node_id})

    # 구 리더 재가동 → 더 높은 term의 AppendEntries 수신 시 step down
    cluster.start(old_leader.node_id)
    cluster.run(ticks=50)
    leaders = [n for n in cluster.nodes.values() if n.is_leader()]
    assert len(leaders) == 1
