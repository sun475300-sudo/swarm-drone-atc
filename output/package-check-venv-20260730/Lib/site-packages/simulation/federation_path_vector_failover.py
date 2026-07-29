"""ODYSSEY Phase 438 (Federation): 분산 경로-벡터 장애 우회 수렴 — 노드 실패 후 재수렴.

Phase 436(`PathVectorRouting`)·437(`TrustAwarePathVectorRouting`)은 *고정된* 메시
스냅샷 위에서 분산 경로-벡터를 한 번 수렴시킨다. Phase 435(`FederationResilientRouting`)
는 어떤 인스턴스가 단일 장애점인지, 내부 분리 백업 경로가 있는지를 *중앙에서 구조적으로*
분석한다. 그러나 둘 사이의 공백 — **하나 이상의 인스턴스(USS)가 실제로 죽었을 때
분산 경로-벡터 프로토콜이 어떻게 재수렴하고, 어느 경로가 우회되고 어느 경로가
끊기는지** — 는 아무도 답하지 않는다.

본 모듈은 그 공백을 메운다. 장애 집합을 메시에서 제거한 뒤 *살아남은* 인접 위에서
Phase 436 경로-벡터 수렴을 다시 돌려(즉 죽은 노드를 지나던 광고가 사라져 이웃들이
대체 경로로 재광고하는 분산 재수렴을 모사) 장애 전후를 비교한다.

  * **우회(rerouted)** — 장애 전후 모두 도달하지만 경로가 바뀐 (origin, dst) 쌍.
  * **단절(lost)** — 장애 전엔 닿았으나 장애 후엔 닿지 못하는 목적지.
  * **재수렴 라운드** — 살아남은 메시에서 경로-벡터가 고정점에 이르기까지의 라운드 수.

경로-벡터는 전체 경로를 광고하므로(AS-PATH 발상) 루프가 경로 검사로 차단되어
거리-벡터의 count-to-infinity 가 없다. 따라서 장애 후 재수렴 결과는 *살아남은 메시에
대한 콜드스타트 수렴과 동일한 고정점*이며, 이는 Phase 436 을 그대로 재사용해(인접
어댑터 경유, 436 코드 무수정) 계산한다. Phase 435 의 구조적 보장과 교차 검증된다:
주 경로의 내부 중계만 죽으면(백업 경로 존재 시) 목적지는 반드시 우회로 살아남는다.

외부 네트워크·랜덤 없이 동작하며 모든 출력은 정렬·결정적이다.
"""

from __future__ import annotations

from simulation.federation_mesh import FederationMesh
from simulation.federation_path_vector import PathVectorRouting


class _AdjacencyMesh:
    """``adjacency()`` 하나만 노출해 Phase 436 라우터에 임의 인접을 주입하는 어댑터.

    `PathVectorRouting` 은 생성 시 ``mesh.adjacency()`` 만 호출하므로, 장애 노드를
    제거한 인접 사전을 그대로 넘기면 Phase 436 수렴 로직을 무수정 재사용할 수 있다.
    """

    def __init__(self, adjacency: dict[str, tuple[str, ...]]) -> None:
        self._adjacency = adjacency

    def adjacency(self) -> dict[str, tuple[str, ...]]:
        return {node: tuple(nbrs) for node, nbrs in self._adjacency.items()}


class PathVectorFailover:
    """노드 장애 전후의 분산 경로-벡터 경로를 비교하는 결정적 분석기.

    상태성: 생성 시 장애 전(전체 메시)·장애 후(살아남은 메시) 두 라우터를 즉시 수렴해
    보관한다. 이후 조회는 캐시된 수렴 결과를 읽기만 한다(불변).
    """

    def __init__(self, mesh: FederationMesh, failed: frozenset[str] | set[str]) -> None:
        # 전체 메시 인접 스냅샷(이후 메시 rebuild와 독립).
        self._adj: dict[str, tuple[str, ...]] = mesh.adjacency()
        failed_set = set(failed)
        # 입력 검증(경계에서 fail-fast): 미등록 장애 id는 거부.
        unknown = failed_set - set(self._adj)
        if unknown:
            raise KeyError(next(iter(sorted(unknown))))
        self._failed: frozenset[str] = frozenset(failed_set)

        # 장애 전: 전체 메시 위 경로-벡터.
        self._before = PathVectorRouting(mesh)
        self._before.converge()

        # 장애 후: 살아남은 노드만 남기고 죽은 노드로의 인접도 제거한 인접 위 경로-벡터.
        survivor_adj: dict[str, tuple[str, ...]] = {
            node: tuple(nb for nb in nbrs if nb not in failed_set)
            for node, nbrs in self._adj.items()
            if node not in failed_set
        }
        self._after = PathVectorRouting(_AdjacencyMesh(survivor_adj))
        self._after.converge()

    # --- 기본 조회 ---------------------------------------------------------

    def failed_instances(self) -> tuple[str, ...]:
        """장애 인스턴스 id를 정렬해 반환한다."""
        return tuple(sorted(self._failed))

    def survivors(self) -> tuple[str, ...]:
        """장애 후에도 살아남은 인스턴스 id를 정렬해 반환한다."""
        return tuple(sorted(node for node in self._adj if node not in self._failed))

    @property
    def reconvergence_rounds(self) -> int:
        """장애 후 살아남은 메시에서 경로-벡터가 재수렴하기까지의 라운드 수.

        ``__init__`` 에서 항상 ``converge()`` 를 호출하므로 비-None 이 보장된다.
        """
        rounds = self._after.rounds_to_converge
        assert rounds is not None  # __init__ 에서 converge() 보장
        return rounds

    def _require(self, instance_id: str) -> None:
        if instance_id not in self._adj:
            raise KeyError(instance_id)

    # --- 장애 후 경로 ------------------------------------------------------

    def surviving_path(self, origin: str, dst: str) -> tuple[str, ...]:
        """장애 후 origin→dst 경로(origin..dst). 도달 불가·죽은 노드면 빈 튜플.

        origin/dst 가 장애 노드이거나 도달 불가면 ``()``. 미등록 노드는 ``KeyError``.
        """
        self._require(origin)
        self._require(dst)
        if origin in self._failed or dst in self._failed:
            return ()
        return self._after.best_path(origin, dst)

    def is_reroutable(self, origin: str, dst: str) -> bool:
        """장애 전 닿던 origin→dst 가 장애 후에도 (경로가 바뀌더라도) 여전히 닿으면 True.

        장애 전에 이미 도달 불가였거나, origin/dst 자체가 죽었으면 False. 자기
        경로(``origin == dst``)는 의미 있는 라우팅 대상이 아니므로 False(`rerouted`
        가 자기 경로를 제외하는 것과 일관).
        """
        self._require(origin)
        self._require(dst)
        if origin == dst:
            return False
        if origin in self._failed or dst in self._failed:
            return False
        before = self._before.best_path(origin, dst)
        if not before:
            return False
        return bool(self._after.best_path(origin, dst))

    # --- 전후 비교 ---------------------------------------------------------

    def lost_routes(self, origin: str) -> tuple[str, ...]:
        """장애 전엔 닿았으나 장애 후엔 닿지 못하는 목적지를 정렬해 반환한다.

        origin 자신이 *죽었으면*(장애 집합 포함) 장애 전 닿던 모든 목적지가 단절로
        집계된다(죽은 origin 은 유효한 조회 대상 — KeyError 아님). 죽은 목적지도
        닿을 수 없게 되므로 단절로 집계된다. *미등록*(메시에 없는) origin 만 ``KeyError``.
        """
        self._require(origin)
        before = self._before.routes(origin)
        lost: list[str] = []
        for dst in before:
            if dst == origin:
                continue
            if origin in self._failed or dst in self._failed:
                lost.append(dst)
                continue
            if not self._after.best_path(origin, dst):
                lost.append(dst)
        return tuple(sorted(lost))

    def rerouted(self, origin: str) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
        """장애 전후 모두 닿지만 경로가 바뀐 목적지 → (장애 전 경로, 장애 후 경로).

        origin 또는 목적지가 죽은 경우는 단절(`lost_routes`)이지 우회가 아니므로 제외.
        origin == dst 자기 경로는 제외. 미등록 origin 은 ``KeyError``.
        """
        self._require(origin)
        if origin in self._failed:
            return {}
        before = self._before.routes(origin)
        changed: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        for dst, before_path in before.items():
            if dst == origin or dst in self._failed:
                continue
            after_path = self._after.best_path(origin, dst)
            if after_path and after_path != before_path:
                changed[dst] = (before_path, after_path)
        return changed

    def summary(self) -> dict[str, int]:
        """결정적 장애 영향 요약 — 생존 수·단절 쌍 수·우회 쌍 수·재수렴 라운드.

        ``lost_pairs``·``rerouted_pairs`` 는 *순서 있는* (origin, dst) 쌍 수다(고유
        목적지 수가 아님 — 죽은 목적지는 닿던 모든 origin 에서 각각 단절로 집계).
        ``lost_pairs`` 는 죽은 origin 의 단절까지 포함해 *모든* origin 을 순회하므로
        실제 총 단절 영향을 과소계상하지 않는다. ``rerouted`` 는 죽은 origin 이면
        정의상 빈 dict 이므로 전 origin 순회와 생존 origin 순회 결과가 같다.
        """
        total_lost = 0
        total_rerouted = 0
        for origin in sorted(self._adj):
            total_lost += len(self.lost_routes(origin))
            total_rerouted += len(self.rerouted(origin))
        return {
            "survivors": len(self.survivors()),
            "failed": len(self._failed),
            "lost_pairs": total_lost,
            "rerouted_pairs": total_rerouted,
            "reconvergence_rounds": self.reconvergence_rounds,
        }
