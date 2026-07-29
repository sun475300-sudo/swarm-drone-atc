# Phase 543: Distributed Consensus Clock — Vector Clock & Causal Order
"""
분산 합의 시계: 벡터 클록, Lamport 타임스탬프, 인과 순서 보장.
군집 드론 간 이벤트 순서 정합성 유지.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class VectorClock:
    """``VectorClock`` 관련 기능을 제공한다."""
    clocks: dict = field(default_factory=dict)

    def tick(self, node_id: str):
        """``tick`` 동작을 수행한다."""
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1

    def merge(self, other: 'VectorClock'):
        """``merge`` 동작을 수행한다."""
        for k, v in other.clocks.items():
            self.clocks[k] = max(self.clocks.get(k, 0), v)

    def happens_before(self, other: 'VectorClock') -> bool:
        """``happens_before`` 동작을 수행한다."""
        all_leq = all(self.clocks.get(k, 0) <= other.clocks.get(k, 0)
                       for k in set(self.clocks) | set(other.clocks))
        any_lt = any(self.clocks.get(k, 0) < other.clocks.get(k, 0)
                      for k in set(self.clocks) | set(other.clocks))
        return all_leq and any_lt

    def concurrent(self, other: 'VectorClock') -> bool:
        """``concurrent`` 동작을 수행한다."""
        return not self.happens_before(other) and not other.happens_before(self)

    def copy(self) -> 'VectorClock':
        """``copy`` 동작을 수행한다."""
        return VectorClock(dict(self.clocks))


@dataclass
class CausalEvent:
    """``CausalEvent`` 데이터를 표현한다."""
    event_id: str
    node_id: str
    timestamp: int  # Lamport
    vclock: VectorClock
    data: str


class LamportClock:
    """Lamport 논리 시계."""

    def __init__(self):
        """인스턴스를 초기화한다."""
        self.time = 0

    def tick(self) -> int:
        """``tick`` 동작을 수행한다."""
        self.time += 1
        return self.time

    def receive(self, sender_time: int) -> int:
        """``receive`` 동작을 수행한다."""
        self.time = max(self.time, sender_time) + 1
        return self.time


class ClockNode:
    """분산 노드: Lamport + Vector Clock 이중 시계."""

    def __init__(self, node_id: str):
        """인스턴스를 초기화한다."""
        self.node_id = node_id
        self.lamport = LamportClock()
        self.vclock = VectorClock()
        self.events: list[CausalEvent] = []

    def local_event(self, data: str) -> CausalEvent:
        """``local_event`` 동작을 수행한다."""
        ts = self.lamport.tick()
        self.vclock.tick(self.node_id)
        ev = CausalEvent(f"{self.node_id}_E{ts}", self.node_id, ts,
                         self.vclock.copy(), data)
        self.events.append(ev)
        return ev

    def send_event(self, data: str) -> CausalEvent:
        """``send_event`` 동작을 수행한다."""
        return self.local_event(f"SEND:{data}")

    def receive_event(self, sender_event: CausalEvent, data: str) -> CausalEvent:
        """``receive_event`` 동작을 수행한다."""
        self.lamport.receive(sender_event.timestamp)
        self.vclock.merge(sender_event.vclock)
        self.vclock.tick(self.node_id)
        ts = self.lamport.time
        ev = CausalEvent(f"{self.node_id}_E{ts}", self.node_id, ts,
                         self.vclock.copy(), f"RECV:{data}")
        self.events.append(ev)
        return ev


class DistributedConsensusClock:
    """분산 합의 시계 시뮬레이션."""

    def __init__(self, n_nodes=10, seed=42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.nodes = {f"node_{i}": ClockNode(f"node_{i}") for i in range(n_nodes)}
        self.all_events: list[CausalEvent] = []
        self.causal_violations = 0

    def simulate(self, n_rounds=20):
        """``simulate`` 동작을 수행한다."""
        node_ids = list(self.nodes.keys())
        for r in range(n_rounds):
            # 각 라운드: 랜덤 노드가 이벤트 생성 또는 메시지 전송
            actor = node_ids[int(self.rng.integers(0, len(node_ids)))]
            node = self.nodes[actor]

            if self.rng.random() < 0.4:
                # 로컬 이벤트
                ev = node.local_event(f"local_r{r}")
                self.all_events.append(ev)
            else:
                # 메시지 전송
                target = node_ids[int(self.rng.integers(0, len(node_ids)))]
                if target != actor:
                    send_ev = node.send_event(f"msg_r{r}")
                    self.all_events.append(send_ev)
                    recv_ev = self.nodes[target].receive_event(send_ev, f"msg_r{r}")
                    self.all_events.append(recv_ev)

    def verify_causal_order(self) -> dict:
        """인과 순서 정합성 검증."""
        violations = 0
        consistent = 0
        for i in range(len(self.all_events)):
            for j in range(i + 1, min(i + 20, len(self.all_events))):
                ei, ej = self.all_events[i], self.all_events[j]
                if ei.vclock.happens_before(ej.vclock):
                    if ei.timestamp > ej.timestamp:
                        violations += 1
                    else:
                        consistent += 1
        self.causal_violations = violations
        return {"consistent": consistent, "violations": violations}

    def summary(self):
        """현재 상태 요약을 반환한다."""
        cv = self.verify_causal_order()
        return {
            "nodes": len(self.nodes),
            "total_events": len(self.all_events),
            "causal_consistent": cv["consistent"],
            "causal_violations": cv["violations"],
        }


if __name__ == "__main__":
    dcc = DistributedConsensusClock(10, 42)
    dcc.simulate(30)
    for k, v in dcc.summary().items():
        print(f"  {k}: {v}")
