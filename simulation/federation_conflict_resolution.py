"""연합 충돌 해소 — 인스턴스 간 우선순위 협상
================================================

ODYSSEY Phase 424 — 연합 운영(Federation Operations).

서로 다른 SDACS 인스턴스가 같은 4D 공역을 점유하려 할 때(Phase 422
`intents_conflict` 로 탐지), 어느 운영 의도가 그 공역을 점유하고 어느 쪽이
양보(CONTINGENT 전환)할지 **결정적으로** 협상한다.

협상 메커니즘은 Phase 602 `VickreyAuction`(2위 가격제 봉인입찰)을 재사용한다.
각 운영 의도의 입찰가는 우선순위에서 파생한다 — 낮은 priority 번호(=높은
우선순위)일수록 높은 입찰가를 낸다. 최고 입찰자가 공역을 점유(승자)하고,
청산가는 차순위 입찰가(Vickrey 2위 가격)로 기록한다.

설계 원칙:
- 무작위성 0 — 협상은 완전 결정적이어야 재현·감사 가능하다. 동률 우선순위는
  intent_id 의 안정적 해시(`hashlib.sha256`)로 분리한다(Python `hash()` 는
  실행마다 솔트가 달라 사용하지 않는다).
- 불변(immutable) — `apply_resolutions` 는 원본 의도를 변형하지 않고 패자만
  CONTINGENT 로 바꾼 새 의도 튜플을 반환한다.
- 감사 로그는 튜플로 노출(외부에서 변형 불가).

사용법::

    resolver = FederationConflictResolver()
    resolutions = resolver.resolve_all([intent_a, intent_b, intent_c])
    settled = resolver.apply_resolutions([intent_a, intent_b, intent_c], resolutions)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from itertools import combinations

from simulation.drone_auction_market import VickreyAuction
from simulation.operational_intent import OperationalIntent, intents_conflict

# 패자 의도가 전환되는 상태 (ASTM F3548-21 CONTINGENT 와 정렬).
CONTINGENT = "CONTINGENT"

# 우선순위 1단계 차이가 만드는 입찰가 간격. 동률 분리 가산값(tiebreak)은
# [0, _PRIORITY_STEP) 범위라 우선순위 밴드를 절대 넘지 못한다.
_PRIORITY_STEP = 1.0


@dataclass(frozen=True)
class ConflictResolution:
    """한 쌍의 충돌하는 운영 의도에 대한 협상 결과(불변 감사 단위)."""

    intent_a: str
    intent_b: str
    winner: str  # 경합 공역을 점유하는 의도
    loser: str  # 양보(CONTINGENT) 대상 의도
    winning_bid: float
    clearing_price: float  # Vickrey 2위 가격


class FederationConflictResolver:
    """우선순위 기반 Vickrey 협상으로 연합 공역 충돌을 해소한다."""

    def __init__(self, max_priority: int = 100) -> None:
        """``max_priority`` 보다 작은 priority 만 양(+)의 입찰가를 갖는다.

        ``OperationalIntent`` 는 ``priority >= 1`` 을 강제하므로, 어떤 의도든
        협상에 참여하려면 ``max_priority`` 가 최소 2 이상이어야 한다(그렇지 않으면
        모든 valid 의도가 ``priority_bid`` 에서 거부되는 사용 불가 resolver 가 된다).
        """
        if max_priority < 2:
            raise ValueError(f"max_priority 는 2 이상이어야 합니다 (받음: {max_priority})")
        self._max_priority = max_priority
        self._auction = VickreyAuction()
        self._log: list[ConflictResolution] = []

    def priority_bid(self, intent: OperationalIntent) -> float:
        """우선순위 → 입찰가. 낮은 priority 번호일수록 높은 입찰가."""
        if intent.priority >= self._max_priority:
            raise ValueError(
                f"priority({intent.priority}) 가 max_priority({self._max_priority}) 이상이라 "
                "협상 입찰가를 산정할 수 없습니다"
            )
        base = (self._max_priority - intent.priority) * _PRIORITY_STEP
        return base + self._tiebreak(intent.intent_id)

    def resolve_pair(
        self, a: OperationalIntent, b: OperationalIntent
    ) -> ConflictResolution | None:
        """두 의도가 충돌하면 협상 결과를 반환·기록, 아니면 None."""
        if not intents_conflict(a, b):
            return None
        bid_a = self.priority_bid(a)
        bid_b = self.priority_bid(b)
        outcome = self._auction.run_auction([(a.intent_id, bid_a), (b.intent_id, bid_b)])
        # run_auction 은 입찰 0건일 때만 None — 여기선 항상 2건이라 발생 불가지만,
        # 선언된 반환 타입(AuctionResult | None)에 대한 경계 가드를 명시한다.
        if outcome is None:
            raise RuntimeError(f"경매 결과 없음 — 의도 {a.intent_id} / {b.intent_id}")
        winner = outcome.winner
        loser = b.intent_id if winner == a.intent_id else a.intent_id
        resolution = ConflictResolution(
            intent_a=a.intent_id,
            intent_b=b.intent_id,
            winner=winner,
            loser=loser,
            winning_bid=outcome.highest_bid,
            clearing_price=outcome.price,
        )
        self._log.append(resolution)
        return resolution

    def resolve_all(
        self, intents: list[OperationalIntent]
    ) -> list[ConflictResolution]:
        """모든 쌍을 검사해 충돌하는 쌍마다 협상 결과를 반환한다.

        이미 양보(CONTINGENT)한 의도는 재경합에 참여시키지 않는다 — 그래야
        ``apply_resolutions`` 결과를 다시 넣어도 양보 의도가 승자를 뒤집지 않는다
        (쌍별 독립 경매라 전이적 일관성이 보장되지 않으므로 단발 협상 의미를 보존).
        """
        results: list[ConflictResolution] = []
        for a, b in combinations(intents, 2):
            if a.state == CONTINGENT or b.state == CONTINGENT:
                continue
            resolution = self.resolve_pair(a, b)
            if resolution is not None:
                results.append(resolution)
        return results

    def apply_resolutions(
        self,
        intents: list[OperationalIntent],
        resolutions: list[ConflictResolution],
    ) -> tuple[OperationalIntent, ...]:
        """패배한 의도를 CONTINGENT 로 전환한 새 튜플을 반환(원본 불변)."""
        losers = {r.loser for r in resolutions}
        return tuple(
            replace(oi, state=CONTINGENT) if oi.intent_id in losers else oi
            for oi in intents
        )

    @property
    def audit_log(self) -> tuple[ConflictResolution, ...]:
        """기록된 협상 결과(불변 튜플)."""
        return tuple(self._log)

    @staticmethod
    def _tiebreak(intent_id: str) -> float:
        """intent_id 의 안정적 해시를 [0, _PRIORITY_STEP) 로 사상(동률 분리)."""
        digest = hashlib.sha256(intent_id.encode("utf-8")).digest()
        fraction = int.from_bytes(digest[:8], "big") / 2**64
        return fraction * _PRIORITY_STEP
