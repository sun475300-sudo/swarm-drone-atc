"""ODYSSEY Phase 432 (Federation): 메시 연합 토폴로지 + 멀티홉 전파.

Phase 425(연합 NOTAM 전파)는 동적 NFZ를 *직접 겹치는* 인접 인스턴스에만 1홉으로
전파한다. 그러나 3+ 인스턴스가 타일처럼 늘어선 메시 연합에서는, 어떤 인스턴스에
관련된 사건(NFZ·운영 의도)이 중간 인스턴스를 *경유*해야만 먼 인스턴스에 닿는다.

본 모듈은 Phase 421 디스커버리에 등록된 인스턴스들의 **공역 경계 인접 그래프**를
구성하고, 그 위에서 결정적 멀티홉 전파(BFS 홉 계층·TTL 한정)와 중계 포워딩
테이블을 계산한다. 외부 네트워크·랜덤 없이 동작하며 모든 출력은 정렬된다(재현성).

인접 정의 (타일형 비중첩 공역도 이웃으로 인식):
  두 볼륨이 *수평(x·y)* 으로 ``border_tolerance_m`` 이내로 접하거나 겹치고,
  *수직(z)* 과 *시간(t)* 으로 (엄격) 교차하면 이웃이다. 수평 경계만 허용오차를
  두므로, 정확히 맞닿은 타일([0,1000)·[1000,2000))은 이웃이지만 멀리 떨어진
  타일([0,1000)·[2000,3000))은 이웃이 아니다. Phase 421 `overlaps`(엄격 4D 교차)는
  맞닿은 타일을 비이웃으로 보므로, 메시 토폴로지에는 이 경계 인접을 별도 정의한다.

스냅샷 모델: 생성 시점의 디스커버리 등록 상태로 그래프를 1회 구성한다. 이후
서비스가 바뀌면 새 ``FederationMesh`` 를 만들거나 ``rebuild()`` 를 호출한다.
"""

from __future__ import annotations

from collections import deque

from simulation.federation_discovery import FederationDiscoveryService, Volume4D

# 수평 경계 허용오차 기본값 (m). 정확히 맞닿은 타일을 이웃으로 인식하는 최소 여유.
DEFAULT_BORDER_TOLERANCE_M = 1.0


def _horizontally_near(a: Volume4D, b: Volume4D, tol: float) -> bool:
    """두 볼륨의 x·y 투영 간 *각 축 간격이 ``tol`` 미만*이면 True (경계 접촉 포함).

    x·y 축을 독립적으로 판정하므로, 모서리(대각)만 맞닿은 타일도 이웃으로 본다
    (king-move 인접). 면(face)만 인접으로 제한하려면 호출부에서 별도 필터가 필요하다.
    """
    return (
        a.x_min - tol < b.x_max
        and b.x_min - tol < a.x_max
        and a.y_min - tol < b.y_max
        and b.y_min - tol < a.y_max
    )


def _adjacent(a: Volume4D, b: Volume4D, tol: float) -> bool:
    """경계 인접 판정 — 수평은 허용오차, 수직·시간은 엄격 교차."""
    return (
        _horizontally_near(a, b, tol)
        and a.z_min < b.z_max
        and b.z_min < a.z_max
        and a.t_start < b.t_end
        and b.t_start < a.t_end
    )


class FederationMesh:
    """디스커버리 등록 상태로부터 구성한 결정적 인스턴스 인접 그래프."""

    def __init__(
        self,
        service: FederationDiscoveryService,
        border_tolerance_m: float = DEFAULT_BORDER_TOLERANCE_M,
    ) -> None:
        if border_tolerance_m < 0:
            raise ValueError("border_tolerance_m은 음수일 수 없음")
        self._service = service
        self._tolerance = float(border_tolerance_m)
        self._adj: dict[str, tuple[str, ...]] = {}
        self.rebuild()

    def rebuild(self) -> None:
        """현재 디스커버리 등록 상태로 인접 그래프를 재구성한다(스냅샷 갱신)."""
        ids = self._service.instances()
        volumes = {iid: self._service.volume_of(iid) for iid in ids}
        edges: dict[str, set[str]] = {iid: set() for iid in ids}
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if _adjacent(volumes[a], volumes[b], self._tolerance):
                    edges[a].add(b)
                    edges[b].add(a)
        self._adj = {iid: tuple(sorted(edges[iid])) for iid in ids}

    def instances(self) -> tuple[str, ...]:
        """그래프에 포함된 모든 인스턴스 id를 정렬해 반환한다."""
        return tuple(sorted(self._adj))

    def neighbors(self, instance_id: str) -> tuple[str, ...]:
        """경계 인접 이웃 id를 정렬해 반환한다. 미등록이면 ``KeyError``."""
        return self._adj[instance_id]

    def adjacency(self) -> dict[str, tuple[str, ...]]:
        """전체 인접 맵의 결정적 복사본 {id: 정렬된 이웃 튜플}."""
        return dict(self._adj)

    def components(self) -> tuple[tuple[str, ...], ...]:
        """연결 요소들을 정렬해 반환한다 (각 요소는 정렬된 id 튜플, 첫 id 기준 정렬)."""
        seen: set[str] = set()
        result: list[tuple[str, ...]] = []
        for start in self.instances():  # 정렬 순회로 결정성 확보
            if start in seen:
                continue
            comp: list[str] = []
            queue = deque([start])
            seen.add(start)
            while queue:
                node = queue.popleft()
                comp.append(node)
                for nb in self._adj[node]:
                    if nb not in seen:
                        seen.add(nb)
                        queue.append(nb)
            result.append(tuple(sorted(comp)))
        return tuple(sorted(result))

    def is_connected(self) -> bool:
        """전 인스턴스가 단일 연결 요소면 True (0·1개 인스턴스는 자명하게 True)."""
        return len(self._adj) <= 1 or len(self.components()) == 1

    def shortest_path(self, src: str, dst: str) -> tuple[str, ...]:
        """src→dst 최단 경로(홉 수 최소)를 반환한다. 동률은 정렬된 이웃 우선.

        도달 불가면 빈 튜플. ``src == dst`` 면 ``(src,)``. 미등록 노드는 ``KeyError``.
        """
        if src not in self._adj:
            raise KeyError(src)
        if dst not in self._adj:
            raise KeyError(dst)
        if src == dst:
            return (src,)
        prev: dict[str, str] = {src: src}
        queue = deque([src])
        while queue:
            node = queue.popleft()
            for nb in self._adj[node]:  # 이미 정렬됨 → 동률 시 사전식 우선
                if nb not in prev:
                    prev[nb] = node
                    if nb == dst:
                        return self._reconstruct(prev, dst)
                    queue.append(nb)
        return ()

    @staticmethod
    def _reconstruct(prev: dict[str, str], dst: str) -> tuple[str, ...]:
        path = [dst]
        while prev[path[-1]] != path[-1]:
            path.append(prev[path[-1]])
        path.reverse()
        return tuple(path)

    def propagate(self, origin: str, ttl: int | None = None) -> dict[str, int]:
        """origin에서 멀티홉 전파 시 도달하는 인스턴스 → 최소 홉 수 (origin=0).

        Phase 425의 1홉 직접 전파를 메시 전역 중계로 일반화한다. ``ttl`` 이 주어지면
        홉 수가 ttl 이하인 인스턴스만 포함한다(TTL 한정 플러딩). 미등록이면 ``KeyError``.
        """
        if origin not in self._adj:
            raise KeyError(origin)
        if ttl is not None and ttl < 0:
            raise ValueError("ttl은 음수일 수 없음")
        reach: dict[str, int] = {origin: 0}
        queue: deque[str] = deque([origin])
        while queue:
            node = queue.popleft()
            hop = reach[node]
            if ttl is not None and hop >= ttl:
                continue
            for nb in self._adj[node]:
                if nb not in reach:
                    reach[nb] = hop + 1
                    queue.append(nb)
        return reach

    def relay_table(self, origin: str, ttl: int | None = None) -> dict[str, str]:
        """origin의 결정적 중계 포워딩 테이블 {목적지: 다음 홉 이웃}.

        도달 가능한 각 목적지(origin 제외)에 대해, origin이 최단 경로를 따라
        패킷을 넘길 *첫 이웃*을 매핑한다. 동률 경로는 정렬된 이웃을 우선해 분리한다.
        ``ttl`` 한정 시 홉 수가 ttl 이하인 목적지만 포함한다. 미등록이면 ``KeyError``.
        """
        if origin not in self._adj:
            raise KeyError(origin)
        if ttl is not None and ttl < 0:
            raise ValueError("ttl은 음수일 수 없음")
        # BFS 트리에서 각 노드가 origin의 어느 이웃 가지에 속하는지(첫 홉) 기록.
        first_hop: dict[str, str] = {}
        hop_of: dict[str, int] = {origin: 0}
        queue: deque[str] = deque([origin])
        while queue:
            node = queue.popleft()
            hop = hop_of[node]
            if ttl is not None and hop >= ttl:
                continue
            for nb in self._adj[node]:
                if nb in hop_of:
                    continue
                hop_of[nb] = hop + 1
                first_hop[nb] = nb if node == origin else first_hop[node]
                queue.append(nb)
        return first_hop

    def summary(self) -> dict[str, int]:
        """결정적 상태 요약 — 인스턴스 수·간선 수·연결 요소 수."""
        edge_count = sum(len(v) for v in self._adj.values()) // 2
        return {
            "instances": len(self._adj),
            "edges": edge_count,
            "components": len(self.components()),
        }
