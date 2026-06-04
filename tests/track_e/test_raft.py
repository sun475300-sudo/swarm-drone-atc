"""P741 Raft HA AirspaceController 단위 검증."""
from __future__ import annotations

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    InMemoryTransport,
    LogEntry,
    NodeRole,
    RaftConfig,
    RaftState,
    health_check,
)


def _make_cluster(node_ids: list[str]) -> tuple[InMemoryTransport, dict[str, AirspaceControllerHA]]:
    """InMemoryTransport로 연결된 노드 클러스터 생성."""
    transport = InMemoryTransport()
    nodes: dict[str, AirspaceControllerHA] = {}
    for nid in node_ids:
        peers = [p for p in node_ids if p != nid]
        node = AirspaceControllerHA(nid, peers=peers, transport=transport)
        transport.register(node)
        nodes[nid] = node
    return transport, nodes


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


# --- 합의 로직: quorum 복제 / 로그 일관성 / 리더 선출 (InMemoryTransport) ---


def test_replicate_commits_on_majority_ack() -> None:
    """3-노드 클러스터에서 리더가 복제 → 과반 ack 받아 커밋."""
    _, nodes = _make_cluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = nodes["ctrl-1"]
    leader.state.role = NodeRole.LEADER
    leader.state.current_term = 1

    assert leader.replicate({"type": "advisory", "drone_id": "DR-001"}) is True
    assert leader.state.commit_index == 0
    # 팔로워에도 복제됨
    assert len(nodes["ctrl-2"].state.log) == 1
    assert len(nodes["ctrl-3"].state.log) == 1


def test_replicate_no_commit_without_quorum() -> None:
    """팔로워가 모두 stale term이면 ack 거부 → 커밋 안 됨(로그엔 남음)."""
    _, nodes = _make_cluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    leader = nodes["ctrl-1"]
    leader.state.role = NodeRole.LEADER
    leader.state.current_term = 1
    # 팔로워들을 더 높은 term으로 올려 AppendEntries 거부 유발
    nodes["ctrl-2"].state.current_term = 99
    nodes["ctrl-3"].state.current_term = 99

    assert leader.replicate({"type": "advisory"}) is False
    assert len(leader.state.log) == 1  # 로그엔 남음
    assert leader.state.commit_index == 0  # 커밋 안 됨 (초기값 유지)


def test_single_node_replicate_commits_immediately() -> None:
    """피어 없는 단일 노드는 즉시 커밋 (자신이 과반)."""
    node = AirspaceControllerHA("solo", peers=[])
    node.state.role = NodeRole.LEADER
    node.state.current_term = 2
    assert node.replicate({"type": "rtl"}) is True
    assert node.state.commit_index == 0


def test_trigger_election_wins_with_majority() -> None:
    """선거 트리거 → 과반 득표 시 리더 승격 + term 증가."""
    _, nodes = _make_cluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    candidate = nodes["ctrl-1"]
    assert candidate.trigger_election() is True
    assert candidate.is_leader()
    assert candidate.state.current_term == 1
    assert candidate.state.leader_id == "ctrl-1"


def test_trigger_election_loses_without_quorum() -> None:
    """피어들이 이미 더 높은 term이면 득표 실패 → FOLLOWER 복귀."""
    _, nodes = _make_cluster(["ctrl-1", "ctrl-2", "ctrl-3"])
    candidate = nodes["ctrl-1"]
    nodes["ctrl-2"].state.current_term = 50
    nodes["ctrl-3"].state.current_term = 50
    assert candidate.trigger_election() is False
    assert candidate.state.role == NodeRole.FOLLOWER


def test_append_entries_rejects_log_inconsistency() -> None:
    """prev_log_index가 로그 범위를 벗어나면 일관성 위반으로 거부."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    entries = [LogEntry(term=2, index=5, command={"type": "advisory"})]
    # 로그가 비어 있는데 prev_log_index=4 요구 → 거부
    ok = node.on_append_entries(
        "ctrl-2", term=2, entries=entries, commit_index=0,
        prev_log_index=4, prev_log_term=1,
    )
    assert ok is False
    assert len(node.state.log) == 0


def test_append_entries_truncates_conflicting_entries() -> None:
    """같은 인덱스에 다른 term 엔트리가 있으면 절단 후 새 엔트리로 교체."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    node.state.log = [
        LogEntry(term=1, index=0, command={"a": 1}),
        LogEntry(term=1, index=1, command={"b": 2}),  # 충돌 대상
    ]
    new_entries = [LogEntry(term=3, index=1, command={"c": 3})]
    ok = node.on_append_entries(
        "ctrl-2", term=3, entries=new_entries, commit_index=0,
        prev_log_index=0, prev_log_term=1,
    )
    assert ok is True
    assert len(node.state.log) == 2
    assert node.state.log[1].term == 3
    assert node.state.log[1].command == {"c": 3}


def test_append_entries_idempotent_on_matching_term() -> None:
    """동일 term 엔트리 재수신은 중복 추가하지 않음(idempotent)."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    e = LogEntry(term=1, index=0, command={"a": 1})
    node.on_append_entries("ctrl-2", term=1, entries=[e], commit_index=0)
    node.on_append_entries("ctrl-2", term=1, entries=[e], commit_index=0)
    assert len(node.state.log) == 1


def test_request_vote_resets_vote_on_higher_term() -> None:
    """상위 term RequestVote 수신 시 이전 vote 무효화 (Raft §5.1)."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    # term 1에서 ctrl-2에게 투표
    assert node.on_request_vote("ctrl-2", term=1, last_log_index=-1, last_log_term=0) is True
    # term 2에서 ctrl-3가 요청 → 새 term이므로 투표 가능해야 함
    assert node.on_request_vote("ctrl-3", term=2, last_log_index=-1, last_log_term=0) is True
    assert node.state.voted_for == "ctrl-3"
    assert node.state.current_term == 2


def test_append_entries_empty_log_heartbeat_no_negative_commit() -> None:
    """빈 로그에 commit_index>0 하트비트가 와도 commit_index가 음수로 퇴행하지 않음."""
    node = AirspaceControllerHA("ctrl-1", peers=[])
    ok = node.on_append_entries("ctrl-2", term=1, entries=[], commit_index=5)
    assert ok is True
    assert node.state.commit_index == 0  # 빈 로그 → 커밋 진전 없음, 음수 금지
