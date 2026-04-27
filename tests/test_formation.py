"""FormationController 회귀 테스트.

영상 참조 (youtube.com/shorts/UJP5GbvlpZs, "자율 군집 비행 — 사전 경로 없음")의
컨셉을 SDACS 기존 FormationController에 맵핑한 DIAMOND 패턴 추가에 대한 가드.

검증 대상:
- 5개 패턴 모두 정상 import / instantiate
- compute_offsets(n) 가 n 개 벡터 반환
- DIAMOND 의 ring/slot 산출이 정확 (4방향 외곽 확장)
- follower_targets 회전 정합성
- change_pattern 동적 전환
- should_break_formation 위협 거리 분기
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from simulation.formation import FormationController, FormationPattern


def test_all_patterns_instantiate():
    for p in ("V_SHAPE", "LINE", "CIRCLE", "GRID", "DIAMOND"):
        fc = FormationController(pattern=p, spacing=80.0)
        assert fc.pattern == FormationPattern(p)


def test_diamond_pattern_in_enum():
    assert FormationPattern.DIAMOND.value == "DIAMOND"
    assert "DIAMOND" in [p.value for p in FormationPattern]


@pytest.mark.parametrize(
    "pattern", ["V_SHAPE", "LINE", "CIRCLE", "GRID", "DIAMOND"]
)
@pytest.mark.parametrize("n", [1, 2, 4, 8])
def test_compute_offsets_count_matches(pattern: str, n: int):
    fc = FormationController(pattern=pattern, spacing=50.0)
    offsets = fc.compute_offsets(n)
    assert len(offsets) == n
    for off in offsets:
        assert isinstance(off, np.ndarray)
        assert off.shape == (3,)


def test_diamond_first_ring_four_directions():
    """DIAMOND 첫 ring (followers 1..4) 가 전·후·좌·우 4방향에 정확히 spacing 거리."""
    s = 100.0
    fc = FormationController(pattern="DIAMOND", spacing=s)
    offsets = fc.compute_offsets(4)

    # 4 slots: front (+x), back (-x), left (+y), right (-y)
    expected = [
        np.array([s, 0.0, 0.0]),
        np.array([-s, 0.0, 0.0]),
        np.array([0.0, s, 0.0]),
        np.array([0.0, -s, 0.0]),
    ]
    for got, exp in zip(offsets, expected):
        assert np.allclose(got, exp), f"got={got} exp={exp}"


def test_diamond_second_ring_doubles_distance():
    """DIAMOND 두 번째 ring (followers 5..8) 은 spacing*2 거리."""
    s = 50.0
    fc = FormationController(pattern="DIAMOND", spacing=s)
    offsets = fc.compute_offsets(8)

    # Last 4 entries belong to ring=2
    ring2 = offsets[4:]
    expected = [
        np.array([2 * s, 0.0, 0.0]),
        np.array([-2 * s, 0.0, 0.0]),
        np.array([0.0, 2 * s, 0.0]),
        np.array([0.0, -2 * s, 0.0]),
    ]
    for got, exp in zip(ring2, expected):
        assert np.allclose(got, exp)


def test_diamond_altitude_stacks_per_ring():
    """altitude_offset 이 ring index 에 비례해 누적."""
    fc = FormationController(pattern="DIAMOND", spacing=80.0, altitude_offset=-5.0)
    offsets = fc.compute_offsets(8)

    # First ring z = -5.0 * 1, second ring z = -5.0 * 2
    for off in offsets[:4]:
        assert off[2] == pytest.approx(-5.0)
    for off in offsets[4:]:
        assert off[2] == pytest.approx(-10.0)


def test_follower_targets_rotation_matches_heading():
    """리더가 동쪽(heading=0)을 향할 때 follower 가 leader 좌표에 offset 그대로 더해진다."""
    fc = FormationController(pattern="LINE", spacing=10.0)
    leader = np.array([100.0, 50.0, 30.0])
    targets = fc.follower_targets(leader, leader_heading_rad=0.0, n_followers=2)

    # LINE: 첫 follower는 -10*x, 두 번째는 -20*x
    assert np.allclose(targets[0], np.array([90.0, 50.0, 30.0]))
    assert np.allclose(targets[1], np.array([80.0, 50.0, 30.0]))


def test_follower_targets_rotation_north():
    """리더가 북쪽(heading=pi/2) 을 향할 때 LINE offset이 +y 축 회전."""
    fc = FormationController(pattern="LINE", spacing=10.0)
    leader = np.array([0.0, 0.0, 0.0])
    targets = fc.follower_targets(leader, leader_heading_rad=math.pi / 2, n_followers=1)

    # LINE 의 첫 follower offset 은 (-10, 0, 0). pi/2 회전 후 (0, -10, 0).
    assert np.allclose(targets[0], np.array([0.0, -10.0, 0.0]), atol=1e-9)


def test_change_pattern_dynamic():
    fc = FormationController(pattern="V_SHAPE", spacing=60.0)
    assert fc.pattern == FormationPattern.V_SHAPE
    fc.change_pattern("DIAMOND")
    assert fc.pattern == FormationPattern.DIAMOND
    # offsets 도 새 패턴 기준으로 반영
    offsets = fc.compute_offsets(4)
    assert np.allclose(offsets[0], np.array([60.0, 0.0, 0.0]))


def test_should_break_formation_threat_close():
    fc = FormationController(pattern="V_SHAPE", spacing=80.0)
    follower = np.array([0.0, 0.0, 50.0])
    obstacle_close = np.array([20.0, 0.0, 50.0])
    obstacle_far = np.array([200.0, 0.0, 50.0])

    assert fc.should_break_formation(follower, np.zeros(3), threat_distance=50.0,
                                     obstacles=[obstacle_close]) is True
    assert fc.should_break_formation(follower, np.zeros(3), threat_distance=50.0,
                                     obstacles=[obstacle_far]) is False
    assert fc.should_break_formation(follower, np.zeros(3), threat_distance=50.0,
                                     obstacles=None) is False


def test_compute_offsets_zero_followers():
    for p in ("V_SHAPE", "LINE", "CIRCLE", "GRID", "DIAMOND"):
        fc = FormationController(pattern=p, spacing=80.0)
        assert fc.compute_offsets(0) == []
