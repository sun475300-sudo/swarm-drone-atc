"""P741 Raft 합의 루프 검증 — 선거·페일오버·quorum 복제.

결정론적 in-process 클러스터(`RaftCluster`)로 네트워크 없이 검증.
시간은 `tick(now_ms)`로 명시적으로 주입하여 재현 가능.
"""
from __future__ import annotations

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    NodeRole,
    RaftCluster,
)


def _run_until_leader(cluster: RaftCluster, max_ms: int = 5000) -> AirspaceControllerHA | None:
    """리더가 나올 때까지 tick 진행. 리더 노드 반환(없으면 None)."""
    for now in range(0, max_ms, 10):
        cluster.tick(now)
        leader = cluster.leader()
        if leader is not None:
            return leader
    return None


def test_single_node_elects_itself() -> None:
    """단일 노드 클러스터는 majority=1 이므로 즉시 자기 자신을 리더로 선출."""
    cluster = RaftCluster(["ctrl-1"], seed=1)
    leader = _run_until_leader(cluster)
    assert leader is not None
    assert leader.node_id == "ctrl-1"
    assert leader.is_leader()


def test_three_node_elects_single_leader() -> None:
    """3노드 클러스터는 정확히 하나의 리더를 선출."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"], seed=7)
    leader = _run_until_leader(cluster)
    assert leader is not None
    leaders = [n for n in cluster.nodes if n.is_leader()]
    assert len(leaders) == 1
    # 나머지는 follower
    followers = [n for n in cluster.nodes if n.state.role == NodeRole.FOLLOWER]
    assert len(followers) == 2


def test_all_nodes_agree_on_term_and_leader() -> None:
    """선출 후 모든 노드가 동일 리더·동일 term 에 수렴."""
    cluster = RaftCluster(["a", "b", "c"], seed=3)
    leader = _run_until_leader(cluster)
    assert leader is not None
    # heartbeat 가 전파되도록 추가 tick
    for now in range(5000, 5500, 10):
        cluster.tick(now)
    terms = {n.state.current_term for n in cluster.nodes}
    assert len(terms) == 1
    for n in cluster.nodes:
        assert n.state.leader_id == leader.node_id


def test_leader_failure_triggers_reelection() -> None:
    """리더 정지 시 나머지 노드가 새 리더를 선출(페일오버)."""
    cluster = RaftCluster(["a", "b", "c"], seed=11)
    leader = _run_until_leader(cluster)
    assert leader is not None
    old_leader_id = leader.node_id

    cluster.fail(old_leader_id)
    new_leader = None
    for now in range(6000, 12000, 10):
        cluster.tick(now)
        new_leader = cluster.leader()
        if new_leader is not None and new_leader.node_id != old_leader_id:
            break
    assert new_leader is not None
    assert new_leader.node_id != old_leader_id
    assert new_leader.state.current_term > leader.state.current_term


def test_replicate_commits_with_quorum() -> None:
    """리더가 명령을 복제하면 quorum 합의로 commit 되고 follower 로 전파."""
    cluster = RaftCluster(["a", "b", "c"], seed=5)
    leader = _run_until_leader(cluster)
    assert leader is not None

    assert leader.replicate({"type": "advisory", "drone_id": "DR-9"}) is True
    assert leader.state.commit_index >= 0
    # follower 로그에도 반영(heartbeat 전파)
    for now in range(5000, 5300, 10):
        cluster.tick(now)
    for n in cluster.nodes:
        assert any(e.command.get("drone_id") == "DR-9" for e in n.state.log)


def test_replicate_rejected_on_follower() -> None:
    """follower 는 replicate 거부."""
    cluster = RaftCluster(["a", "b", "c"], seed=5)
    leader = _run_until_leader(cluster)
    assert leader is not None
    follower = next(n for n in cluster.nodes if not n.is_leader())
    assert follower.replicate({"type": "advisory"}) is False


def test_higher_term_request_vote_steps_down_leader() -> None:
    """더 높은 term 의 RequestVote 수신 시 리더는 follower 로 강등."""
    cluster = RaftCluster(["a", "b", "c"], seed=5)
    leader = _run_until_leader(cluster)
    assert leader is not None
    higher = leader.state.current_term + 5
    granted = leader.on_request_vote(
        candidate_id="z", term=higher, last_log_index=99, last_log_term=higher,
    )
    assert granted is True
    assert leader.state.role == NodeRole.FOLLOWER
    assert leader.state.current_term == higher
