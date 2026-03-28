"""
암호화 통신 채널
===============
키 교환 시뮬레이션 + 메시지 무결성 + 재전송 방지.

사용법:
    sc = SecureChannel()
    sc.register_node("d1")
    sc.establish_session("d1", "d2")
    ok = sc.send_secure("d1", "d2", payload="hello")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import hashlib
import numpy as np


@dataclass
class Session:
    """암호화 세션"""
    node_a: str
    node_b: str
    session_key: str
    nonce_counter: int = 0
    messages_sent: int = 0
    established_at: float = 0.0
    valid: bool = True


@dataclass
class SecureMessage:
    """암호화 메시지"""
    sender: str
    receiver: str
    payload_hash: str
    nonce: int
    verified: bool = True


class SecureChannel:
    """암호화 통신 채널."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._nodes: set[str] = set()
        self._sessions: dict[tuple[str, str], Session] = {}
        self._messages: list[SecureMessage] = []
        self._replay_cache: set[str] = set()

    def register_node(self, node_id: str) -> None:
        self._nodes.add(node_id)

    def _session_key(self, a: str, b: str) -> tuple[str, str]:
        pair = tuple(sorted([a, b]))
        key_material = f"{pair[0]}:{pair[1]}:{self._rng.integers(0, 10**9)}"
        return pair, hashlib.sha256(key_material.encode()).hexdigest()[:16]

    def establish_session(self, node_a: str, node_b: str, t: float = 0.0) -> bool:
        if node_a not in self._nodes or node_b not in self._nodes:
            return False
        pair, key = self._session_key(node_a, node_b)
        self._sessions[pair] = Session(
            node_a=pair[0], node_b=pair[1],
            session_key=key, established_at=t,
        )
        return True

    def _get_session(self, a: str, b: str) -> Session | None:
        pair = tuple(sorted([a, b]))
        return self._sessions.get(pair)

    def send_secure(self, sender: str, receiver: str, payload: str = "") -> bool:
        session = self._get_session(sender, receiver)
        if not session or not session.valid:
            return False

        session.nonce_counter += 1
        nonce = session.nonce_counter

        # 메시지 해시
        msg_hash = hashlib.sha256(
            f"{payload}:{nonce}:{session.session_key}".encode()
        ).hexdigest()[:16]

        # 재전송 방지
        replay_key = f"{sender}:{receiver}:{nonce}"
        if replay_key in self._replay_cache:
            self._messages.append(SecureMessage(
                sender=sender, receiver=receiver,
                payload_hash=msg_hash, nonce=nonce, verified=False,
            ))
            return False

        self._replay_cache.add(replay_key)
        session.messages_sent += 1

        self._messages.append(SecureMessage(
            sender=sender, receiver=receiver,
            payload_hash=msg_hash, nonce=nonce, verified=True,
        ))
        return True

    def revoke_session(self, node_a: str, node_b: str) -> bool:
        session = self._get_session(node_a, node_b)
        if session:
            session.valid = False
            return True
        return False

    def active_sessions(self) -> int:
        return sum(1 for s in self._sessions.values() if s.valid)

    def replay_attempts(self) -> int:
        return sum(1 for m in self._messages if not m.verified)

    def summary(self) -> dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "active_sessions": self.active_sessions(),
            "total_messages": len(self._messages),
            "replay_attempts": self.replay_attempts(),
        }
