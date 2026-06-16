"""ODYSSEY Phase 439 (Federation): 신뢰 한정 도달성 통합 토폴로지 — 3+ 인스턴스.

Phase 432(`FederationMesh`)는 디스커버리에서 구성한 *연결성*만, Phase 428
(`FederationTrustModel`)은 인스턴스 쌍 *신뢰*만 답한다. Phase 433
(`TrustWeightedRouter`)은 둘을 합치되 **가장 싼 신뢰 가중 경로 하나**를 고른다.
그러나 3개 이상의 인스턴스가 중계(relay)로 엮이는 연합에서 운영자가 실제로 묻는
질문 — **"목적지까지 신뢰할 수 있는 중계만 거치는 경로가 *존재하는가*"** — 는
아무도 답하지 않는다(존재성 ≠ 최소 비용). 중계가 끼어드는 3+ 인스턴스에서만
의미가 생기는 질문이다(2-인스턴스 직결엔 중계가 없다).

본 모듈은 연결성(Phase 432)과 신뢰(Phase 428)를 합쳐, 한 origin 관점에서 연합 내
모든 목적지를 도달성 *품질*로 분류하는 읽기 전용 관측(observability) 뷰다:

  * ``SELF``            — origin == dst.
  * ``DIRECT``          — 직접 이웃(중계 없음). 중계 위험이 정의상 없다.
  * ``RELAYED_TRUSTED`` — 다중 홉. *모든 중계가 origin 이 적극 신뢰*(Phase 428 증거
                          게이트 통과)하는 경로가 존재한다.
  * ``RELAYED_RISKY``   — 다중 홉. 도달은 가능하나 위 의미의 완전-신뢰 경로가 없다
                          (어느 경로든 미검증/저신뢰 중계가 끼어든다).
  * ``UNREACHABLE``     — 어떤 경로도 없다.

Phase 433 `avoid_untrusted_route` 와의 핵심 차이: 433 은 *알려진 불신*(충분 관찰 +
저점수)만 회피하므로 미검증(증거 부족) 중계는 통과시킨다("유죄 입증 전 무죄"). 본
모듈의 신뢰 경로는 더 엄격해 각 중계가 *적극 신뢰*(`is_trusted` True)여야 한다 —
"모든 중계가 검증됐다"는 더 강한 포스처(posture) 진술. 따라서 둘은 상보적이다.

신뢰는 방향성이므로(Phase 428) 경로 판정은 항상 origin 자신의 신뢰 믿음으로만
한다(Phase 433 과 동일 철학: 연합엔 중앙 신뢰 권위가 없다). 외부 네트워크·랜덤
없이 동작하며 모든 출력은 정렬·결정적이다. 기존 모듈은 무수정 순수 추가다.
"""

from __future__ import annotations

from collections import deque

from simulation.federation_mesh import FederationMesh
from simulation.federation_trust import FederationTrustModel

# Phase 428/433 과 동일한 신뢰 게이트 기본값(사설 상수 import 대신 로컬 정의).
_DEFAULT_TRUST_THRESHOLD = 0.5
_DEFAULT_MIN_OBSERVATIONS = 5

# 도달성 분류 라벨(상수로 노출해 호출측이 문자열 오타 없이 비교).
CLASS_SELF = "SELF"
CLASS_DIRECT = "DIRECT"
CLASS_RELAYED_TRUSTED = "RELAYED_TRUSTED"
CLASS_RELAYED_RISKY = "RELAYED_RISKY"
CLASS_UNREACHABLE = "UNREACHABLE"

#: ``summary()`` 가 항상 모든 키를 0 이상으로 채우도록 하는 *순서쌍* 분류 라벨.
#: ``CLASS_SELF`` 는 origin==dst 전용이라 순서쌍(origin != dst) 집계엔 없으므로 의도적 제외.
REACHABILITY_CLASSES = (
    CLASS_DIRECT,
    CLASS_RELAYED_TRUSTED,
    CLASS_RELAYED_RISKY,
    CLASS_UNREACHABLE,
)


class FederationTopologyView:
    """연결성(Phase 432)·신뢰(Phase 428)를 합친 신뢰 한정 도달성 통합 뷰.

    상태성: 메시·신뢰 모델 스냅샷에 대한 읽기 전용 질의기다. 어느 메서드도 메시나
    신뢰 모델을 변경하지 않으며, 동일 입력엔 항상 동일 출력을 낸다.
    """

    def __init__(
        self,
        mesh: FederationMesh,
        trust_model: FederationTrustModel,
        *,
        trust_threshold: float = _DEFAULT_TRUST_THRESHOLD,
        min_observations: int = _DEFAULT_MIN_OBSERVATIONS,
    ) -> None:
        # 입력 검증(경계에서 fail-fast) — Phase 433 과 동일 규약.
        if not 0.0 < trust_threshold < 1.0:
            raise ValueError("trust_threshold는 (0, 1) 범위여야 합니다")
        if min_observations < 0:
            raise ValueError("min_observations는 음수일 수 없습니다")
        self._mesh = mesh
        self._trust = trust_model
        self._threshold = float(trust_threshold)
        self._min_obs = int(min_observations)
        # 등록 인스턴스 집합 스냅샷 — 명시적 멤버십 검증용(Phase 433 규약과 일치).
        self._known: frozenset[str] = frozenset(mesh.instances())

    # --- 기본 조회 ---------------------------------------------------------

    def instances(self) -> tuple[str, ...]:
        """메시에 등록된 모든 인스턴스 id를 정렬해 반환한다."""
        return self._mesh.instances()

    def _is_trusted_relay(self, origin: str, node: str) -> bool:
        """origin 이 node 를 *적극* 신뢰하면 True(증거 게이트 + 임계값 통과).

        미검증(관찰 부족)이면 False — 적극 신뢰가 아니므로 완전-신뢰 경로에서 배제.
        """
        return self._trust.is_trusted(
            origin, node, threshold=self._threshold, min_observations=self._min_obs
        )

    def _require_registered(self, *ids: str) -> None:
        for iid in ids:
            if iid not in self._known:
                raise KeyError(iid)

    # --- 신뢰 한정 경로 ----------------------------------------------------

    def trusted_path(self, origin: str, dst: str) -> tuple[str, ...]:
        """중계가 모두 origin 의 적극 신뢰인 최단(홉) 경로. 동률은 정렬 이웃 우선.

        목적지 자체는 종단점이므로 신뢰 여부와 무관하게 허용한다(중계가 아님).
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
                # 목적지는 종단점이라 허용. 그 외 중계는 적극 신뢰일 때만 통과.
                if nb != dst and not self._is_trusted_relay(origin, nb):
                    continue
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

    # --- 도달성 분류 -------------------------------------------------------

    def reachability_class(self, origin: str, dst: str) -> str:
        """(origin, dst) 의 도달성 품질을 5개 라벨 중 하나로 분류한다. 미등록은 ``KeyError``."""
        self._require_registered(origin, dst)
        if origin == dst:
            return CLASS_SELF
        if dst in self._mesh.neighbors(origin):
            return CLASS_DIRECT
        if not self._mesh.shortest_path(origin, dst):
            return CLASS_UNREACHABLE
        if self.trusted_path(origin, dst):
            return CLASS_RELAYED_TRUSTED
        return CLASS_RELAYED_RISKY

    def classify(self, origin: str) -> dict[str, str]:
        """origin 에서 본 *다른 모든* 인스턴스의 도달성 분류 {dst: 라벨}. 미등록은 ``KeyError``."""
        self._require_registered(origin)
        return {
            dst: self.reachability_class(origin, dst)
            for dst in self._mesh.instances()
            if dst != origin
        }

    # --- 집계 도달 집합 ----------------------------------------------------

    def trusted_reach(self, origin: str) -> tuple[str, ...]:
        """origin 이 *불신 중계 없이* 닿는 목적지를 정렬해 반환한다(DIRECT + RELAYED_TRUSTED).

        직접 이웃은 중계가 없어 정의상 포함된다. ``risky_reach`` 와 동일하게 단일
        분류 경로(`classify`)에 위임해 라벨 정의와 항상 일치한다. 미등록은 ``KeyError``.
        """
        return tuple(
            sorted(
                dst
                for dst, label in self.classify(origin).items()
                if label in (CLASS_DIRECT, CLASS_RELAYED_TRUSTED)
            )
        )

    def risky_reach(self, origin: str) -> tuple[str, ...]:
        """도달은 가능하나 완전-신뢰 경로가 없는 목적지를 정렬해 반환한다(RELAYED_RISKY).

        미등록은 ``KeyError``.
        """
        self._require_registered(origin)
        return tuple(
            sorted(
                dst
                for dst, label in self.classify(origin).items()
                if label == CLASS_RELAYED_RISKY
            )
        )

    def summary(self) -> dict[str, int]:
        """연합 전체의 도달성 분류 분포 — 모든 순서쌍 (origin, dst), origin != dst.

        ``REACHABILITY_CLASSES`` 의 모든 라벨을 키로 0 이상 보장. SELF 는 origin==dst
        만 해당하므로 순서쌍 집계에서 제외된다. 값은 *순서 있는 쌍* 수다.
        """
        counts: dict[str, int] = {label: 0 for label in REACHABILITY_CLASSES}
        for origin in self._mesh.instances():
            for dst, label in self.classify(origin).items():
                counts[label] += 1
        return counts
