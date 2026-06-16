"""ODYSSEY Phase 436 (Federation): 분산 경로-벡터 라우팅 — 지역 지식만으로 수렴.

Phase 432(`FederationMesh.shortest_path`)와 Phase 433(`TrustWeightedRouter`)은
**전역 메시 스냅샷**을 한 노드가 통째로 보고 BFS·Dijkstra로 경로를 계산한다. 그러나
실제 inter-USS 연합에서는 어떤 인스턴스도 연합 전체 토폴로지를 알지 못한다 — 각
인스턴스는 *경계가 맞닿은 직접 이웃*만 알고, 그 이웃이 광고하는 도달성 정보를
주고받아 먼 목적지로 가는 경로를 *분산적으로* 학습해야 한다.

본 모듈은 Phase 432 메시 인접 위에서 **경로-벡터(path-vector) 라우팅**을 시뮬레이션한다.
각 인스턴스는 목적지별로 (자신→목적지) 전체 경로를 보유하고, 매 라운드 이웃에게
광고한다. 이웃은 광고된 경로 앞에 자신을 붙여 후보 경로를 만들되, **경로에 자신이
이미 들어 있으면 거부**(path-vector 루프 방지 — BGP AS-PATH 발상)한다. 동기 라운드를
변화가 없을 때까지 반복하면 루프 없는 최단(홉) 경로로 결정적으로 수렴한다.

Jacobi(동기) 갱신: 한 라운드의 모든 갱신은 *직전 라운드 스냅샷*만 참조하므로, 갱신
순서와 무관하게 결과가 같다(재현성). 수렴 라운드 수는 메시 지름(diameter)과 같다.

전역 스냅샷 라우터(432·433)와의 차이:
  * 432/433 — 중앙 관찰자가 전체 그래프를 보고 1회 계산. 신뢰 가중은 433이 담당.
  * 436(본 모듈) — 지역 이웃 지식만으로 분산 수렴. 홉 수 metric, 신뢰 비가중.

외부 네트워크·랜덤 없이 동작하며 모든 출력은 정렬·결정적이다.
"""

from __future__ import annotations

from simulation.federation_mesh import FederationMesh


def _better(candidate: tuple[str, ...], current: tuple[str, ...] | None) -> bool:
    """후보 경로가 현재 경로보다 우월하면 True.

    1순위 홉 수(길이)가 작은 쪽, 동률이면 사전식으로 작은 경로 튜플을 택한다.
    ``current`` 가 None(아직 경로 없음)이면 항상 후보 채택.
    """
    if current is None:
        return True
    if len(candidate) != len(current):
        return len(candidate) < len(current)
    return candidate < current


class PathVectorRouting:
    """Phase 432 메시 인접만으로 분산 수렴하는 경로-벡터 라우터 (결정적)."""

    def __init__(self, mesh: FederationMesh) -> None:
        # 메시 인접 스냅샷을 복사해 보관(이후 메시 rebuild와 독립).
        self._adj: dict[str, tuple[str, ...]] = mesh.adjacency()
        # 인스턴스별 라우팅 테이블 {origin: {dst: 경로 튜플(origin..dst)}}.
        self._tables: dict[str, dict[str, tuple[str, ...]]] = {}
        self._rounds: int | None = None  # 수렴까지 걸린 라운드 수(미수렴 시 None)

    # --- 수렴 ---------------------------------------------------------------

    def converge(self) -> int:
        """경로-벡터 동기 라운드를 고정점(변화 없음)에 이를 때까지 반복하고 라운드 수 반환.

        각 라운드는 직전 라운드 테이블 *스냅샷만* 참조(Jacobi)하고 새 테이블에 기록하므로
        노드 순회 순서와 무관하게 결정적이다. 단순 경로 최대 길이는 노드 수이므로 라운드
        상한을 노드 수로 두면 정상 메시는 그 전에 반드시 수렴한다(상한 = 안전 종결용).
        반환값은 *변화를 만든* 라운드 수로, 연결 메시에서 메시 지름과 같다. 이미 수렴
        상태에서 재호출하면 캐시된 라운드 수를 그대로 반환한다(`self._adj` 는 불변).
        """
        if self.is_converged:
            return self._rounds  # type: ignore[return-value]
        # 초기 상태: 각 노드는 자기 자신으로의 경로만 안다.
        tables: dict[str, dict[str, tuple[str, ...]]] = {
            node: {node: (node,)} for node in self._adj
        }
        bound = len(self._adj)  # 라운드 상한 = 노드 수 (지름 ≤ 노드 수 - 1)
        rounds = 0
        while rounds < bound:
            snapshot = tables
            # 이번 라운드 기록 대상: 각 노드의 직전 테이블 사본(읽기는 snapshot, 쓰기는 신규).
            new_tables = {node: dict(routes) for node, routes in snapshot.items()}
            changed = False
            for node in sorted(self._adj):  # 정렬 순회(결정성; Jacobi라 순서 무관)
                node_routes = new_tables[node]
                for nb in self._adj[node]:  # 이미 정렬된 이웃
                    for dst, adv_path in snapshot[nb].items():
                        if node in adv_path:  # path-vector 루프 방지
                            continue
                        candidate = (node,) + adv_path
                        if _better(candidate, node_routes.get(dst)):
                            node_routes[dst] = candidate
                            changed = True
            if not changed:
                self._tables = snapshot
                self._rounds = rounds
                return rounds
            tables = new_tables
            rounds += 1
        # 정상 메시에선 도달 불가(상한 = 노드 수 > 지름) — 방어적 종결.
        self._tables = tables
        self._rounds = rounds
        return rounds

    def _ensure_converged(self) -> None:
        if not self.is_converged:
            self.converge()

    @property
    def rounds_to_converge(self) -> int | None:
        """수렴까지 걸린 라운드 수. 아직 ``converge()`` 호출 전이면 None."""
        return self._rounds

    @property
    def is_converged(self) -> bool:
        """동기 라운드가 고정점에 도달했으면 True."""
        return self._rounds is not None

    # --- 조회 ---------------------------------------------------------------

    def instances(self) -> tuple[str, ...]:
        """라우팅 대상 인스턴스 id를 정렬해 반환한다."""
        return tuple(sorted(self._adj))

    def routes(self, origin: str) -> dict[str, tuple[str, ...]]:
        """origin의 수렴된 라우팅 테이블 {목적지: 경로 튜플}의 복사본.

        미등록 origin은 ``KeyError``. 필요 시 자동으로 ``converge()`` 한다.
        """
        if origin not in self._adj:
            raise KeyError(origin)
        self._ensure_converged()
        return dict(self._tables[origin])

    def best_path(self, origin: str, dst: str) -> tuple[str, ...]:
        """origin→dst 수렴 경로(origin..dst)를 반환한다.

        ``origin == dst`` 면 ``(origin,)``. 도달 불가면 빈 튜플. 미등록은 ``KeyError``.
        """
        if origin not in self._adj:
            raise KeyError(origin)
        if dst not in self._adj:
            raise KeyError(dst)
        self._ensure_converged()
        return self._tables[origin].get(dst, ())

    def hop_count(self, origin: str, dst: str) -> int:
        """origin→dst 최소 홉 수. ``origin == dst`` 면 0, 도달 불가면 -1."""
        path = self.best_path(origin, dst)
        return len(path) - 1 if path else -1

    def next_hop(self, origin: str, dst: str) -> str | None:
        """origin이 dst로 패킷을 넘길 첫 이웃. 자기 자신·도달 불가면 None."""
        path = self.best_path(origin, dst)
        if len(path) < 2:  # () 또는 (origin,)
            return None
        return path[1]

    def forwarding_table(self, origin: str) -> dict[str, str]:
        """origin의 포워딩 테이블 {목적지: 다음 홉 이웃} (자기 자신 제외)."""
        if origin not in self._adj:
            raise KeyError(origin)
        self._ensure_converged()
        table: dict[str, str] = {}
        for dst, path in self._tables[origin].items():
            if len(path) >= 2:
                table[dst] = path[1]
        return table
