"""ODYSSEY Phase 437 (Federation): 신뢰 인지 분산 경로-벡터 라우팅.

Phase 436(`PathVectorRouting`)은 지역 이웃 지식만으로 분산 수렴하지만 *홉 수*만
metric으로 쓴다 — 어떤 이웃이 협조 행위를 신뢰성 있게 이행하는지는 무시한다.
Phase 433(`TrustWeightedRouter`)은 신뢰를 가중하지만 **한 origin이 전역 토폴로지를
통째로 보고** 그 origin의 신뢰로 *모든* 중계 노드를 평가하는 중앙식 계산이다 —
실제 inter-USS 연합에는 그런 중앙 신뢰 권위가 없다.

본 모듈은 둘의 공백을 메운다: Phase 432 메시 인접 위에서 **분산** 경로-벡터로 수렴하되
(Phase 436처럼 각 노드는 직접 이웃만 안다), 각 노드가 광고된 경로 중 하나를 고를 때
**자신이 직접 관찰한 그 다음 홉 이웃의 신뢰도**(Phase 428)를 1순위 선호로 적용한다.
즉 BGP의 LOCAL_PREF처럼, 노드는 더 신뢰하는 이웃으로 트래픽을 먼저 보낸다. 경로의
나머지 구간 신뢰는 그 구간을 고른 *하류 노드들*이 각자의 로컬 신뢰로 이미 반영했으므로,
한 경로의 신뢰 결정은 홉마다 분산되어 합성된다(중앙식 433과의 핵심 차이).

선호 키 (노드 ``n`` 이 목적지 ``dst`` 로 가는 후보 경로 ``(n, nb, ...)`` 평가):
    key = (untrust_penalty(n→nb), 홉 수, 경로 튜플)
  - ``untrust_penalty(n→nb) = untrust_weight * (1 - trust(n→nb))`` — Phase 428 사후 평균.
  - 1순위가 *다음 홉* 신뢰이므로(BGP LOCAL_PREF > AS-PATH 길이), 더 신뢰하는 이웃을
    거치면 홉이 더 늘어나도 그 경로를 택한다 — Phase 433과 같은 안전 논거(불신 중계로
    운영 의도·NOTAM 이 유실/지연될 위험 회피)를 분산 환경에 적용.
  - 신뢰 동률(특히 *관찰 0 → 모든 이웃 균일 0.5*)이면 페널티가 같아 키가 (상수, 홉, 경로)
    로 환원 → **Phase 436과 정확히 동일한 경로**(홉 최단·사전식). 이 정확 일치는 기본
    정수 prior(Beta(1,1))에서 미관찰 신뢰가 *비트 단위로 동일한* 0.5 라는 점에 기댄다 —
    Phase 433과 마찬가지로(거기 `route` docstring 참조) 동률 분리는 정확한 float 상등에
    의존하지만, 같은 입력은 항상 같은 출력을 내므로 재현성 자체는 어떤 prior 에서도 보장된다.
  - 신뢰는 후보를 *재배열*만 할 뿐 어떤 후보도 제거하지 않으므로 도달성은 메시(Phase 432)와 동일하다.

설계 원칙 (federation_* 공통 규약):
- 무작위성 0 — 같은 메시·신뢰 상태는 항상 같은 라우팅 테이블(재현·감사 가능).
- Jacobi(동기) 갱신 — 한 라운드는 직전 라운드 스냅샷만 참조해 노드 순회 순서와 무관.
- 기존 모듈 무수정 — Phase 432 메시·Phase 428 신뢰를 *읽기만* 하는 순수 추가 계층.
"""

from __future__ import annotations

from simulation.federation_mesh import FederationMesh
from simulation.federation_trust import FederationTrustModel

# 다음 홉 불신 페널티의 기본 가중치. Phase 433 `DEFAULT_UNTRUST_WEIGHT` 와 같은 의미.
DEFAULT_UNTRUST_WEIGHT = 1.0


class TrustPathVectorRouting:
    """Phase 432 메시에서 다음 홉 로컬 신뢰로 선호하는 분산 경로-벡터 라우터 (결정적)."""

    def __init__(
        self,
        mesh: FederationMesh,
        trust_model: FederationTrustModel,
        *,
        untrust_weight: float = DEFAULT_UNTRUST_WEIGHT,
    ) -> None:
        if untrust_weight < 0.0:
            raise ValueError("untrust_weight는 음수일 수 없습니다")
        # 메시 인접 스냅샷을 복사해 보관(이후 메시 rebuild와 독립).
        self._adj: dict[str, tuple[str, ...]] = mesh.adjacency()
        self._trust = trust_model
        self._untrust_weight = float(untrust_weight)
        # 인스턴스별 라우팅 테이블 {origin: {dst: 경로 튜플(origin..dst)}}.
        self._tables: dict[str, dict[str, tuple[str, ...]]] = {}
        self._rounds: int | None = None  # 수렴까지 걸린 라운드 수(미수렴 시 None)

    # --- 선호 키 -----------------------------------------------------------

    def _untrust_penalty(self, node: str, neighbor: str) -> float:
        """node 가 직접 이웃 neighbor 를 거칠 때의 불신 페널티(낮을수록 선호)."""
        return self._untrust_weight * (1.0 - self._trust.trust(node, neighbor))

    def _route_key(self, node: str, path: tuple[str, ...]) -> tuple[float, int, tuple[str, ...]]:
        """node 가 평가하는 후보 경로 ``path``(node..dst)의 선호 키.

        1순위 다음 홉 불신 페널티(BGP LOCAL_PREF), 2순위 홉 수, 3순위 경로 사전식.
        ``path`` 는 항상 길이 ≥ 2(자기 자신 경로는 평가 대상이 아님)이며 ``path[1]``
        이 node 의 직접 이웃 다음 홉이다.
        """
        return (self._untrust_penalty(node, path[1]), len(path), path)

    # --- 수렴 ---------------------------------------------------------------

    def converge(self) -> int:
        """경로-벡터 동기 라운드를 고정점(변화 없음)에 이를 때까지 반복하고 라운드 수 반환.

        각 라운드는 직전 라운드 스냅샷만 참조(Jacobi)하므로 노드 순회 순서와 무관하게
        결정적이다. 각 노드는 BGP 처럼 목적지별 *단일 최선 경로*만 광고하고, 다음 홉
        로컬 신뢰를 1순위로 한 선호 키(후보 경로 위의 엄격 전순서)로 후보를 고른다 —
        선호가 *다음 홉* 에만 의존하는(임의 경로별 정책이 아닌) next-hop local-pref 이라
        BGP 류 진동 없이 고정점으로 수렴한다.

        라운드 상한 = 노드 수는 *방어적 종결 캡* 이다(어떤 입력에도 무한 루프 없이 종결).
        실제 수렴은 `not changed` 로 조기 검출하며, 정상(연결) 메시에선 이 캡에 닿기 전에
        고정점에 이른다(테스트로 검증). 홉만 보는 Phase 436 은 지름 라운드에 수렴하지만,
        신뢰가 *더 긴* 경로를 선호할 수 있어 본 라우터의 수렴 라운드는 지름보다 클 수 있다.
        이미 수렴 상태면 캐시된 라운드 수를 반환한다(`self._adj`·신뢰 스냅샷 불변).
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
            new_tables = {node: dict(routes) for node, routes in snapshot.items()}
            changed = False
            for node in sorted(self._adj):  # 정렬 순회(결정성; Jacobi라 순서 무관)
                node_routes = new_tables[node]
                for nb in self._adj[node]:  # 이미 정렬된 이웃
                    for dst, adv_path in snapshot[nb].items():
                        if node in adv_path:  # path-vector 루프 방지(BGP AS-PATH)
                            continue
                        candidate = (node,) + adv_path
                        current = node_routes.get(dst)
                        if current is None or self._route_key(node, candidate) < self._route_key(
                            node, current
                        ):
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
        """origin→dst 선택 경로의 홉 수. ``origin == dst`` 면 0, 도달 불가면 -1."""
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
