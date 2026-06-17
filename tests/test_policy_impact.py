"""ODYSSEY Phase 469 — 정책 영향 시뮬레이션 비교 엔진 테스트.

규제 파라미터 변경 효과 비교·순위·리포트 엔진의 결정성과 방향성 정확성을
결정적 토이 평가 함수로 검증한다 (시뮬레이터 비의존).
"""
from __future__ import annotations

import math

import pytest

from simulation.policy_impact import (
    PolicyImpactAnalyzer,
    PolicyKPIs,
    RegulatoryPolicy,
    _pct_delta,
)

BASELINE = RegulatoryPolicy(min_separation_m=5.0, max_altitude_m=120.0, max_speed_mps=15.0)


def toy_evaluate(policy: RegulatoryPolicy) -> PolicyKPIs:
    """결정적 토이 모델: 이격 거리↑ → 충돌↓·해결률↑ 이지만 처리량↓.

    실제 물리 모델이 아니라 비교 엔진을 검증하기 위한 단조 토이 함수다.
    """
    sep = policy.min_separation_m
    return PolicyKPIs(
        conflict_resolution_rate=min(1.0, 0.80 + 0.02 * sep),
        collisions=max(0.0, 20.0 - 2.0 * sep),
        throughput=max(0.0, 100.0 - 3.0 * sep),
        mean_completion_time_s=60.0 + 1.5 * sep,
    )


# ── RegulatoryPolicy ──────────────────────────────────────────────


def test_policy_rejects_nonpositive_parameter():
    with pytest.raises(ValueError):
        RegulatoryPolicy(min_separation_m=0.0, max_altitude_m=120.0, max_speed_mps=15.0)


def test_with_changes_returns_new_instance_without_mutation():
    # Arrange / Act
    changed = BASELINE.with_changes(min_separation_m=10.0)

    # Assert
    assert changed.min_separation_m == 10.0
    assert BASELINE.min_separation_m == 5.0  # 원본 불변
    assert changed.max_altitude_m == BASELINE.max_altitude_m


def test_with_changes_rejects_unknown_parameter():
    with pytest.raises(ValueError):
        BASELINE.with_changes(unknown_knob=1.0)


# ── PolicyKPIs ────────────────────────────────────────────────────


def test_kpis_reject_resolution_rate_out_of_range():
    with pytest.raises(ValueError):
        PolicyKPIs(
            conflict_resolution_rate=1.5,
            collisions=0.0,
            throughput=10.0,
            mean_completion_time_s=60.0,
        )


def test_kpis_reject_negative_collisions():
    with pytest.raises(ValueError):
        PolicyKPIs(
            conflict_resolution_rate=0.9,
            collisions=-1.0,
            throughput=10.0,
            mean_completion_time_s=60.0,
        )


# ── pct_delta 규약 ────────────────────────────────────────────────


def test_pct_delta_zero_baseline_increase_is_positive_infinity():
    assert _pct_delta(0.0, 5.0) == math.inf


def test_pct_delta_zero_baseline_unchanged_is_zero():
    assert _pct_delta(0.0, 0.0) == 0.0


def test_pct_delta_normal_case():
    assert _pct_delta(100.0, 90.0) == pytest.approx(-10.0)


# ── 비교 엔진 ─────────────────────────────────────────────────────


def test_compare_computes_abs_delta_against_baseline():
    # Arrange
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)
    looser = BASELINE.with_changes(min_separation_m=10.0)

    # Act
    comparison = analyzer.compare([looser])

    # Assert: 이격 10m → 충돌 20-20=0, 기준(5m)은 20-10=10 → 델타 -10
    delta = comparison.deltas[0]
    assert delta.abs_delta["collisions"] == pytest.approx(-10.0)
    assert delta.improved("collisions")  # 충돌 감소는 개선
    assert delta.improved("conflict_resolution_rate")  # 해결률 상승은 개선
    assert not delta.improved("throughput")  # 처리량 감소는 악화


def test_sweep_preserves_input_order_for_monotone_trend():
    # Arrange
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)

    # Act
    comparison = analyzer.sweep("min_separation_m", [5.0, 10.0, 15.0])

    # Assert: 입력 순서 보존 + 충돌 단조 감소
    seps = [d.policy.min_separation_m for d in comparison.deltas]
    collisions = [d.kpis.collisions for d in comparison.deltas]
    assert seps == [5.0, 10.0, 15.0]
    assert collisions == sorted(collisions, reverse=True)


def test_ranked_by_orders_by_improvement_direction():
    # Arrange
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)
    comparison = analyzer.sweep("min_separation_m", [6.0, 12.0, 9.0])

    # Act: 충돌은 작을수록 좋음 → 이격 큰 정책이 1위
    ranked = comparison.ranked_by("collisions")

    # Assert
    assert ranked[0].policy.min_separation_m == 12.0
    assert ranked[-1].policy.min_separation_m == 6.0


def test_best_by_throughput_prefers_tightest_separation():
    # Arrange: 처리량은 클수록 좋고 토이 모델에서 이격 작을수록 처리량↑
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)
    comparison = analyzer.sweep("min_separation_m", [6.0, 12.0, 9.0])

    # Act
    best = comparison.best_by("throughput")

    # Assert
    assert best is not None
    assert best.policy.min_separation_m == 6.0


def test_sweep_rejects_unknown_param():
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)
    with pytest.raises(ValueError):
        analyzer.sweep("nonexistent", [1.0, 2.0])


def test_engine_is_deterministic_across_runs():
    # Arrange
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)

    # Act
    first = analyzer.sweep("min_separation_m", [6.0, 9.0, 12.0])
    second = analyzer.sweep("min_separation_m", [6.0, 9.0, 12.0])

    # Assert: 동일 입력 → 동일 절대 델타
    assert [d.abs_delta for d in first.deltas] == [d.abs_delta for d in second.deltas]


def test_delta_mappings_are_immutable():
    # Arrange
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)
    comparison = analyzer.compare([BASELINE.with_changes(min_separation_m=10.0)])

    # Act / Assert: frozen dataclass 의 매핑 내용도 변조 불가
    with pytest.raises(TypeError):
        comparison.deltas[0].abs_delta["collisions"] = 0.0


def test_markdown_renders_undefined_pct_as_new_for_zero_baseline():
    # Arrange: 기준 충돌 0 → 변형에서 충돌 발생 시 백분율 정의 불가
    def zero_collision_baseline(policy: RegulatoryPolicy) -> PolicyKPIs:
        collisions = 0.0 if policy.min_separation_m >= 5.0 else 8.0
        return PolicyKPIs(
            conflict_resolution_rate=0.9,
            collisions=collisions,
            throughput=50.0,
            mean_completion_time_s=60.0,
        )

    analyzer = PolicyImpactAnalyzer(BASELINE, zero_collision_baseline)

    # Act
    report = analyzer.compare([BASELINE.with_changes(min_separation_m=3.0)]).to_markdown(
        objective="collisions"
    )

    # Assert: "+inf%" 대신 명시적 "(신규)" 로 렌더링
    assert "신규" in report
    assert "inf" not in report.lower()


def test_to_markdown_contains_baseline_and_best_policy():
    # Arrange
    analyzer = PolicyImpactAnalyzer(BASELINE, toy_evaluate)
    comparison = analyzer.sweep("min_separation_m", [10.0, 15.0])

    # Act
    report = analyzer.compare(
        [BASELINE.with_changes(min_separation_m=10.0)]
    ).to_markdown(objective="collisions")

    # Assert
    assert "정책 영향 비교" in report
    assert "collisions 최적 정책" in report
    assert "기준" in report
    # 스윕 리포트도 정상 생성
    assert comparison.to_markdown().startswith("# 정책 영향 비교")
