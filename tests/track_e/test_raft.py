"""P741 Raft HA AirspaceController 단위 검증."""
from __future__ import annotations

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    LogEntry,
    NodeRole,
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
    # 단일 노드(peers 없음): 리더 자신이 과반 → 즉시 커밋.
    assert node.state.commit_index == 0


def test_replicate_defers_commit_when_peers_present() -> None:
    """피어가 있으면 replicate 는 로그만 추가하고 커밋은 클러스터에 위임."""
    node = AirspaceControllerHA("ctrl-1", peers=["ctrl-2:8001", "ctrl-3:8002"])
    node.state.role = NodeRole.LEADER
    node.state.current_term = 5
    assert node.replicate({"type": "advisory", "drone_id": "DR-002"}) is True
    assert node.replicate({"type": "advisory", "drone_id": "DR-003"}) is True
    assert len(node.state.log) == 2
    # quorum 복제 전이므로 commit_index 가 새 엔트리(index 1)로 진행되지 않는다.
    assert node.state.commit_index < 1


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


def test_on_append_entries_rejects_on_log_gap() -> None:
    """prev_log_index가 팔로워 로그 범위를 벗어나면 거부 (§5.3 일관성 검사)."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    ok = node.on_append_entries(
        "ctrl-2",
        term=1,
        entries=[LogEntry(term=1, index=3, command={})],
        commit_index=0,
        prev_log_index=2,
        prev_log_term=1,
    )
    assert ok is False
    assert node.state.log == []
    # 일관성 검사에 실패해도 리더/term 은 인지한다.
    assert node.state.current_term == 1
    assert node.state.leader_id == "ctrl-2"


def test_on_append_entries_truncates_conflicting_suffix() -> None:
    """동일 index·상이 term 엔트리는 잘라내고 리더 로그로 정렬한다 (§5.3)."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.state.log = [
        LogEntry(term=1, index=0, command={"type": "old"}),
        LogEntry(term=1, index=1, command={"type": "stale"}),
    ]
    ok = node.on_append_entries(
        "ctrl-2",
        term=2,
        entries=[LogEntry(term=2, index=1, command={"type": "fresh"})],
        commit_index=1,
        prev_log_index=0,
        prev_log_term=1,
    )
    assert ok is True
    assert len(node.state.log) == 2
    assert node.state.log[1].term == 2
    assert node.state.log[1].command["type"] == "fresh"


def test_on_append_entries_is_idempotent() -> None:
    """동일 엔트리 재전송(하트비트 재방송)은 로그를 중복 추가하지 않는다."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    entries = [LogEntry(term=1, index=0, command={"type": "advisory"})]
    assert node.on_append_entries("ctrl-2", term=1, entries=entries, commit_index=0)
    assert node.on_append_entries("ctrl-2", term=1, entries=entries, commit_index=0)
    assert len(node.state.log) == 1


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
