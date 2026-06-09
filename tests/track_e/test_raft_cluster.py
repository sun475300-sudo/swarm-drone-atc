"""P741 Raft 합의 루프 통합 검증 — 선거·복제·페일오버 (결정론적)."""
from __future__ import annotations

from src.raft.airspace_controller_ha import NodeRole, RaftConfig
from src.raft.raft_cluster import InMemoryRaftCluster


def _cluster(n: int = 3, seed: int = 0) -> InMemoryRaftCluster:
    """n개 노드 클러스터 생성 + 시작."""
    c = InMemoryRaftCluster([f"n{i}" for i in range(n)], seed=seed)
    c.start()
    return c


def test_cluster_elects_single_leader() -> None:
    """타임아웃 만료 후 정확히 하나의 리더가 선출된다."""
    cluster = _cluster()
    leader = cluster.run_until_leader()
    assert leader is not None
    assert len(cluster.leaders()) == 1
    assert leader.state.role == NodeRole.LEADER


def test_followers_recognize_leader_term() -> None:
    """선거 후 팔로워가 리더의 term을 공유한다."""
    cluster = _cluster()
    leader = cluster.run_until_leader()
    assert leader is not None
    for node in cluster.nodes.values():
        assert node.state.current_term == leader.state.current_term


def test_leader_replicates_command_to_followers() -> None:
    """리더 replicate → 과반 커밋 + 팔로워 로그 복제."""
    cluster = _cluster()
    leader = cluster.run_until_leader()
    assert leader is not None
    assert leader.replicate({"type": "advisory", "drone_id": "DR-001"}) is True
    assert leader.state.commit_index == 0
    followers = [n for n in cluster.nodes.values() if n is not leader]
    replicated = [n for n in followers if len(n.state.log) == 1]
    assert len(replicated) >= 1  # 과반(자신 포함)이면 최소 1 팔로워 복제


def test_failover_elects_new_leader_after_kill() -> None:
    """리더 장애 시 생존 노드 중 더 높은 term의 새 리더 선출."""
    cluster = _cluster()
    leader = cluster.run_until_leader()
    assert leader is not None
    old_term = leader.state.current_term
    cluster.kill(leader.node_id)

    new_leader = cluster.run_until_leader()
    assert new_leader is not None
    assert new_leader.node_id != leader.node_id
    assert new_leader.state.current_term > old_term


def test_replicate_fails_without_majority() -> None:
    """과반 피어 장애 시 커밋 불가 → replicate False."""
    cluster = _cluster()
    leader = cluster.run_until_leader()
    assert leader is not None
    # 3노드 중 리더 외 2개를 모두 죽이면 과반(2) 미달
    for nid in list(cluster.nodes):
        if nid != leader.node_id:
            cluster.kill(nid)
    assert leader.replicate({"type": "advisory"}) is False


def test_leader_stable_without_failures() -> None:
    """장애 없으면 추가 틱에도 리더가 유지된다 (불필요한 재선거 없음)."""
    cluster = _cluster()
    leader = cluster.run_until_leader()
    assert leader is not None
    term_after_election = leader.state.current_term
    cluster.tick(20)
    assert cluster.leader() is leader
    assert leader.state.current_term == term_after_election


def test_election_is_deterministic_with_seed() -> None:
    """같은 seed → 같은 리더 (재현성)."""
    c1 = InMemoryRaftCluster(["a", "b", "c"], seed=7)
    c2 = InMemoryRaftCluster(["a", "b", "c"], seed=7)
    c1.start()
    c2.start()
    l1 = c1.run_until_leader()
    l2 = c2.run_until_leader()
    assert l1 is not None and l2 is not None
    assert l1.node_id == l2.node_id


def test_custom_config_faster_heartbeat() -> None:
    """RaftConfig 커스텀 타이밍으로도 선거가 수렴한다."""
    cfg = RaftConfig(election_timeout_ms=(100, 200), heartbeat_interval_ms=25)
    cluster = InMemoryRaftCluster(["x", "y", "z"], cfg=cfg, seed=3)
    cluster.start()
    assert cluster.run_until_leader() is not None
