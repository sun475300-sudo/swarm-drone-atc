"""ODYSSEY Phase 433 (Federation): 신뢰 가중 메시 라우팅.

Phase 432 메시 토폴로지(`federation_mesh`)는 모든 인스턴스를 동등하게 보고 *홉 수*
만으로 최단 경로를 계산한다. 그러나 Phase 428 신뢰 모델(`federation_trust`)은 어떤
인스턴스가 협조 행위(핸드오버·충돌 협상·NOTAM 전파)를 신뢰성 있게 이행하는지를
정량화한다 — 신뢰가 낮은 인스턴스를 중계(relay)로 거치면 운영 의도·NOTAM 이 유실
되거나 늦게 전달될 위험이 크다. 홉 수만 보는 라우팅은 이 위험을 무시한다.

본 모듈은 메시(Phase 432) 위에서, 라우팅하는 인스턴스(origin) **자신의** 신뢰 믿음
(Phase 428)으로 각 중계 후보의 비용을 가중해 신뢰하는 이웃을 우선하는 결정적 최소
비용 경로를 계산한다. 라우팅은 항상 origin 의 관점에서 이뤄지므로(연합은 중앙 신뢰
권위가 없다), 같은 토폴로지라도 인스턴스마다 다른 경로를 선택할 수 있다.

비용 모형 (origin → node v 로 들어가는 간선):
    cost(v) = hop_cost + untrust_weight * (1 - trust(origin → v))
  - 완전 신뢰(trust=1.0) 이웃: cost = hop_cost (홉 수와 동일).
  - 미관찰 이웃: 중립 사전분포 trust=0.5 → cost = hop_cost + 0.5*untrust_weight.
  - 완전 불신(trust=0.0) 이웃: cost = hop_cost + untrust_weight (최대 페널티).
경로 비용은 거쳐 들어간 각 노드 비용의 합이며, 목적지가 고정이면 그 목적지 자체의
페널티는 모든 경로에 공통이라 경로 선택은 중계 신뢰도가 가른다.

설계 원칙 (federation_* 모듈 공통 규약):
- 무작위성 0 — 같은 토폴로지·신뢰 상태·origin 은 항상 같은 경로/비용(재현·감사 가능).
- 동률 분리 — 비용이 같은 경로는 경로 튜플의 사전식 순서로 결정적으로 분리한다.
- 기존 모듈 무수정 — Phase 432 메시·Phase 428 신뢰를 *읽기만* 하는 순수 추가 계층.

사용법::

    mesh = FederationMesh(discovery_service)
    trust = FederationTrustModel()
    # ... trust.observe(...) 로 평판 누적 ...
    router = TrustWeightedRouter(mesh, trust)
    router.route("uss-a", "uss-c")          # 신뢰 가중 최소 비용 경로
    router.avoid_untrusted_route("uss-a", "uss-c")  # 불신 중계 회피 경로
"""

from __future__ import annotations

import heapq
import math
from collections import deque

from simulation.federation_mesh import FederationMesh
from simulation.federation_trust import FederationTrustModel

# 각 홉의 기본 비용. 신뢰 페널티가 0이면 라우팅은 순수 홉 수 최단 경로로 환원된다.
DEFAULT_HOP_COST = 1.0

# 불신 페널티 스케일 — 완전 불신(trust=0) 이웃 1홉이 추가로 무는 비용.
# 기본 1.0 이면 불신 이웃 1홉(비용 2.0)이 신뢰 이웃 2홉(비용 2.0)과 동등해진다.
DEFAULT_UNTRUST_WEIGHT = 1.0

# Phase 428 federation_trust 의 신뢰 게이트 기본값과 일치(사설 상수 직접 import 대신
# 로컬 정의 — 읽기 전용 통합 계층이 상대 모듈의 내부 namespace 에 결합하지 않게 한다).
_DEFAULT_MIN_OBSERVATIONS = 5
_DEFAULT_TRUST_THRESHOLD = 0.5


class TrustWeightedRouter:
    """Phase 432 메시 위에서 Phase 428 신뢰로 가중한 결정적 최소 비용 라우터."""

    def __init__(
        self,
        mesh: FederationMesh,
        trust_model: FederationTrustModel,
        *,
        hop_cost: float = DEFAULT_HOP_COST,
        untrust_weight: float = DEFAULT_UNTRUST_WEIGHT,
        trust_threshold: float = _DEFAULT_TRUST_THRESHOLD,
        min_observations: int = _DEFAULT_MIN_OBSERVATIONS,
    ) -> None:
        if hop_cost <= 0.0:
            raise ValueError("hop_cost는 양수여야 합니다")
        if untrust_weight < 0.0:
            raise ValueError("untrust_weight는 음수일 수 없습니다")
        if min_observations < 0:
            raise ValueError("min_observations는 음수일 수 없습니다")
        # 신뢰 점수는 Beta 사후 평균이라 항상 (0, 1) 개구간. 경계 밖 임계값은 모든
        # 노드를 불신/신뢰로 단정해 avoid_untrusted_route 를 조용히 무력화하므로 거부.
        if not 0.0 < trust_threshold < 1.0:
            raise ValueError("trust_threshold는 (0, 1) 범위여야 합니다")
        self._mesh = mesh
        self._trust = trust_model
        self._hop_cost = float(hop_cost)
        self._untrust_weight = float(untrust_weight)
        self._threshold = float(trust_threshold)
        self._min_obs = int(min_observations)

    def relay_trust(self, origin: str, node: str) -> float:
        """origin 이 node 를 신뢰하는 정도(사후 평균). 자기 자신은 완전 신뢰 1.0."""
        if origin == node:
            return 1.0
        return self._trust.trust(origin, node)

    def _edge_cost(self, origin: str, node: str) -> float:
        """origin 관점에서 node 로 들어가는 간선 비용 — 낮은 신뢰일수록 높다."""
        return self._hop_cost + self._untrust_weight * (1.0 - self.relay_trust(origin, node))

    def _is_untrusted(self, origin: str, node: str) -> bool:
        """origin 이 충분히 관찰한 끝에 신뢰 임계값 미만으로 판정한 node 인가.

        미관찰(증거 부족) 노드는 불신으로 단정하지 않는다 — Phase 428 `untrusted`
        와 동일한 최소 관찰 게이트.
        """
        if origin == node:
            return False
        belief = self._trust.belief(origin, node)
        return belief.observations >= self._min_obs and belief.trust_score < self._threshold

    def _require_registered(self, *ids: str) -> None:
        known = set(self._mesh.instances())
        for iid in ids:
            if iid not in known:
                raise KeyError(iid)

    def route(self, origin: str, dst: str) -> tuple[str, ...]:
        """origin→dst 신뢰 가중 최소 비용 경로. 동률은 경로 튜플 사전식 우선.

        도달 불가면 빈 튜플, ``origin == dst`` 면 ``(origin,)``. 미등록은 ``KeyError``.

        결정성: 우선순위 큐는 ``(누적 비용, 경로 튜플)`` 키로 정렬되므로, 노드가
        처음 확정될 때(첫 pop) 그 노드로의 *최소 비용·동률이면 사전식 최소* 경로가
        고정된다. 후보가 기존 기록보다 사전식으로 엄격히 나을 때만 push 하므로
        동률 경로가 큐를 무한 증식시키지 않는다. (비용 동률 분리는 *정확한* float
        상등에 의존하며, 무리수 신뢰 분수에서 ULP 차이가 나면 그 미세 비용차로
        분리된다 — 어느 쪽이든 같은 입력은 항상 같은 경로를 내므로 재현성은 보장된다.)
        """
        self._require_registered(origin, dst)
        if origin == dst:
            return (origin,)
        start: tuple[float, tuple[str, ...]] = (0.0, (origin,))
        heap: list[tuple[float, tuple[str, ...]]] = [start]
        best: dict[str, tuple[float, tuple[str, ...]]] = {origin: start}
        finalized: set[str] = set()
        while heap:
            cost, path = heapq.heappop(heap)
            node = path[-1]
            if node in finalized:
                continue
            finalized.add(node)
            if node == dst:
                return path
            for nb in self._mesh.neighbors(node):  # 이미 정렬됨
                if nb in finalized:
                    continue
                cand = (cost + self._edge_cost(origin, nb), path + (nb,))
                # 사전식으로 엄격히 더 나은 후보일 때만 갱신·push → 큐 증식 방지.
                if nb not in best or cand < best[nb]:
                    best[nb] = cand
                    heapq.heappush(heap, cand)
        return ()

    def route_cost(self, origin: str, dst: str) -> float:
        """origin→dst 선택 경로의 총 비용. 도달 불가면 ``math.inf``, 동일 노드면 0.0."""
        path = self.route(origin, dst)
        if not path:
            return math.inf
        return sum(self._edge_cost(origin, node) for node in path[1:])

    def avoid_untrusted_route(self, origin: str, dst: str) -> tuple[str, ...]:
        """불신 중계(intermediate)를 거치지 않는 최단(홉 수) 경로. 동률은 정렬 이웃 우선.

        목적지 자체가 불신이어도 경로는 허용한다(전달 종단점이지 중계가 아님).
        그런 경로가 없으면 빈 튜플. ``origin == dst`` 면 ``(origin,)``. 미등록은 ``KeyError``.
        """
        self._require_registered(origin, dst)
        if origin == dst:
            return (origin,)
        prev: dict[str, str] = {origin: origin}
        queue: deque[str] = deque([origin])
        while queue:
            node = queue.popleft()
            for nb in self._mesh.neighbors(node):  # 정렬됨 → 동률 사전식 우선
                if nb in prev:
                    continue
                # 목적지는 종단점이므로 불신이어도 허용. 그 외 중계는 불신이면 회피.
                if nb != dst and self._is_untrusted(origin, nb):
                    continue
                prev[nb] = node
                if nb == dst:
                    return self._reconstruct(prev, dst)
                queue.append(nb)
        return ()

    def forwarding_table(self, origin: str) -> dict[str, str]:
        """origin 의 신뢰 가중 포워딩 테이블 {목적지: 다음 홉 이웃}.

        도달 가능한 각 목적지(origin 제외)에 대해 신뢰 가중 최소 비용 경로의 *첫
        이웃*을 매핑한다. 미등록은 ``KeyError``.
        """
        self._require_registered(origin)
        table: dict[str, str] = {}
        for dst in self._mesh.instances():
            if dst == origin:
                continue
            path = self.route(origin, dst)
            if len(path) >= 2:
                table[dst] = path[1]
        return table

    @staticmethod
    def _reconstruct(prev: dict[str, str], dst: str) -> tuple[str, ...]:
        path = [dst]
        while prev[path[-1]] != path[-1]:
            path.append(prev[path[-1]])
        path.reverse()
        return tuple(path)
