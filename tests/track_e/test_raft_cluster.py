"""P741 RaftCluster 통합 검증 — 선거·quorum 복제·페일오버.

결정론적 가상 클럭(step) 구동이므로 seed 고정 시 재현 가능.
"""
from __future__ import annotations

import pytest

from src.raft.airspace_controller_ha import NodeRole, RaftConfig
from src.raft.raft_cluster import RaftCluster


def _cluster(n: int = 3, seed: int = 0) -> RaftCluster:
    """n-노드 클러스터 헬퍼."""
    return RaftCluster([f"ctrl-{i}" for i in range(1, n + 1)], seed=seed)


# --- 선거 (Leader Election) ---

def test_elects_single_leader() -> None:
    """클러스터는 정확히 1명의 리더를 선출한다."""
    cluster = _cluster(3, seed=1)
    leader = cluster.run_until_leader()
    assert leader is not None
    assert leader.is_leader()
    assert len(cluster.leaders()) == 1


def test_no_two_leaders_same_term() -> None:
    """안전성: 어떤 시점에도 동시 리더는 1명 이하."""
    cluster = _cluster(5, seed=2)
    cluster.run_until_leader()
    # 충분히 더 진행해도 동시 리더는 1명을 넘지 않는다.
    for _ in range(500):
        cluster.tick()
        assert len(cluster.leaders()) <= 1


def test_followers_recognize_leader() -> None:
    """리더 선출 후 모든 팔로워가 동일 leader_id를 인지한다."""
    cluster = _cluster(3, seed=3)
    leader = cluster.run_until_leader()
    assert leader is not None
    cluster.run(50)  # 하트비트 전파
    for node in cluster.nodes.values():
        if node is leader:
            continue
        assert node.state.leader_id == leader.node_id
        assert node.state.role == NodeRole.FOLLOWER


def test_single_node_self_elects() -> None:
    """단일 노드 클러스터는 자기 자신을 리더로 선출(quorum=1)."""
    cluster = _cluster(1, seed=0)
    leader = cluster.run_until_leader()
    assert leader is not None
    assert leader.node_id == "ctrl-1"


# --- 복제 (Quorum Replication) ---

def test_propose_commits_with_quorum() -> None:
    """리더 propose → quorum ack → 커밋 + 팔로워 로그 복제."""
    cluster = _cluster(3, seed=4)
    leader = cluster.run_until_leader()
    assert leader is not None
    assert cluster.propose({"type": "advisory", "drone_id": "DR-001"}) is True
    assert leader.state.commit_index == 0
    # 팔로워에 엔트리가 복제되고 커밋 인덱스도 전파되었는지 확인.
    for node in cluster.nodes.values():
        assert len(node.state.log) == 1
        assert node.state.log[0].command["drone_id"] == "DR-001"
        assert node.state.commit_index == 0


def test_propose_fails_without_quorum() -> None:
    """과반 노드 장애 시 복제 실패(커밋 불가)."""
    cluster = _cluster(3, seed=5)
    leader = cluster.run_until_leader()
    assert leader is not None
    # 리더 외 2개를 모두 죽이면 quorum(2/3) 미달.
    others = [nid for nid in cluster.nodes if nid != leader.node_id]
    for nid in others:
        cluster.kill(nid)
    assert cluster.propose({"type": "rtl"}) is False


def test_multiple_proposals_increment_commit_index() -> None:
    """연속 propose는 commit_index를 순차 증가시킨다."""
    cluster = _cluster(3, seed=6)
    leader = cluster.run_until_leader()
    assert leader is not None
    for i in range(3):
        assert cluster.propose({"seq": i}) is True
    assert leader.state.commit_index == 2
    assert len(leader.state.log) == 3


# --- 페일오버 (Failover) ---

def test_failover_elects_new_leader() -> None:
    """리더 장애 시 남은 노드가 새 리더를 선출한다."""
    cluster = _cluster(3, seed=7)
    old_leader = cluster.run_until_leader()
    assert old_leader is not None
    old_term = old_leader.state.current_term

    cluster.kill(old_leader.node_id)
    new_leader = cluster.run_until_leader()
    assert new_leader is not None
    assert new_leader.node_id != old_leader.node_id
    assert new_leader._alive
    # 새 리더의 term은 이전보다 높다.
    assert new_leader.state.current_term > old_term


def test_no_leader_below_quorum() -> None:
    """과반 노드 장애 시 리더 선출 불가(가용성 상실, 안전성 유지)."""
    cluster = _cluster(3, seed=8)
    leader = cluster.run_until_leader()
    assert leader is not None
    # 3개 중 2개 장애 → 남은 1개는 quorum 미달.
    alive_id = leader.node_id
    for nid in list(cluster.nodes):
        if nid != alive_id:
            cluster.kill(nid)
    # 기존 리더까지 죽이면 생존 노드 0 → 새 리더 없음.
    cluster.kill(alive_id)
    assert cluster.run_until_leader(max_steps=500) is None


def test_revived_node_rejoins_as_follower() -> None:
    """복귀 노드는 FOLLOWER로 재합류하고 현 리더를 인지한다."""
    cluster = _cluster(3, seed=9)
    old_leader = cluster.run_until_leader()
    assert old_leader is not None
    cluster.kill(old_leader.node_id)
    new_leader = cluster.run_until_leader()
    assert new_leader is not None

    cluster.revive(old_leader.node_id)
    cluster.run(100)  # 하트비트 전파
    revived = cluster.nodes[old_leader.node_id]
    assert revived.state.role == NodeRole.FOLLOWER
    assert revived.state.leader_id == new_leader.node_id
    # 여전히 리더는 1명.
    assert len(cluster.leaders()) == 1


# --- 설정/입력 검증 ---

def test_empty_node_ids_raises() -> None:
    """빈 노드 목록은 ValueError."""
    with pytest.raises(ValueError):
        RaftCluster([])


def test_custom_config_propagates() -> None:
    """전달한 RaftConfig가 모든 노드에 적용된다."""
    cfg = RaftConfig(election_timeout_ms=(120, 200), heartbeat_interval_ms=30)
    cluster = RaftCluster(["a", "b", "c"], cfg=cfg, seed=0)
    for node in cluster.nodes.values():
        assert node.cfg.heartbeat_interval_ms == 30
