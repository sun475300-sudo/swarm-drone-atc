"""P741 RaftCluster — 결정론적 합의 루프(선거·복제·페일오버) 검증."""
from __future__ import annotations

from src.raft.airspace_controller_ha import NodeRole
from src.raft.raft_cluster import RaftCluster


def _three_node() -> RaftCluster:
    return RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"], seed=0)


def test_cluster_elects_single_leader() -> None:
    """tick 진행 시 정확히 1개의 리더가 선출된다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    assert leader is not None
    leaders = [n for n in cluster.nodes.values() if n.state.role == NodeRole.LEADER]
    assert len(leaders) == 1
    assert leader.state.role == NodeRole.LEADER


def test_followers_recognize_leader() -> None:
    """선출 후 팔로워는 리더 id 를 인지한다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    cluster.run_for(ms=200)
    for nid, node in cluster.nodes.items():
        if nid == leader.node_id:
            continue
        assert node.state.role == NodeRole.FOLLOWER
        assert node.state.leader_id == leader.node_id


def test_single_node_cluster_self_elects() -> None:
    """단일 노드 클러스터는 자기 자신을 리더로 선출 (quorum=1)."""
    cluster = RaftCluster(["solo"], seed=0)
    leader = cluster.run_until_leader()
    assert leader is not None
    assert leader.node_id == "solo"
    assert leader.quorum == 1


def test_submitted_command_replicates_to_quorum() -> None:
    """리더에 제출한 명령이 과반 노드에 복제된다."""
    cluster = _three_node()
    cluster.run_until_leader()
    idx = cluster.submit({"type": "advisory", "drone_id": "DR-001"})
    assert idx == 0
    cluster.run_for(ms=300)
    replicated = sum(
        1 for n in cluster.nodes.values()
        if n.state.log and n.state.log[0].command["drone_id"] == "DR-001"
    )
    assert replicated >= cluster.leader().quorum


def test_committed_after_quorum_replication() -> None:
    """과반 복제 후 commit_index 가 전진하고 명령이 커밋된다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    cluster.submit({"type": "rtl", "drone_id": "DR-009"})
    cluster.run_for(ms=300)
    assert leader.state.commit_index == 0
    committed = cluster.committed_commands(leader.node_id)
    assert committed[0]["drone_id"] == "DR-009"


def test_submit_returns_none_without_leader() -> None:
    """리더 선출 전에는 제출이 거부된다."""
    cluster = _three_node()
    assert cluster.submit({"type": "advisory"}) is None


def test_failover_elects_new_leader_after_crash() -> None:
    """리더 crash 후 잔여 노드가 새 리더를 선출한다 (페일오버)."""
    cluster = _three_node()
    old_leader = cluster.run_until_leader()
    cluster.run_for(ms=200)

    cluster.crash(old_leader.node_id)
    new_leader = cluster.run_until_leader()

    assert new_leader is not None
    assert new_leader.node_id != old_leader.node_id
    assert cluster.alive[new_leader.node_id]
    assert new_leader.state.current_term > old_leader.state.current_term


def test_no_leader_when_quorum_lost() -> None:
    """과반 노드 장애 시 새 리더를 선출하지 못한다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    # 3노드 중 2개 crash → quorum(2) 불가.
    others = [nid for nid in cluster.nodes if nid != leader.node_id]
    cluster.crash(leader.node_id)
    cluster.crash(others[0])
    new_leader = cluster.run_until_leader(max_ms=1000)
    assert new_leader is None


def test_recovered_node_rejoins_as_follower() -> None:
    """복구된 노드는 FOLLOWER 로 재합류하고 리더 로그를 따라잡는다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    follower_id = next(nid for nid in cluster.nodes if nid != leader.node_id)

    cluster.crash(follower_id)
    cluster.submit({"type": "advisory", "drone_id": "DR-100"})
    cluster.run_for(ms=300)

    cluster.recover(follower_id)
    cluster.run_for(ms=300)

    recovered = cluster.nodes[follower_id]
    assert recovered.state.role == NodeRole.FOLLOWER
    assert any(
        e.command.get("drone_id") == "DR-100" for e in recovered.state.log
    )


def test_election_is_reproducible_with_seed() -> None:
    """동일 seed → 동일 리더 (재현성)."""
    leader_a = RaftCluster(["a", "b", "c"], seed=42).run_until_leader()
    leader_b = RaftCluster(["a", "b", "c"], seed=42).run_until_leader()
    assert leader_a is not None and leader_b is not None
    assert leader_a.node_id == leader_b.node_id


def test_multiple_commands_replicate_in_order() -> None:
    """다중 명령이 순서대로 복제·커밋된다."""
    cluster = _three_node()
    leader = cluster.run_until_leader()
    for i in range(3):
        cluster.submit({"type": "advisory", "seq": i})
        cluster.run_for(ms=120)
    cluster.run_for(ms=200)
    assert leader.state.commit_index == 2
    committed = cluster.committed_commands(leader.node_id)
    assert [c["seq"] for c in committed] == [0, 1, 2]
