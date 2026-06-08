"""P741 Raft 합의 루프 검증 — 선거·quorum 복제·페일오버.

in-process 클러스터(`connect`)로 RPC를 동기 메서드 호출로 만들어
타이밍 의존 없이 결정론적으로 검증한다.
"""
from __future__ import annotations

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    LogEntry,
    NodeRole,
    RaftConfig,
)


def _make_cluster(n: int) -> dict[str, AirspaceControllerHA]:
    """n개 노드를 서로 연결한 in-process 클러스터 생성."""
    ids = [f"ctrl-{i}" for i in range(n)]
    nodes = {
        nid: AirspaceControllerHA(nid, peers=[p for p in ids if p != nid])
        for nid in ids
    }
    for node in nodes.values():
        node.connect(nodes)
        node.start()
    return nodes


def test_majority_calculation() -> None:
    """과반 = size // 2 + 1 (3노드→2, 5노드→3)."""
    c3 = _make_cluster(3)["ctrl-0"]
    assert c3.cluster_size == 3
    assert c3._majority() == 2
    c5 = _make_cluster(5)["ctrl-0"]
    assert c5.cluster_size == 5
    assert c5._majority() == 3


def test_election_elects_single_leader() -> None:
    """후보가 선거를 시작하면 과반 득표로 리더가 된다."""
    nodes = _make_cluster(3)
    nodes["ctrl-0"].start_election()
    assert nodes["ctrl-0"].is_leader()
    # 나머지는 팔로워이고 같은 term
    leaders = [n for n in nodes.values() if n.is_leader()]
    assert len(leaders) == 1
    for n in nodes.values():
        assert n.state.current_term == 1


def test_followers_recognize_leader_after_election() -> None:
    """선거 후 팔로워가 leader_id를 인지한다 (초기 heartbeat)."""
    nodes = _make_cluster(3)
    nodes["ctrl-1"].start_election()
    assert nodes["ctrl-1"].is_leader()
    for nid in ("ctrl-0", "ctrl-2"):
        assert nodes[nid].state.role == NodeRole.FOLLOWER
        assert nodes[nid].state.leader_id == "ctrl-1"


def test_replicate_commits_with_quorum_and_propagates() -> None:
    """리더 복제 시 과반 ack로 commit + 팔로워 로그에 반영."""
    nodes = _make_cluster(3)
    leader = nodes["ctrl-0"]
    leader.start_election()
    assert leader.replicate({"type": "advisory", "drone_id": "DR-1"}) is True
    assert leader.state.commit_index == 0
    for nid in ("ctrl-1", "ctrl-2"):
        follower = nodes[nid]
        assert len(follower.state.log) == 1
        assert follower.state.log[0].command["drone_id"] == "DR-1"
        # commit_index도 전파됨
        assert follower.state.commit_index == 0


def test_replicate_fails_without_quorum() -> None:
    """과반에 도달 못하면 commit 실패 (로그는 append되나 commit 안됨)."""
    # peers 2개를 선언하지만 연결하지 않음 → ack는 self뿐 (1 < majority 2)
    node = AirspaceControllerHA("ctrl-0", peers=["ctrl-1", "ctrl-2"])
    node.start()
    node.state.role = NodeRole.LEADER
    node.state.current_term = 1
    assert node.replicate({"type": "rtl"}) is False
    assert len(node.state.log) == 1  # append는 됨
    assert node.state.commit_index == 0  # 미커밋 (초기값 유지)


def test_failover_follower_times_out_and_wins() -> None:
    """리더 정지 후 팔로워가 election timeout 만료 → 새 리더 선출."""
    nodes = _make_cluster(3)
    old_leader = nodes["ctrl-0"]
    old_leader.start_election()
    assert old_leader.is_leader()

    # 리더 장애 시뮬레이션
    old_leader.stop()

    follower = nodes["ctrl-1"]
    base = follower.state.last_heartbeat_ts
    # election timeout 한참 지난 시점에 tick → 선거 시작 → 리더 승격
    follower.tick(now=base + 10.0)
    assert follower.is_leader()
    assert follower.state.current_term == 2  # term 증가


def test_tick_noop_when_not_running() -> None:
    """stop된 노드는 tick에서 선거를 시작하지 않는다."""
    node = AirspaceControllerHA("ctrl-0", peers=["ctrl-1", "ctrl-2"])
    # start() 안 함 → _running False
    node.tick(now=10_000.0)
    assert node.state.role == NodeRole.FOLLOWER
    assert node.state.current_term == 0


def test_higher_term_request_vote_steps_down_leader() -> None:
    """리더가 더 높은 term의 RequestVote를 받으면 step-down."""
    nodes = _make_cluster(3)
    leader = nodes["ctrl-0"]
    leader.start_election()
    assert leader.is_leader()
    granted = leader.on_request_vote(
        candidate_id="ctrl-2", term=99, last_log_index=-1, last_log_term=0,
    )
    assert granted is True
    assert leader.state.role == NodeRole.FOLLOWER
    assert leader.state.current_term == 99


def test_append_entries_rejects_log_inconsistency() -> None:
    """prev_log 불일치 시 AppendEntries 거부 (Raft §5.3)."""
    node = AirspaceControllerHA("ctrl-1", peers=["ctrl-0"])
    node.start()
    # 빈 로그인데 prev_log_index=2를 요구 → 거부
    ok = node.on_append_entries(
        leader_id="ctrl-0",
        term=1,
        entries=[LogEntry(term=1, index=3, command={})],
        commit_index=0,
        prev_log_index=2,
        prev_log_term=1,
    )
    assert ok is False
    assert len(node.state.log) == 0


def test_append_entries_truncates_conflicting_tail() -> None:
    """prev_log 일치 시 충돌 tail을 절단하고 새 엔트리로 교체."""
    node = AirspaceControllerHA("ctrl-1", peers=["ctrl-0"])
    node.start()
    # 초기 로그: index0(term1), index1(term1, 충돌 예정)
    node.state.log = [
        LogEntry(term=1, index=0, command={"v": "a"}),
        LogEntry(term=1, index=1, command={"v": "stale"}),
    ]
    # prev_log_index=0(term1) 일치 → index1 이후 절단 후 새 엔트리 추가
    ok = node.on_append_entries(
        leader_id="ctrl-0",
        term=2,
        entries=[LogEntry(term=2, index=1, command={"v": "fresh"})],
        commit_index=1,
        prev_log_index=0,
        prev_log_term=1,
    )
    assert ok is True
    assert len(node.state.log) == 2
    assert node.state.log[1].command["v"] == "fresh"
    assert node.state.log[1].term == 2


def test_custom_config_distinct_timeouts() -> None:
    """노드마다 election timeout이 결정론적으로 서로 다르다 (split-vote 완화)."""
    cfg = RaftConfig(election_timeout_ms=(150, 300))
    a = AirspaceControllerHA("ctrl-alpha", peers=[], cfg=cfg)
    b = AirspaceControllerHA("ctrl-beta", peers=[], cfg=cfg)
    assert 150 <= a._election_timeout_ms < 300
    assert 150 <= b._election_timeout_ms < 300
    assert a._election_timeout_ms != b._election_timeout_ms
