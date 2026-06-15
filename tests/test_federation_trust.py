"""ODYSSEY Phase 428 — 연합 신뢰 모델(인스턴스 간 Bayesian 평판) 단위 테스트.

Phase 608 Beta-Bernoulli 평판을 인스턴스 레벨로 재사용한다. 신뢰는 방향성이
있고(A→B ≠ B→A), 외부 무작위성 없이 완전 결정적이며, 같은 관찰 순서는 항상
같은 신뢰 상태를 만든다. 신뢰/불신 판정은 임계값과 최소 관찰 게이트를 거친다.
"""

from __future__ import annotations

import math

import pytest

from simulation.federation_trust import (
    FederationTrustModel,
    InstanceTrust,
    TrustEvent,
)


# --- InstanceTrust 믿음 ----------------------------------------------------


def test_neutral_prior_trust_score_is_half() -> None:
    # Arrange — Beta(1,1) 균등 사전분포
    belief = InstanceTrust(observer="a", target="b")

    # Act / Assert — 관찰 전 신뢰는 중립 0.5
    assert belief.trust_score == 0.5
    assert belief.observations == 0


def test_success_observation_raises_trust() -> None:
    # Arrange
    belief = InstanceTrust(observer="a", target="b")

    # Act
    updated = belief.updated(success=True)

    # Assert — α 증가, 신뢰 상승, 관찰 카운트 증가
    assert updated.alpha == 2.0
    assert updated.beta == 1.0
    assert updated.trust_score > 0.5
    assert updated.observations == 1


def test_failure_observation_lowers_trust() -> None:
    # Arrange
    belief = InstanceTrust(observer="a", target="b")

    # Act
    updated = belief.updated(success=False)

    # Assert — β 증가, 신뢰 하락
    assert updated.beta == 2.0
    assert updated.trust_score < 0.5
    assert updated.observations == 1


def test_updated_does_not_mutate_original() -> None:
    # Arrange
    belief = InstanceTrust(observer="a", target="b")

    # Act
    belief.updated(success=True)

    # Assert — 원본 불변(frozen + 새 인스턴스 반환)
    assert belief.alpha == 1.0
    assert belief.observations == 0


def test_uncertainty_decreases_with_observations() -> None:
    # Arrange
    sparse = InstanceTrust(observer="a", target="b").updated(True)

    # Act — 같은 방향으로 관찰을 더 쌓는다
    dense = sparse
    for _ in range(20):
        dense = dense.updated(True)

    # Assert — 관찰이 많을수록 불확실성 감소
    assert dense.uncertainty < sparse.uncertainty


def test_uncertainty_matches_beta_std_formula() -> None:
    # Arrange — α=3, β=2 인 상태 구성
    belief = InstanceTrust(observer="a", target="b", alpha=3.0, beta=2.0, observations=3)
    total = 5.0
    expected = math.sqrt(3.0 * 2.0 / (total**2 * (total + 1.0)))

    # Act / Assert
    assert belief.uncertainty == pytest.approx(expected)


def test_frozen_dataclass_rejects_mutation() -> None:
    # Arrange
    belief = InstanceTrust(observer="a", target="b")

    # Act / Assert
    with pytest.raises((AttributeError, TypeError)):
        belief.alpha = 99.0  # type: ignore[misc]


# --- FederationTrustModel 관찰·신뢰 ---------------------------------------


def test_unseen_pair_returns_prior_trust() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act / Assert — 관찰 없는 쌍은 중립 사전분포
    assert model.trust("uss-a", "uss-b") == 0.5
    assert model.belief("uss-a", "uss-b").observations == 0


def test_observe_updates_directed_trust() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act
    model.observe("uss-a", "uss-b", success=True, kind="handover")

    # Assert
    assert model.trust("uss-a", "uss-b") > 0.5
    assert model.belief("uss-a", "uss-b").observations == 1


def test_trust_is_directional() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act — a→b 만 긍정 관찰
    model.observe("uss-a", "uss-b", success=True)

    # Assert — 역방향 b→a 는 영향받지 않음(비대칭)
    assert model.trust("uss-a", "uss-b") > 0.5
    assert model.trust("uss-b", "uss-a") == 0.5


def test_repeated_failures_drive_trust_down() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act — 반복 실패 관찰
    for _ in range(10):
        model.observe("uss-a", "uss-b", success=False, kind="notam")

    # Assert
    assert model.trust("uss-a", "uss-b") < 0.2


def test_observe_returns_audit_event_with_resulting_state() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act
    event = model.observe("uss-a", "uss-b", success=True, kind="conflict")

    # Assert
    assert isinstance(event, TrustEvent)
    assert event.kind == "conflict"
    assert event.success is True
    assert event.observations == 1
    assert event.trust_score == model.trust("uss-a", "uss-b")


def test_deterministic_replay_same_trust() -> None:
    # Arrange — 동일 관찰 순서를 두 모델에 적용
    seq = [(True, "h"), (False, "n"), (True, "c"), (True, "h")]

    def run() -> float:
        m = FederationTrustModel()
        for success, kind in seq:
            m.observe("uss-a", "uss-b", success=success, kind=kind)
        return m.trust("uss-a", "uss-b")

    # Act / Assert — 무작위성 0 → 완전 재현
    assert run() == run()


# --- 신뢰 판정 게이트 ------------------------------------------------------


def test_is_trusted_requires_min_observations() -> None:
    # Arrange — 긍정이지만 관찰 1건뿐
    model = FederationTrustModel()
    model.observe("uss-a", "uss-b", success=True)

    # Act / Assert — 증거 부족이면 신뢰 단정 안 함
    assert model.is_trusted("uss-a", "uss-b", min_observations=5) is False


def test_is_trusted_after_enough_positive_observations() -> None:
    # Arrange
    model = FederationTrustModel()
    for _ in range(6):
        model.observe("uss-a", "uss-b", success=True)

    # Act / Assert
    assert model.is_trusted("uss-a", "uss-b", min_observations=5) is True


def test_is_not_trusted_when_below_threshold() -> None:
    # Arrange — 충분히 관찰됐지만 다수가 실패
    model = FederationTrustModel()
    for _ in range(6):
        model.observe("uss-a", "uss-b", success=False)

    # Act / Assert
    assert model.is_trusted("uss-a", "uss-b", min_observations=5) is False


def test_untrusted_lists_only_observed_low_trust_pairs() -> None:
    # Arrange
    model = FederationTrustModel()
    for _ in range(6):
        model.observe("uss-a", "uss-bad", success=False)
    for _ in range(6):
        model.observe("uss-a", "uss-good", success=True)
    # 관찰 부족한 저신뢰 쌍은 제외돼야 함
    model.observe("uss-a", "uss-sparse", success=False)

    # Act
    flagged = model.untrusted(min_observations=5)

    # Assert
    assert flagged == (("uss-a", "uss-bad"),)


def test_untrusted_is_deterministically_sorted() -> None:
    # Arrange — 여러 저신뢰 쌍을 의도적으로 역순 입력
    model = FederationTrustModel()
    for observer in ("uss-z", "uss-a", "uss-m"):
        for _ in range(6):
            model.observe(observer, "uss-b", success=False)

    # Act
    flagged = model.untrusted(min_observations=5)

    # Assert — 키 정렬 순서 고정
    assert flagged == (("uss-a", "uss-b"), ("uss-m", "uss-b"), ("uss-z", "uss-b"))


# --- 사전분포·검증 ---------------------------------------------------------


def test_custom_prior_shifts_initial_trust() -> None:
    # Arrange — 낙관적 사전분포 Beta(9,1)
    model = FederationTrustModel(prior_alpha=9.0, prior_beta=1.0)

    # Act / Assert
    assert model.trust("uss-a", "uss-b") == pytest.approx(0.9)


def test_non_positive_prior_rejected() -> None:
    # Act / Assert
    with pytest.raises(ValueError):
        FederationTrustModel(prior_alpha=0.0)
    with pytest.raises(ValueError):
        FederationTrustModel(prior_beta=-1.0)


def test_self_evaluation_rejected() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act / Assert — 인스턴스는 자기 자신을 평가할 수 없음
    with pytest.raises(ValueError):
        model.observe("uss-a", "uss-a", success=True)


def test_empty_instance_id_rejected() -> None:
    # Arrange
    model = FederationTrustModel()

    # Act / Assert
    with pytest.raises(ValueError):
        model.observe("", "uss-b", success=True)
    with pytest.raises(ValueError):
        model.observe("uss-a", "   ", success=True)


def test_instance_trust_rejects_negative_observations() -> None:
    # Act / Assert — 잘못된 observations 는 신뢰 게이트를 왜곡하므로 거부
    with pytest.raises(ValueError):
        InstanceTrust(observer="a", target="b", observations=-1)


def test_instance_trust_rejects_non_positive_alpha_beta() -> None:
    # Act / Assert
    with pytest.raises(ValueError):
        InstanceTrust(observer="a", target="b", alpha=0.0)
    with pytest.raises(ValueError):
        InstanceTrust(observer="a", target="b", beta=-2.0)


def test_instance_trust_rejects_self_pair() -> None:
    # Act / Assert
    with pytest.raises(ValueError):
        InstanceTrust(observer="a", target="a")


def test_whitespace_in_id_normalised_to_same_slot() -> None:
    # Arrange — 같은 논리 인스턴스를 앞뒤 공백 차이로 두 번 관찰
    model = FederationTrustModel()
    model.observe("uss-a", "uss-b", success=True)
    model.observe(" uss-a ", "uss-b ", success=True)

    # Assert — 공백은 정규화돼 단일 슬롯에 누적(중복 분기 없음)
    assert model.belief("uss-a", "uss-b").observations == 2
    assert model.belief("uss-a ", " uss-b").observations == 2


def test_multi_pair_replay_is_deterministic_including_log_order() -> None:
    # Arrange — 여러 쌍을 교차 관찰하는 시퀀스
    seq = [
        ("a", "b", True, "h"),
        ("c", "d", False, "n"),
        ("a", "b", False, "c"),
        ("c", "d", True, "h"),
    ]

    def run() -> tuple[tuple, ...]:
        m = FederationTrustModel()
        for o, t, s, k in seq:
            m.observe(o, t, success=s, kind=k)
        return tuple(
            (e.observer, e.target, e.kind, e.success, e.trust_score) for e in m.audit_log
        )

    # Act / Assert — 신뢰값뿐 아니라 감사 로그 순서까지 완전 재현
    assert run() == run()


def test_custom_prior_gates_is_trusted() -> None:
    # Arrange — 낙관적 사전분포지만 관찰이 부족하면 신뢰 단정 안 함
    model = FederationTrustModel(prior_alpha=9.0, prior_beta=1.0)

    # Act / Assert
    assert model.is_trusted("uss-a", "uss-b", min_observations=5) is False
    model.observe("uss-a", "uss-b", success=True)
    assert model.belief("uss-a", "uss-b").alpha == 10.0  # 사전분포 위에 누적


def test_untrusted_respects_custom_threshold() -> None:
    # Arrange — 6건 중 4성공/2실패 → 점수 ~0.625
    model = FederationTrustModel()
    for success in (True, True, True, True, False, False):
        model.observe("uss-a", "uss-b", success=success)

    # Act / Assert — 임계값 0.5 에선 통과(불신 아님), 0.7 에선 불신으로 분류
    assert model.untrusted(threshold=0.5, min_observations=5) == ()
    assert model.untrusted(threshold=0.7, min_observations=5) == (("uss-a", "uss-b"),)


def test_audit_log_is_immutable_tuple_in_order() -> None:
    # Arrange
    model = FederationTrustModel()
    model.observe("uss-a", "uss-b", success=True, kind="handover")
    model.observe("uss-a", "uss-b", success=False, kind="notam")

    # Act
    log = model.audit_log

    # Assert — 튜플(불변), 입력 순서 보존
    assert isinstance(log, tuple)
    assert len(log) == 2
    assert log[0].kind == "handover"
    assert log[1].kind == "notam"
