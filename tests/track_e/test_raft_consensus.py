"""P741 Raft 합의 루프 실구현 검증 — 선거·quorum 복제·페일오버.

인메모리 결정론적 `RaftCluster`로 네트워크 없이 합의 동작을 검증한다.
재현성을 위해 `np.random.default_rng(seed)` 사용.
"""
from __future__ import annotations

from src.raft.airspace_controller_ha import NodeRole, RaftCluster


def test_cluster_elects_single_leader() -> None:
    """선거 루프 → 정확히 1명의 리더가 선출된다."""
    cluster = RaftCluster(["c1", "c2", "c3"], seed=0)
    cluster.run_until_leader(max_ticks=200)
    leaders = [n for n in cluster.nodes.values() if n.is_leader()]
    assert len(leaders) == 1
    assert cluster.leader() is leaders[0]


def test_leader_term_is_consistent_across_followers() -> None:
    """리더 선출 후 팔로워들은 리더의 term으로 수렴한다."""
    cluster = RaftCluster(["c1", "c2", "c3"], seed=1)
    cluster.run_until_leader(max_ticks=200)
    leader = cluster.leader()
    assert leader is not None
    for node in cluster.nodes.values():
        assert node.state.current_term == leader.state.current_term


def test_replicate_commits_with_quorum() -> None:
    """리더 replicate → 과반 복제 후 commit, 팔로워 로그 수렴."""
    cluster = RaftCluster(["c1", "c2", "c3"], seed=2)
    cluster.run_until_leader(max_ticks=200)
    leader = cluster.leader()
    assert leader is not None
    assert leader.replicate({"type": "advisory", "drone_id": "DR-007"}) is True
    assert leader.state.commit_index == len(leader.state.log) - 1
    # 과반(2/3 이상) 노드가 엔트리를 보유
    holders = sum(1 for n in cluster.nodes.values() if n.state.log)
    assert holders >= 2


def test_replicate_fails_without_quorum() -> None:
    """과반 노드 다운 시 replicate는 commit하지 못한다."""
    cluster = RaftCluster(["c1", "c2", "c3"], seed=3)
    cluster.run_until_leader(max_ticks=200)
    leader = cluster.leader()
    assert leader is not None
    # 두 팔로워 모두 다운 → 리더만 생존(1/3) → quorum 미달
    for nid in list(cluster.nodes):
        if nid != leader.node_id:
            cluster.kill(nid)
    assert leader.replicate({"type": "rtl"}) is False


def test_failover_elects_new_leader() -> None:
    """리더 다운 → 페일오버로 새 리더 선출."""
    cluster = RaftCluster(["c1", "c2", "c3"], seed=4)
    cluster.run_until_leader(max_ticks=200)
    old = cluster.leader()
    assert old is not None
    old_id = old.node_id
    cluster.kill(old_id)
    cluster.run_until_leader(max_ticks=400)
    new = cluster.leader()
    assert new is not None
    assert new.node_id != old_id
    assert new.state.current_term > old.state.current_term


def test_killed_node_does_not_vote() -> None:
    """다운된 노드는 투표/AppendEntries에 응답하지 않는다."""
    cluster = RaftCluster(["c1", "c2"], seed=5)
    cluster.kill("c2")
    granted = cluster.send_request_vote("c1", "c2", term=1, last_log_index=0, last_log_term=0)
    assert granted is False


def test_single_node_cluster_self_elects() -> None:
    """단일 노드 클러스터는 스스로 리더가 된다(과반=1)."""
    cluster = RaftCluster(["solo"], seed=0)
    cluster.run_until_leader(max_ticks=100)
    leader = cluster.leader()
    assert leader is not None and leader.node_id == "solo"
    assert leader.replicate({"type": "advisory"}) is True


def test_revive_node_rejoins_as_follower() -> None:
    """복구된 노드는 팔로워로 재합류하고 리더 하트비트로 수렴."""
    cluster = RaftCluster(["c1", "c2", "c3"], seed=6)
    cluster.run_until_leader(max_ticks=200)
    leader = cluster.leader()
    assert leader is not None
    follower_id = next(n for n in cluster.nodes if n != leader.node_id)
    cluster.kill(follower_id)
    cluster.tick_n(20)
    cluster.revive(follower_id)
    cluster.tick_n(50)
    revived = cluster.nodes[follower_id]
    assert revived.state.role == NodeRole.FOLLOWER
    assert revived.state.leader_id is not None
