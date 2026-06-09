"""P741 Raft RPC 메시지 + 인메모리 전송 계층.

실제 배포에서는 gRPC/HTTP 전송으로 교체 가능하도록 `RaftTransport`
프로토콜로 추상화한다. 테스트·시뮬레이션은 `InMemoryTransport`로
네트워크 없이 결정론적 합의를 검증한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.raft.airspace_controller_ha import LogEntry


@dataclass(frozen=True)
class RequestVoteArgs:
    """RequestVote RPC 요청 (Raft §5.2)."""

    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass(frozen=True)
class RequestVoteReply:
    """RequestVote RPC 응답."""

    term: int
    granted: bool


@dataclass(frozen=True)
class AppendEntriesArgs:
    """AppendEntries RPC 요청 — 하트비트 + 로그 복제 (Raft §5.3)."""

    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: list[LogEntry] = field(default_factory=list)
    leader_commit: int = 0


@dataclass(frozen=True)
class AppendEntriesReply:
    """AppendEntries RPC 응답."""

    term: int
    success: bool
    match_index: int = -1


class RaftTransport(Protocol):
    """노드 간 RPC 전송 추상화."""

    def request_vote(self, target: str, args: RequestVoteArgs) -> RequestVoteReply:
        """``target`` 노드에 RequestVote RPC 전송."""
        ...

    def append_entries(self, target: str, args: AppendEntriesArgs) -> AppendEntriesReply:
        """``target`` 노드에 AppendEntries RPC 전송."""
        ...


class InMemoryTransport:
    """인메모리 동기 전송 — 테스트/시뮬레이션용.

    도달 불가(정지/파티션) 노드로의 RPC는 타임아웃으로 간주하여
    실패 응답을 반환한다.
    """

    def __init__(self, cluster) -> None:  # noqa: ANN001 (cluster: RaftCluster, 순환 import 회피)
        """``cluster`` 라우팅 테이블을 참조하는 전송 인스턴스 생성."""
        self._cluster = cluster

    def request_vote(self, target: str, args: RequestVoteArgs) -> RequestVoteReply:
        """도달 가능하면 대상 핸들러 호출, 아니면 거부 응답."""
        node = self._cluster.reachable(target)
        if node is None:
            return RequestVoteReply(term=args.term, granted=False)
        return node.handle_request_vote(args)

    def append_entries(self, target: str, args: AppendEntriesArgs) -> AppendEntriesReply:
        """도달 가능하면 대상 핸들러 호출, 아니면 실패 응답."""
        node = self._cluster.reachable(target)
        if node is None:
            return AppendEntriesReply(term=args.term, success=False)
        return node.handle_append_entries(args)
