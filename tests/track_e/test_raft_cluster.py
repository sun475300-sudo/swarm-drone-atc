"""P741 RaftCluster — 실제 선거·quorum 복제·페일오버 결정론 검증."""
from __future__ import annotations

import pytest

from src.raft.airspace_controller_ha import NodeRole, RaftConfig
from src.raft.cluster import RaftCluster


def _three_node(seed: int = 42) -> RaftCluster:
    return RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"], seed=seed)


def test_majority_property() -> None:
    """과반 정족수는 전체 멤버십 기준."""
    assert RaftCluster(["a"]).majority == 1
    assert RaftCluster(["a", "b", "c"]).majority == 2
    assert RaftCluster(["a", "b", "c", "d", "e"]).majority == 3


def test_rejects_empty_and_duplicate_membership() -> None:
    """빈/중복 멤버십은 거부."""
    with pytest.raises(ValueError):
        RaftCluster([])
    with pytest.raises(ValueError):
        RaftCluster(["a", "a"])


def test_fresh_cluster_has_no_leader() -> None:
    """tick 이전에는 리더가 없다."""
    cluster = _three_node()
    assert cluster.leader() is None


def test_elects_exactly_one_leader() -> None:
    """선거 후 정확히 한 명의 리더가 선출된다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    assert leader.is_leader()
    assert leader.state.current_term >= 1
    leaders = [n for n in cluster.nodes.values() if n.is_leader()]
    assert len(leaders) == 1


def test_followers_recognize_leader() -> None:
    """선출 직후 follower는 리더 id와 term을 인지한다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    for nid, node in cluster.nodes.items():
        if nid == leader.node_id:
            continue
        assert node.state.role == NodeRole.FOLLOWER
        assert node.state.leader_id == leader.node_id
        assert node.state.current_term == leader.state.current_term


def test_single_node_self_elects() -> None:
    """단일 노드 클러스터는 스스로 리더가 된다 (majority=1)."""
    cluster = RaftCluster(["solo"], seed=1)
    leader = cluster.run_until_leader()
    assert leader.node_id == "solo"
    assert leader.is_leader()


def test_propose_fails_without_leader() -> None:
    """리더 부재 시 propose는 거부된다."""
    cluster = _three_node()
    assert cluster.propose({"type": "advisory"}) is False


def test_propose_commits_with_quorum() -> None:
    """리더 선출 후 propose는 과반 복제로 커밋된다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    assert cluster.propose({"type": "advisory", "drone_id": "DR-001"}) is True
    assert len(leader.state.log) == 1
    assert leader.state.commit_index == 0
    # follower 로그에도 복제됨
    for nid, node in cluster.nodes.items():
        if nid == leader.node_id:
            continue
        assert any(e.command.get("drone_id") == "DR-001" for e in node.state.log)


def test_failover_elects_new_leader() -> None:
    """리더 장애 시 새 리더가 더 높은 term으로 선출된다 (페일오버)."""
    cluster = _three_node()
    old = cluster.run_until_leader()
    old_term = old.state.current_term
    cluster.kill(old.node_id)
    new = cluster.run_until_leader()
    assert new.node_id != old.node_id
    assert new.state.current_term > old_term
    assert new.is_leader()


def test_no_leader_when_majority_dead() -> None:
    """과반이 죽으면 리더를 선출할 수 없다."""
    cluster = _three_node()
    cluster.run_until_leader()
    # 3노드 중 2노드 정지 → 1노드로는 majority(2) 미달
    alive = cluster.alive_node_ids()
    cluster.kill(alive[0])
    cluster.kill(alive[1])
    with pytest.raises(RuntimeError):
        cluster.run_until_leader(max_ticks=200)


def test_revive_rejoins_as_follower() -> None:
    """복귀한 노드는 follower로 합류하고 현 리더를 인지한다."""
    cluster = _three_node()
    old = cluster.run_until_leader()
    cluster.kill(old.node_id)
    new = cluster.run_until_leader()
    cluster.revive(old.node_id)
    revived = cluster.nodes[old.node_id]
    assert revived.state.role == NodeRole.FOLLOWER
    # 몇 번의 하트비트 후 새 리더를 인지
    for _ in range(20):
        cluster.tick()
    assert revived.state.leader_id == new.node_id
    assert cluster.leader().node_id == new.node_id


def test_deterministic_same_seed_same_leader() -> None:
    """동일 시드는 동일한 리더를 선출한다 (재현성)."""
    a = _three_node(seed=7).run_until_leader()
    b = _three_node(seed=7).run_until_leader()
    assert a.node_id == b.node_id


def test_leader_stays_stable_under_heartbeats() -> None:
    """하트비트가 유지되면 리더가 바뀌지 않는다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    for _ in range(50):
        cluster.tick()
    assert cluster.leader().node_id == leader.node_id


def test_custom_config_timing_respected() -> None:
    """사용자 RaftConfig 타이밍이 election timer에 반영된다."""
    cfg = RaftConfig(election_timeout_ms=(150, 300), heartbeat_interval_ms=50)
    cluster = RaftCluster(["a", "b", "c"], seed=3, cfg=cfg)
    leader = cluster.run_until_leader()
    assert leader.is_leader()


def test_revived_follower_catches_up_missed_entries() -> None:
    """죽은 동안 놓친 엔트리를 복귀 후 하트비트로 따라잡는다 (Raft §5.3 log matching)."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    # 팔로워 한 명을 정지시킨 뒤 두 엔트리를 커밋 → 그 팔로워는 둘 다 놓친다.
    follower_id = next(
        nid for nid in cluster.alive_node_ids() if nid != leader.node_id
    )
    cluster.kill(follower_id)
    assert cluster.propose({"type": "advisory", "drone_id": "DR-A"}) is True
    assert cluster.propose({"type": "advisory", "drone_id": "DR-B"}) is True
    # 복귀 후 하트비트(AppendEntries)로 누락 엔트리를 따라잡아야 한다.
    cluster.revive(follower_id)
    for _ in range(20):
        cluster.tick()
    revived = cluster.nodes[follower_id]
    cmds = [e.command.get("drone_id") for e in revived.state.log]
    assert "DR-A" in cmds
    assert "DR-B" in cmds
    assert len(revived.state.log) == len(leader.state.log)
