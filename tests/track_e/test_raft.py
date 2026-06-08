"""P741 Raft HA AirspaceController 단위 검증."""
from __future__ import annotations

import pytest

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    LogEntry,
    NodeRole,
    RaftCluster,
    RaftConfig,
    RaftState,
    health_check,
)


def test_initial_state_is_follower() -> None:
    """노드 초기 상태는 FOLLOWER."""
    node = AirspaceControllerHA("ctrl-1", peers=["ctrl-2", "ctrl-3"])
    assert node.state.role == NodeRole.FOLLOWER
    assert node.state.current_term == 0
    assert not node.is_leader()


def test_replicate_returns_false_when_not_leader() -> None:
    """리더가 아니면 replicate 거부."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    assert node.replicate({"type": "advisory"}) is False


def test_replicate_appends_to_log_when_leader() -> None:
    """리더 상태에서 replicate → 로그에 추가."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.state.role = NodeRole.LEADER
    node.state.current_term = 5
    assert node.replicate({"type": "advisory", "drone_id": "DR-001"}) is True
    assert len(node.state.log) == 1
    assert node.state.log[0].command["drone_id"] == "DR-001"
    assert node.state.log[0].term == 5


def test_on_request_vote_grants_when_eligible() -> None:
    """투표 자격 충족 시 vote granted."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    granted = node.on_request_vote(
        candidate_id="ctrl-2", term=1, last_log_index=0, last_log_term=0,
    )
    assert granted is True
    assert node.state.voted_for == "ctrl-2"
    assert node.state.current_term == 1


def test_on_request_vote_rejects_lower_term() -> None:
    """더 낮은 term은 vote 거부."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.state.current_term = 5
    granted = node.on_request_vote(
        candidate_id="ctrl-2", term=3, last_log_index=0, last_log_term=0,
    )
    assert granted is False


def test_on_request_vote_rejects_when_already_voted() -> None:
    """같은 term에서 이미 투표했으면 다른 후보 거부."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.on_request_vote("ctrl-2", term=1, last_log_index=0, last_log_term=0)
    granted = node.on_request_vote("ctrl-3", term=1, last_log_index=0, last_log_term=0)
    assert granted is False


def test_on_append_entries_updates_term_and_role() -> None:
    """AppendEntries 수신 → term 갱신 + FOLLOWER."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.state.role = NodeRole.CANDIDATE
    node.on_append_entries(leader_id="ctrl-2", term=3, entries=[], commit_index=0)
    assert node.state.role == NodeRole.FOLLOWER
    assert node.state.current_term == 3
    assert node.state.leader_id == "ctrl-2"


def test_on_append_entries_appends_log() -> None:
    """엔트리 포함 AppendEntries → 로그 누적."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    entries = [
        LogEntry(term=1, index=0, command={"type": "advisory"}),
        LogEntry(term=1, index=1, command={"type": "rtl"}),
    ]
    node.on_append_entries("ctrl-2", term=1, entries=entries, commit_index=1)
    assert len(node.state.log) == 2
    assert node.state.commit_index == 1


def test_health_check_returns_expected_fields() -> None:
    """헬스체크 dict 구조."""
    node = AirspaceControllerHA("ctrl-1", peers=["ctrl-2"])
    h = health_check(node)
    assert h["node_id"] == "ctrl-1"
    assert h["role"] == "follower"
    assert h["is_leader"] is False
    assert "term" in h
    assert "log_size" in h


def test_config_defaults_reasonable() -> None:
    """RaftConfig 기본값이 Raft 논문 권고치 범위."""
    cfg = RaftConfig()
    assert 100 <= cfg.election_timeout_ms[0] <= 200
    assert 200 <= cfg.election_timeout_ms[1] <= 400
    assert 20 <= cfg.heartbeat_interval_ms <= 100


def test_raft_state_dataclass_defaults() -> None:
    """RaftState 기본 dataclass field."""
    s = RaftState(node_id="x")
    assert s.role == NodeRole.FOLLOWER
    assert s.current_term == 0
    assert s.log == []
    assert s.voted_for is None


def test_on_request_vote_steps_down_on_higher_term() -> None:
    """더 높은 term 관측 시 투표 초기화 후 grant (Raft §5.1)."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.on_request_vote("ctrl-2", term=1, last_log_index=0, last_log_term=0)
    # 더 높은 term의 다른 후보 → 강등 후 grant
    granted = node.on_request_vote("ctrl-3", term=2, last_log_index=0, last_log_term=0)
    assert granted is True
    assert node.state.current_term == 2
    assert node.state.voted_for == "ctrl-3"


# --- RaftCluster: 실제 선거·복제·페일오버 ---


def test_cluster_elects_single_leader() -> None:
    """3노드 클러스터에서 선거 → 정확히 1명의 리더."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    assert leader is not None
    assert leader.is_leader()
    leaders = [n for n in cluster.nodes.values() if n.is_leader()]
    assert len(leaders) == 1


def test_cluster_replicate_commits_with_quorum() -> None:
    """리더의 replicate가 과반 ack로 commit."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    assert leader.replicate({"type": "advisory", "drone_id": "DR-1"}) is True
    assert leader.state.commit_index == leader.state.log[-1].index


def test_cluster_failover_reelects_new_leader() -> None:
    """마스터 장애 후 재선거로 새 리더 선출."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    first = cluster.elect_leader()
    cluster.fail(first.node_id)
    new_leader = cluster.elect_leader()
    assert new_leader is not None
    assert new_leader.node_id != first.node_id
    assert new_leader.state.current_term > first.state.current_term


def test_cluster_no_quorum_when_majority_down() -> None:
    """과반 노드 장애 시 리더 선출 실패 (split-brain 방지)."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    cluster.fail("ctrl-2")
    cluster.fail("ctrl-3")
    leader = cluster.elect_leader(preferred="ctrl-1")
    assert leader is None
    assert not cluster.nodes["ctrl-1"].is_leader()


def test_cluster_replicate_fails_without_quorum() -> None:
    """리더 단독 생존(과반 미달) 시 replicate commit 실패."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    others = [nid for nid in cluster.nodes if nid != leader.node_id]
    for nid in others:
        cluster.fail(nid)
    assert leader.replicate({"type": "advisory"}) is False


def test_cluster_recover_rejoins_node() -> None:
    """down 노드 복구 후 다시 투표 가능."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    cluster.fail("ctrl-3")
    cluster.recover("ctrl-3")
    assert "ctrl-3" not in cluster._down
    assert cluster.nodes["ctrl-3"]._running


def test_cluster_rejects_duplicate_node_ids() -> None:
    """중복 node_id는 ValueError."""
    with pytest.raises(ValueError, match="중복"):
        RaftCluster(["ctrl-1", "ctrl-1"])


def test_on_append_entries_empty_log_keeps_commit_nonneg() -> None:
    """빈 로그 + commit_index=0 하트비트가 commit_index를 음수로 만들지 않음."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.on_append_entries("ctrl-2", term=1, entries=[], commit_index=0)
    assert node.state.commit_index == 0


def test_cluster_followers_catch_up_commit_index() -> None:
    """post-commit 하트비트로 follower commit_index가 리더를 따라잡음."""
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = cluster.elect_leader()
    leader.replicate({"type": "advisory", "n": 1})
    leader.replicate({"type": "advisory", "n": 2})
    for nid, node in cluster.nodes.items():
        if nid != leader.node_id:
            assert node.state.commit_index == leader.state.commit_index
