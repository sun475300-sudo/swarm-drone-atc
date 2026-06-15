"""연합 신뢰 모델 — 인스턴스 간 Bayesian 평판
=================================================

ODYSSEY Phase 428 — 연합 운영(Federation Operations).

서로 다른 SDACS 인스턴스(USS)가 연합으로 운영될 때, 한 인스턴스는 상대
인스턴스가 약속한 협조 행위를 실제로 이행하는지 관찰한다 — 핸드오버 수락
(Phase 423), 충돌 협상 결과 준수(Phase 424), NOTAM 전파 수신 확인(Phase 425).
이 관찰을 누적해 **상대 인스턴스를 얼마나 신뢰할 수 있는가**를 정량화한다.

신뢰 모델은 Phase 608 `BayesianReputation` 의 Beta-Bernoulli 켤레(conjugate)
사전분포를 인스턴스 레벨로 재사용한다. 각 (관찰자→대상) 방향 쌍은 Beta(α, β)
믿음을 가지며, 성공 관찰은 α 를, 실패 관찰은 β 를 증가시킨다. 신뢰 점수는
사후 평균 ``α / (α + β)`` 이고, 불확실성은 Beta 분포 표준편차다.

설계 원칙 (federation_* 모듈 공통 규약):
- 무작위성 0 — 신뢰는 실제 연합 이벤트에서 관찰되며 시뮬레이션하지 않는다.
  같은 관찰 순서는 항상 같은 신뢰 상태를 만든다(재현·감사 가능).
- 불변(immutable) — 개별 믿음·감사 항목은 불변이다. ``InstanceTrust`` 는 frozen
  dataclass 이며 ``updated`` 는 원본을 변형하지 않고 갱신된 새 인스턴스를 반환한다.
  (모델 자체는 관찰을 누적하는 상태형 객체이며, 감사 로그는 `audit_log` 가
  방어적 튜플 스냅샷으로 노출해 외부 변형을 막는다 — federation_* 공통 패턴.)
- 방향성 — 신뢰는 비대칭이다. A 의 B 에 대한 신뢰와 B 의 A 에 대한 신뢰는
  별개의 믿음으로 추적한다. 인스턴스는 자기 자신을 평가하지 않는다.
- 감사 로그는 튜플로 노출(외부에서 변형 불가).

사용법::

    model = FederationTrustModel()
    model.observe("uss-a", "uss-b", success=True, kind="handover")
    model.observe("uss-a", "uss-b", success=False, kind="notam")
    model.trust("uss-a", "uss-b")          # 사후 평균 신뢰 점수
    model.is_trusted("uss-a", "uss-b")     # 임계값·최소 관찰 게이트 통과 여부
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

# 신뢰 판정에 필요한 최소 관찰 횟수. Phase 608 detect_malicious 의 증거 게이트
# (observations > 5)와 같은 취지 — 사전분포만으로 신뢰/불신을 단정하지 않는다.
# (게이트는 observations >= _DEFAULT_MIN_OBSERVATIONS 이므로 5건째에 통과한다.)
_DEFAULT_MIN_OBSERVATIONS = 5

# 신뢰/불신 경계 기본 임계값(사후 평균). 0.5 = 중립 사전분포 평균.
_DEFAULT_TRUST_THRESHOLD = 0.5


@dataclass(frozen=True)
class InstanceTrust:
    """한 관찰자 인스턴스가 한 대상 인스턴스에 갖는 Beta 신뢰 믿음(불변)."""

    observer: str
    target: str
    alpha: float = 1.0  # 성공 관찰 누적 (Beta 사전 + 사후)
    beta: float = 1.0  # 실패 관찰 누적
    observations: int = 0

    def __post_init__(self) -> None:
        """믿음 불변식 검증 — 잘못 구성된 믿음이 신뢰 게이트를 왜곡하지 못하게 한다.

        ``observations`` 가 음수면 `is_trusted` 최소 관찰 게이트가 무의미해지고,
        α·β 가 0 이하면 신뢰 점수·불확실성이 정의되지 않는다(0 나눗셈/허수).
        """
        if self.alpha <= 0.0 or self.beta <= 0.0:
            raise ValueError(f"α·β 는 양수여야 합니다 (받음: α={self.alpha}, β={self.beta})")
        if self.observations < 0:
            raise ValueError(f"observations 는 음수일 수 없습니다 (받음: {self.observations})")
        if self.observer == self.target:
            raise ValueError(
                f"인스턴스는 자기 자신에 대한 믿음을 가질 수 없습니다 (observer == target == {self.observer!r})"
            )

    @property
    def trust_score(self) -> float:
        """사후 평균 신뢰 점수 ``α / (α + β)`` ∈ (0, 1)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        """Beta 분포 표준편차 — 관찰이 쌓일수록 0 으로 수렴."""
        total = self.alpha + self.beta
        return math.sqrt(self.alpha * self.beta / (total**2 * (total + 1.0)))

    def updated(self, success: bool) -> InstanceTrust:
        """관찰 1건을 반영한 새 믿음을 반환한다(원본 불변)."""
        if success:
            return replace(self, alpha=self.alpha + 1.0, observations=self.observations + 1)
        return replace(self, beta=self.beta + 1.0, observations=self.observations + 1)


@dataclass(frozen=True)
class TrustEvent:
    """신뢰 관찰 1건의 불변 감사 단위(관찰 후 결과 신뢰 상태 포함)."""

    observer: str
    target: str
    kind: str  # 관찰 출처 분류 라벨(handover/conflict/notam 등)
    success: bool
    trust_score: float  # 이 관찰 직후의 사후 평균
    observations: int  # 이 관찰 직후의 누적 관찰 수


class FederationTrustModel:
    """방향성 Beta-Bernoulli 신뢰로 인스턴스 간 평판을 추적한다."""

    def __init__(self, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> None:
        """Beta 사전분포 Beta(prior_alpha, prior_beta). 둘 다 양수여야 한다.

        기본값 (1, 1) 은 균등 사전분포로, 첫 관찰 전 신뢰 점수는 중립 0.5 다.
        """
        if prior_alpha <= 0.0 or prior_beta <= 0.0:
            raise ValueError(
                f"사전분포 α·β 는 양수여야 합니다 (받음: α={prior_alpha}, β={prior_beta})"
            )
        self._prior_alpha = prior_alpha
        self._prior_beta = prior_beta
        self._beliefs: dict[tuple[str, str], InstanceTrust] = {}
        self._log: list[TrustEvent] = []

    def belief(self, observer: str, target: str) -> InstanceTrust:
        """(observer→target) 현재 믿음. 미관찰 쌍은 사전분포 믿음을 반환한다."""
        obs, tgt = self._validate_pair(observer, target)
        existing = self._beliefs.get((obs, tgt))
        if existing is not None:
            return existing
        return InstanceTrust(
            observer=obs,
            target=tgt,
            alpha=self._prior_alpha,
            beta=self._prior_beta,
        )

    def observe(
        self, observer: str, target: str, success: bool, kind: str = "interaction"
    ) -> TrustEvent:
        """협조 이벤트 1건을 관찰해 신뢰를 갱신하고 감사 이벤트를 반환한다."""
        obs, tgt = self._validate_pair(observer, target)
        updated = self.belief(obs, tgt).updated(success)
        self._beliefs[(obs, tgt)] = updated
        event = TrustEvent(
            observer=obs,
            target=tgt,
            kind=kind,
            success=success,
            trust_score=updated.trust_score,
            observations=updated.observations,
        )
        self._log.append(event)
        return event

    def trust(self, observer: str, target: str) -> float:
        """(observer→target) 사후 평균 신뢰 점수."""
        return self.belief(observer, target).trust_score

    def is_trusted(
        self,
        observer: str,
        target: str,
        threshold: float = _DEFAULT_TRUST_THRESHOLD,
        min_observations: int = _DEFAULT_MIN_OBSERVATIONS,
    ) -> bool:
        """신뢰 점수가 임계값 이상이고 충분히 관찰됐으면 True.

        ``min_observations`` 미만이면 증거 부족으로 신뢰를 단정하지 않는다(False).
        """
        belief = self.belief(observer, target)
        if belief.observations < min_observations:
            return False
        return belief.trust_score >= threshold

    def untrusted(
        self,
        threshold: float = _DEFAULT_TRUST_THRESHOLD,
        min_observations: int = _DEFAULT_MIN_OBSERVATIONS,
    ) -> tuple[tuple[str, str], ...]:
        """신뢰 점수가 임계값 미만인 (충분히 관찰된) 쌍을 결정적 순서로 반환."""
        flagged = [
            key
            for key, belief in self._beliefs.items()
            if belief.observations >= min_observations and belief.trust_score < threshold
        ]
        return tuple(sorted(flagged))

    @property
    def audit_log(self) -> tuple[TrustEvent, ...]:
        """기록된 신뢰 관찰(불변 튜플)."""
        return tuple(self._log)

    @staticmethod
    def _validate_pair(observer: str, target: str) -> tuple[str, str]:
        """관찰자·대상 식별자를 검증·정규화(strip)한 키 튜플을 반환한다.

        식별자를 strip 한 뒤 키로 쓰므로 ``"uss-a"`` 와 ``"uss-a "`` 가 별개의
        신뢰 슬롯으로 분기되지 않는다(앞뒤 공백으로 인한 조용한 중복 방지).
        """
        if not observer or not observer.strip():
            raise ValueError("observer 인스턴스 식별자는 비어 있을 수 없습니다")
        if not target or not target.strip():
            raise ValueError("target 인스턴스 식별자는 비어 있을 수 없습니다")
        obs, tgt = observer.strip(), target.strip()
        if obs == tgt:
            raise ValueError(
                f"인스턴스는 자기 자신을 평가할 수 없습니다 (observer == target == {obs!r})"
            )
        return (obs, tgt)
