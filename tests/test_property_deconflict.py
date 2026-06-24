"""ODYSSEY Phase 448 — 속성 기반 테스트 (Hypothesis): 시뮬 코어 불변식.

4D 경로 탈충돌 코어(`simulation/path_deconflict.py` — `PathDeconflict`)의
충돌 감지·보간 불변식을 무작위 입력으로 검증한다. 예제 기반 테스트
(`tests/test_phase60_67.py::TestPathDeconflict`)가 못 잡는 경계 조건을 노린다.

기존 property 자산(`test_apf_property.py` = APF 힘장, `test_property_telemetry.py`
= 텔레메트리 압축)이 다루지 않던 **충돌 감지 코어**를 덮어 Phase 448의
"시뮬 코어 불변식" 목표를 채운다. 본 파일 단독으로 1,000+ 케이스를 실행한다.

검증 불변식:
  P1. 결정성        — find_conflicts() 반복 호출 결과 동일 (무작위성 0).
  P2. 순서 무관      — 경로 삽입 순서와 무관하게 충돌 개수 동일.
  P3. 보간 볼록성    — interpolate_position 좌표는 항상 웨이포인트 경계상자 안.
  P4. 보간 클램프    — t ≤ 첫 시각 → 첫 점, t ≥ 끝 시각 → 끝 점.
  P5. 충돌 술어 일관 — 보고된 모든 충돌은 h<sep_h ∧ v<sep_v, 거리 유한·비음수.
  P6. 시각 정렬      — find_conflicts 는 충돌 시각 t 오름차순.
  P7. 수직 분리 보장 — 고도차 ≥ sep_v 인 평행 경로 쌍은 충돌 0.
  P8. 단일 경로      — 경로 1개면 충돌 0.
  P9. 동일 경로 충돌 — 겹치는 동일 경로 쌍(양의 분리)은 충돌 ≥ 1.
"""
from __future__ import annotations

import math

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from simulation.path_deconflict import PathDeconflict, Waypoint4D

# 공역 ±2km, 고도 0~150m, 시간창 0~120s (스캔 루프 유계 유지)
_x = st.floats(min_value=-2000.0, max_value=2000.0, allow_nan=False, allow_infinity=False)
_z = st.floats(min_value=0.0, max_value=150.0, allow_nan=False, allow_infinity=False)
_t = st.floats(min_value=0.0, max_value=120.0, allow_nan=False, allow_infinity=False)


@st.composite
def _waypoints(draw, min_pts: int = 1, max_pts: int = 6):
    """단조 증가 시각의 4D 웨이포인트 리스트."""
    n = draw(st.integers(min_value=min_pts, max_value=max_pts))
    ts = sorted(draw(st.lists(_t, min_size=n, max_size=n, unique=True)))
    return [
        Waypoint4D(x=draw(_x), y=draw(_x), z=draw(_z), t=ts[k])
        for k in range(n)
    ]


_SETTINGS = settings(
    max_examples=130,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


# ── P1. 결정성 ──────────────────────────────────────────────
@_SETTINGS
@given(wa=_waypoints(min_pts=2), wb=_waypoints(min_pts=2))
def test_find_conflicts_is_deterministic(wa, wb):
    dc = PathDeconflict()
    dc.add_path("a", wa)
    dc.add_path("b", wb)
    first = dc.find_conflicts()
    second = dc.find_conflicts()
    assert len(first) == len(second)
    assert [c.t for c in first] == [c.t for c in second]
    assert [round(c.distance, 9) for c in first] == [round(c.distance, 9) for c in second]


# ── P2. 삽입 순서 무관 ──────────────────────────────────────
@_SETTINGS
@given(wa=_waypoints(min_pts=2), wb=_waypoints(min_pts=2))
def test_conflict_count_independent_of_insertion_order(wa, wb):
    dc1 = PathDeconflict()
    dc1.add_path("a", wa)
    dc1.add_path("b", wb)

    dc2 = PathDeconflict()
    dc2.add_path("b", wb)
    dc2.add_path("a", wa)

    assert len(dc1.find_conflicts()) == len(dc2.find_conflicts())


# ── P3. 보간 볼록성 (경계상자) ──────────────────────────────
@_SETTINGS
@given(wp=_waypoints(min_pts=1), t=_t)
def test_interpolation_within_bounding_box(wp, t):
    dc = PathDeconflict()
    dc.add_path("a", wp)
    pos = dc.interpolate_position("a", t)
    assert pos is not None, f"interpolate_position returned None for t={t}"
    eps = 1e-6
    xs = [w.x for w in wp]
    ys = [w.y for w in wp]
    zs = [w.z for w in wp]
    assert min(xs) - eps <= pos[0] <= max(xs) + eps
    assert min(ys) - eps <= pos[1] <= max(ys) + eps
    assert min(zs) - eps <= pos[2] <= max(zs) + eps
    assert all(math.isfinite(v) for v in pos)


# ── P4. 보간 클램프 (경계 외삽 금지) ────────────────────────
@_SETTINGS
@given(wp=_waypoints(min_pts=2))
def test_interpolation_clamps_outside_time_range(wp):
    dc = PathDeconflict()
    dc.add_path("a", wp)
    first, last = wp[0], wp[-1]
    before = dc.interpolate_position("a", first.t - 10.0)
    after = dc.interpolate_position("a", last.t + 10.0)
    assert before == (first.x, first.y, first.z)
    assert after == (last.x, last.y, last.z)


# ── P5. 충돌 술어 일관성 ────────────────────────────────────
@_SETTINGS
@given(wa=_waypoints(min_pts=2), wb=_waypoints(min_pts=2))
def test_reported_conflicts_satisfy_separation_predicate(wa, wb):
    dc = PathDeconflict(separation_h=30.0, separation_v=10.0)
    dc.add_path("a", wa)
    dc.add_path("b", wb)
    for c in dc.find_conflicts():
        pa, pb = c.pos_a, c.pos_b
        h = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        v = abs(pa[2] - pb[2])
        assert h < dc.separation_h
        assert v < dc.separation_v
        assert math.isfinite(c.distance)
        assert c.distance >= 0.0


# ── P6. 충돌 시각 오름차순 ──────────────────────────────────
@_SETTINGS
@given(wa=_waypoints(min_pts=2), wb=_waypoints(min_pts=2))
def test_conflicts_sorted_by_time(wa, wb):
    dc = PathDeconflict()
    dc.add_path("a", wa)
    dc.add_path("b", wb)
    times = [c.t for c in dc.find_conflicts()]
    assert times == sorted(times)


# ── P7. 수직 분리 보장 ──────────────────────────────────────
@_SETTINGS
@given(
    z1=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    gap=st.floats(min_value=12.0, max_value=90.0, allow_nan=False, allow_infinity=False),
    x0=_x,
    x1=_x,
)
def test_vertical_separation_guarantees_no_conflict(z1, gap, x0, x1):
    sep_v = 10.0
    # gap 은 sep_v 보다 충분히 큼 — 부동소수점 경계 아티팩트(z2-z1 이 sep_v 를
    # 미세하게 밑도는 경우)를 피하면서 "명확히 분리된 평행 경로" 불변식을 검증.
    z2 = z1 + gap
    dc = PathDeconflict(separation_h=30.0, separation_v=sep_v)
    dc.add_path("a", [Waypoint4D(x0, 0.0, z1, 0.0), Waypoint4D(x1, 0.0, z1, 30.0)])
    dc.add_path("b", [Waypoint4D(x0, 0.0, z2, 0.0), Waypoint4D(x1, 0.0, z2, 30.0)])
    assert dc.find_conflicts() == []


# ── P8. 단일 경로는 충돌 없음 ───────────────────────────────
@_SETTINGS
@given(wp=_waypoints(min_pts=1))
def test_single_path_has_no_conflicts(wp):
    dc = PathDeconflict()
    dc.add_path("solo", wp)
    assert dc.find_conflicts() == []


# ── P9. 동일 경로 쌍은 반드시 충돌 ──────────────────────────
@_SETTINGS
@given(wp=_waypoints(min_pts=2))
def test_identical_paths_always_conflict(wp):
    dc = PathDeconflict(separation_h=30.0, separation_v=10.0)
    dc.add_path("a", list(wp))
    dc.add_path("b", list(wp))
    assert len(dc.find_conflicts()) >= 1
