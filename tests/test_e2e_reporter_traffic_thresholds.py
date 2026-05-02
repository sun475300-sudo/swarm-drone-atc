"""e2e_reporter traffic state 임계 회귀 테스트.

`docs/OPS_TRAFFIC_RED_ANALYSIS_2026-05-03.md` 분석 결과 ops_report seed42 의
traffic RED 는 의도된 동작. 임계 자체는 합리적이라 변경하지 않음.

이 테스트는 임계가 무심코 바뀌면 즉시 잡히도록 경계 6건 + ops_report 의도
재현 1건 + health penalty 캡 가드 1건을 락한다.

기존 임계 (simulation/e2e_reporter.py:_section_diagnostics):
- congestion <  0.5  → GREEN
- 0.5 ≤   < 0.8     → YELLOW
- congestion ≥ 0.8  → RED
"""
from __future__ import annotations

import pytest

from simulation.e2e_reporter import E2EReporter


def _diagnostics_for(congestion: float) -> dict:
    """헬퍼: traffic.avg_congestion 만 변화시켜 _section_diagnostics 결과."""
    pseudo_report = {
        "scenario": {},
        "delivery": {"dispatches": 1, "delivered": 1},
        "compliance": {"total_violations": 0},
        "recorder": {"events": 5},
        "performance": {"success_rate": 1.0},
        "traffic": {"avg_congestion": congestion},
    }
    return E2EReporter._section_diagnostics(pseudo_report)


@pytest.mark.parametrize(
    "congestion,expected",
    [
        (0.0, "GREEN"),
        (0.49, "GREEN"),
        (0.5, "YELLOW"),
        (0.79, "YELLOW"),
        (0.8, "RED"),
        (1.0, "RED"),
    ],
)
def test_traffic_state_threshold_boundaries(congestion: float, expected: str):
    """임계 0.5 / 0.8 경계가 정확히 일관성 있게 분기되어야 한다."""
    diag = _diagnostics_for(congestion)
    state = diag["sections"]["traffic"]["state"]
    assert state == expected, (
        f"congestion={congestion} → expected={expected}, got={state}"
    )


def test_ops_report_full_saturation_red_intent():
    """ops_report 시나리오의 100% 포화 = RED 가 의도된 동작 — 회귀 아님 가드."""
    diag = _diagnostics_for(1.0)
    assert diag["sections"]["traffic"]["state"] == "RED"
    # blockers 에 traffic 만 들어있어야 (다른 섹션은 정상)
    assert "traffic" in diag["blockers"]


def test_health_score_penalty_capped_at_12pct():
    """traffic_penalty = min(0.12, congestion * 0.12) — 최대 12% 만 감점.

    build() 의 health_score 계산이 의도된 캡(0.12)을 유지하는지 가드.
    """
    reporter = E2EReporter()
    base_kwargs = dict(
        delivery_summary={"delivered": 2, "dispatches": 2},
        compliance_report={"total_violations": 0},
        recorder_summary={"events": 10},
        perf_report={"success_rate": 1.0},
    )
    high = reporter.build(traffic_summary={"avg_congestion": 1.0}, **base_kwargs)
    low = reporter.build(traffic_summary={"avg_congestion": 0.0}, **base_kwargs)
    diff = float(low["kpi"]["health_score"]) - float(high["kpi"]["health_score"])
    assert diff <= 0.12 + 1e-6, f"penalty exceeded cap: diff={diff}"
    assert diff >= 0.10, f"penalty too small: diff={diff}"
