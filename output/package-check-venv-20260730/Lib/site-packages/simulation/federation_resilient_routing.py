"""ODYSSEY Phase 435 (Federation): 메시 복원력 라우팅 — 절단점·브리지 + 백업 경로.

Phase 432(`FederationMesh`)는 인스턴스 경계 인접 그래프와 *단일* 최단 경로
(`shortest_path`)·멀티홉 전파를 제공한다. 그러나 3+ 인스턴스 메시 연합이 실제로
한 인스턴스(USS) 장애를 견디려면, **어떤 중계 인스턴스의 장애가 연합을 분단시키는지**
(단일 장애점)와 **주 경로가 끊겼을 때 우회할 백업 경로가 있는지**를 알아야 한다.

본 모듈은 Phase 432 메시 스냅샷 위에서 다음을 결정적으로 계산한다.

* **절단점(articulation point)** — 제거 시 연결 요소 수가 늘어나는 인스턴스. 즉 그
  인스턴스가 죽으면 한쪽 무리가 다른 쪽과 단절되는 단일 장애점. Hopcroft-Tarjan
  DFS(`disc`/`low`) 1회 순회로 식별한다.
* **브리지(bridge)** — 제거 시 연결이 끊기는 단일 링크 인접. 동일 DFS에서 산출.
* **백업 경로** — 주 최단 경로와 *내부 노드·간선을 공유하지 않는* 대체 경로. 주
  경로의 어떤 중계가 죽어도 살아남는 이중화 경로 존재 여부를 답한다.
* **생존 도달성** — 임의의 장애 인스턴스 집합을 제거했을 때 origin에서 여전히
  닿는 인스턴스와 홉 수.

Phase 430(분할 뇌 안전 강하)이 *분단이 이미 일어난 뒤* 안전 정책을 다룬다면, 본
모듈은 *분단을 일으킬 수 있는 구조적 취약점을 사전에* 드러낸다. 외부 네트워크·랜덤
없이 동작하며 모든 출력은 정렬된다(재현성).
"""

from __future__ import annotations

from collections import deque

from simulation.federation_mesh import FederationMesh


class FederationResilientRouting:
    """Phase 432 메시 스냅샷의 구조적 복원력 분석기 (결정적·읽기 전용)."""

    def __init__(self, mesh: FederationMesh) -> None:
        # 메시의 인접 스냅샷을 복사해 보관(이후 메시 변경과 독립). 모든 분석은
        # 이 스냅샷에서만 수행하므로 메시가 나중에 rebuild돼도 결과가 흔들리지 않는다.
        self._adj: dict[str, tuple[str, ...]] = mesh.adjacency()
        self._tarjan_cache: tuple[set[str], list[tuple[str, str]]] | None = None

    def instances(self) -> tuple[str, ...]:
        """분석 대상 인스턴스 id를 정렬해 반환한다."""
        return tuple(sorted(self._adj))

    # --- 절단점 / 브리지 (Hopcroft-Tarjan) ---------------------------------

    def _tarjan(self) -> tuple[set[str], list[tuple[str, str]]]:
        """절단점 집합과 브리지 목록을 단일 DFS로 산출한다.

        재귀 대신 명시적 스택을 써서 큰 메시에서도 재귀 한계에 걸리지 않게 한다.
        정렬된 이웃을 순회하므로 동일 입력은 동일 결과(브리지 목록 순서 포함).
        그래프는 생성 후 불변이므로 첫 호출 결과를 캐시해 재계산을 피한다.
        """
        if self._tarjan_cache is not None:
            return self._tarjan_cache
        disc: dict[str, int] = {}
        low: dict[str, int] = {}
        articulation: set[str] = set()
        bridges: list[tuple[str, str]] = []
        timer = 0

        for root in self.instances():  # 정렬 순회 → 결정성
            if root in disc:
                continue
            root_children = 0
            # 스택 항목: (노드, 부모, 이웃 인덱스)
            stack: list[list] = [[root, None, 0]]
            disc[root] = low[root] = timer
            timer += 1
            while stack:
                node, parent, idx = stack[-1]
                nbrs = self._adj[node]
                if idx < len(nbrs):
                    stack[-1][2] += 1  # 다음 이웃으로 진행
                    nb = nbrs[idx]
                    if nb == parent:
                        continue
                    if nb in disc:
                        # 역방향 간선 → low 갱신
                        low[node] = min(low[node], disc[nb])
                    else:
                        if parent is None:
                            root_children += 1
                        disc[nb] = low[nb] = timer
                        timer += 1
                        stack.append([nb, node, 0])
                else:
                    # node의 모든 이웃 처리 완료 → 부모 low 갱신·판정
                    stack.pop()
                    if parent is not None:
                        low[parent] = min(low[parent], low[node])
                        # 비루트 절단점: 자식 low가 부모 disc 이상이면 단절 발생
                        if parent != root and low[node] >= disc[parent]:
                            articulation.add(parent)
                        # 브리지: 자식 서브트리가 부모 위로 못 올라가면 단일 링크
                        if low[node] > disc[parent]:
                            bridges.append(tuple(sorted((parent, node))))
            if root_children >= 2:
                articulation.add(root)
        self._tarjan_cache = (articulation, bridges)
        return self._tarjan_cache

    def articulation_points(self) -> tuple[str, ...]:
        """제거 시 연결 요소가 늘어나는 단일 장애점 인스턴스를 정렬해 반환한다."""
        articulation, _ = self._tarjan()
        return tuple(sorted(articulation))

    def bridges(self) -> tuple[tuple[str, str], ...]:
        """제거 시 연결이 끊기는 단일 링크 인접을 정렬해 반환한다.

        각 브리지는 정렬된 ``(a, b)`` 쌍이고, 전체 목록도 사전식 정렬된다.
        """
        _, bridges = self._tarjan()
        return tuple(sorted(bridges))

    def is_single_point_of_failure(self, instance_id: str) -> bool:
        """해당 인스턴스가 절단점(단일 장애점)이면 True. 미등록이면 ``KeyError``."""
        if instance_id not in self._adj:
            raise KeyError(instance_id)
        return instance_id in self.articulation_points()

    # --- 백업 경로 (내부 노드·간선 분리) -----------------------------------

    @staticmethod
    def _bfs(adj: dict[str, set[str]] | dict[str, tuple[str, ...]], src: str, dst: str) -> tuple[str, ...]:
        """정렬 이웃 우선 BFS 최단 경로. 도달 불가면 빈 튜플."""
        if src == dst:
            return (src,)
        prev: dict[str, str] = {src: src}
        queue: deque[str] = deque([src])
        while queue:
            node = queue.popleft()
            for nb in sorted(adj[node]):  # 동률은 사전식 우선
                if nb not in prev:
                    prev[nb] = node
                    if nb == dst:
                        path = [dst]
                        while prev[path[-1]] != path[-1]:
                            path.append(prev[path[-1]])
                        path.reverse()
                        return tuple(path)
                    queue.append(nb)
        return ()

    def backup_path(self, src: str, dst: str) -> tuple[str, ...]:
        """주 최단 경로와 내부 노드·간선을 공유하지 않는 백업 경로.

        주 경로(``mesh.shortest_path``)의 모든 *내부* 인스턴스와 *연속 간선*을 그래프에서
        제거한 뒤 src→dst 최단 경로를 다시 구한다. 따라서 주 경로의 어떤 중계가 죽어도
        백업 경로는 영향받지 않는다(엔드포인트만 공유). 백업이 없으면 빈 튜플,
        주 경로 자체가 없어도 빈 튜플. 미등록 노드는 ``KeyError``.

        주 경로는 메시 스냅샷(``self._adj``)에서 직접 BFS로 산정한다 — 메시가 생성
        이후 rebuild돼도 분석기는 스냅샷 일관성을 유지한다(`shortest_path` 와 동일한
        정렬 이웃 우선 BFS라 결과 경로 동일).
        """
        if src not in self._adj:
            raise KeyError(src)
        if dst not in self._adj:
            raise KeyError(dst)
        primary = self._bfs(self._adj, src, dst)
        if not primary or len(primary) < 2:
            return ()
        interior = set(primary[1:-1])
        primary_edges = {
            frozenset((primary[i], primary[i + 1])) for i in range(len(primary) - 1)
        }
        restricted: dict[str, set[str]] = {}
        for node, nbrs in self._adj.items():
            if node in interior:
                continue
            restricted[node] = {
                nb
                for nb in nbrs
                if nb not in interior
                and frozenset((node, nb)) not in primary_edges
            }
        return self._bfs(restricted, src, dst)

    def has_backup_path(self, src: str, dst: str) -> bool:
        """src→dst에 내부 노드·간선 분리 백업 경로가 존재하면 True."""
        return bool(self.backup_path(src, dst))

    # --- 생존 도달성 -------------------------------------------------------

    def surviving_reach(self, origin: str, failed: frozenset[str] | set[str]) -> dict[str, int]:
        """``failed`` 인스턴스들이 죽었을 때 origin에서 닿는 인스턴스 → 최소 홉 수.

        origin 자신이 ``failed`` 에 있으면 빈 dict(아무 데도 못 보냄). origin은 결과에
        홉 0으로 포함된다(살아 있다는 전제). 미등록 origin은 ``KeyError``.
        """
        if origin not in self._adj:
            raise KeyError(origin)
        failed_set = set(failed)
        if origin in failed_set:
            return {}
        reach: dict[str, int] = {origin: 0}
        queue: deque[str] = deque([origin])
        while queue:
            node = queue.popleft()
            hop = reach[node]
            for nb in self._adj[node]:
                if nb in failed_set or nb in reach:
                    continue
                reach[nb] = hop + 1
                queue.append(nb)
        return reach

    def summary(self) -> dict[str, int]:
        """결정적 복원력 요약 — 인스턴스 수·절단점 수·브리지 수."""
        articulation, bridges = self._tarjan()
        return {
            "instances": len(self._adj),
            "articulation_points": len(articulation),
            "bridges": len(bridges),
        }
