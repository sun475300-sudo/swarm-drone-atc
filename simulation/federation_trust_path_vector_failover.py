"""ODYSSEY Phase 439 (Federation): 신뢰 인지 분산 경로-벡터 장애 우회 수렴.

연합 라우팅 2×2 격자의 마지막 빈 칸을 메운다:

|                | 고정 메시 1회 수렴            | 노드 장애 후 재수렴              |
|----------------|------------------------------|--------------------------------|
| **홉만**        | Phase 436 `PathVectorRouting`| Phase 438 `PathVectorFailover` |
| **신뢰 인지**   | Phase 437 `TrustPathVector…` | **본 모듈 (Phase 439)**         |

Phase 438 은 *홉 최단* 분산 경로-벡터가 인스턴스(USS) 장애 후 어떻게 재수렴하는지를
답하지만, 각 노드가 더 신뢰하는 다음 홉을 선호한다는 Phase 437 의 정책(BGP LOCAL_PREF)
은 반영하지 않는다. 반대로 Phase 437 은 신뢰를 반영하되 *고정* 메시만 다룬다. 본 모듈은
둘을 결합한다: 장애 집합을 메시에서 제거한 *살아남은* 인접 위에서 Phase 437 의
신뢰 인지 경로-벡터를 다시 수렴시켜(죽은 노드 경유 광고가 사라져 이웃이 차선 신뢰
경로로 재광고하는 분산 재수렴을 모사), 장애 전후의 *신뢰 가중* 경로를 비교한다.

  * **우회(rerouted)** — 장애 전후 모두 도달하지만 신뢰 가중 경로가 바뀐 (origin, dst).
  * **단절(lost)** — 장애 전엔 닿았으나 장애 후엔 닿지 못하는 목적지.
  * **재수렴 라운드** — 살아남은 메시에서 신뢰 인지 경로-벡터가 고정점에 이르는 라운드.

핵심 불변식(테스트로 고정):
  * 빈 장애 집합 → Phase 437 고정 메시 결과와 항등.
  * 신뢰 관찰이 전혀 없으면(모든 이웃 균일 0.5) 선호 키가 (상수, 홉, 경로)로 환원되어
    **Phase 438(홉만) 장애 분석과 정확히 동일** — 2×2 격자의 두 칸이 그 모서리에서 만난다.
  * 신뢰는 후보를 *재배열*만 할 뿐 제거하지 않으므로, 장애 후 도달성(어느 쌍이 단절되는가)
    은 신뢰와 무관하게 Phase 438 과 같다. 신뢰는 *어느 우회로를 고르는가* 에만 영향.

기존 모듈(437·438·432·428)을 *읽기만* 하는 순수 추가 계층이다. 외부 네트워크·랜덤 없이
동작하며 모든 출력은 정렬·결정적이다.
"""

from __future__ import annotations

from simulation.federation_mesh import FederationMesh
from simulation.federation_trust import FederationTrustModel
from simulation.federation_trust_path_vector import (
    DEFAULT_UNTRUST_WEIGHT,
    TrustPathVectorRouting,
)


class _AdjacencyMesh:
    """``adjacency()`` 하나만 노출해 Phase 437 라우터에 임의 인접을 주입하는 어댑터.

    `TrustPathVectorRouting` 은 생성 시 ``mesh.adjacency()`` 만 호출하므로, 장애 노드를
    제거한 인접 사전을 그대로 넘기면 Phase 437 수렴 로직을 무수정 재사용할 수 있다.
    (Phase 438 이 Phase 436 에 쓴 어댑터와 같은 발상 — 각 모듈이 자기 어댑터를 들고
    있어 모듈 간 사설 이름 의존이 없다.)
    """

    def __init__(self, adjacency: dict[str, tuple[str, ...]]) -> None:
        self._adjacency = adjacency

    def adjacency(self) -> dict[str, tuple[str, ...]]:
        return {node: tuple(nbrs) for node, nbrs in self._adjacency.items()}


class TrustPathVectorFailover:
    """노드 장애 전후의 *신뢰 가중* 분산 경로-벡터 경로를 비교하는 결정적 분석기.

    상태성: 생성 시 장애 전(전체 메시)·장애 후(살아남은 메시) 두 신뢰 인지 라우터를
    즉시 수렴해 보관한다. 이후 조회는 캐시된 수렴 결과를 읽기만 한다(불변).
    """

    def __init__(
        self,
        mesh: FederationMesh,
        trust_model: FederationTrustModel,
        failed: frozenset[str] | set[str],
        *,
        untrust_weight: float = DEFAULT_UNTRUST_WEIGHT,
    ) -> None:
        # 경계에서 fail-fast 검증: 가중치는 의존 라우터가 아닌 *이 경계* 에서도 거부한다
        # (CLAUDE.md "시스템 경계에서 검증" — 전이 의존에 위임하지 않음).
        if untrust_weight < 0.0:
            raise ValueError("untrust_weight는 음수일 수 없습니다")
        # 전체 메시 인접 스냅샷(이후 메시 rebuild와 독립).
        self._adj: dict[str, tuple[str, ...]] = mesh.adjacency()
        failed_set = set(failed)
        # 입력 검증(경계에서 fail-fast): 미등록 장애 id는 거부.
        unknown = failed_set - set(self._adj)
        if unknown:
            raise KeyError(next(iter(sorted(unknown))))
        self._failed: frozenset[str] = frozenset(failed_set)
        self._trust = trust_model

        # 장애 전: 전체 메시 위 신뢰 인지 경로-벡터.
        self._before = TrustPathVectorRouting(
            mesh, trust_model, untrust_weight=untrust_weight
        )
        self._before.converge()

        # 장애 후: 살아남은 노드만 남기고 죽은 노드로의 인접도 제거한 인접 위 라우터.
        # 신뢰 모델은 *그대로* 재사용한다 — 살아남은 노드에 대한 신뢰 믿음은 장애와
        # 무관하며, 죽은 이웃은 인접에서 빠져 신뢰 조회 대상이 되지 않는다.
        survivor_adj: dict[str, tuple[str, ...]] = {
            node: tuple(nb for nb in nbrs if nb not in failed_set)
            for node, nbrs in self._adj.items()
            if node not in failed_set
        }
        self._after = TrustPathVectorRouting(
            _AdjacencyMesh(survivor_adj), trust_model, untrust_weight=untrust_weight
        )
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
        """장애 후 살아남은 메시에서 신뢰 인지 경로-벡터가 재수렴하기까지의 라운드 수.

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
        """장애 후 origin→dst 신뢰 가중 경로(origin..dst). 도달 불가·죽은 노드면 빈 튜플.

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
        가 자기 경로를 제외하는 것과 일관). 도달성은 신뢰와 무관하므로 Phase 438 의
        `is_reroutable` 과 동일한 결과를 낸다(신뢰는 경로 선택만 바꾼다).
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
        단절 집합은 도달성에만 의존하므로 Phase 438 과 동일하다.
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
        """장애 전후 모두 닿지만 신뢰 가중 경로가 바뀐 목적지 → (장애 전 경로, 장애 후 경로).

        origin 또는 목적지가 죽은 경우는 단절(`lost_routes`)이지 우회가 아니므로 제외.
        origin == dst 자기 경로는 제외. 미등록 origin 은 ``KeyError``. Phase 438 과 달리
        경로 변화 판정은 *신뢰 가중* 선택 경로 기준이므로, 장애로 더 신뢰하던 다음 홉이
        죽어 차선 신뢰 경로로 옮겨가는 우회도 포착한다.
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
        목적지 수가 아님). ``lost_pairs`` 는 죽은 origin 의 단절까지 포함해 *모든*
        origin 을 순회하므로 실제 총 단절 영향을 과소계상하지 않는다. ``rerouted`` 는
        죽은 origin 이면 정의상 빈 dict 이므로 전 origin 순회와 생존 origin 순회 결과가
        같다.
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
