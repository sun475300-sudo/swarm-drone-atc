"""ODYSSEY Phase 448 — 속성 기반 테스트 (Hypothesis).

TelemetryCompressor (Phase 642)의 무손실/유계 손실 속성을 무작위 입력
1,000+ 케이스로 검증한다. 예제 기반 테스트가 못 잡는 경계 조건을 노린다.

속성:
  P1. 프레임 수 보존 — decompress(compress(frames)) 길이 동일
  P2. status RLE 완전 무손실 — 시퀀스 정확 복원
  P3. 첫 프레임 위치 정확 보존 (base frame)
  P4. 위치 누적 오차 유계 — 스텝당 양자화 오차 ≤ q/2 → n스텝 ≤ n·q/2
  P5. drone_id 보존
"""
from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from simulation.telemetry_compression import TelemetryCompressor, TelemetryFrame

# H-01 fix (2026-06-19): Hypothesis 1,000+ 케이스 = 수십 초 소요. CI fast 레인 제외.
pytestmark = pytest.mark.slow

QUANT_MM = 10.0
QUANT_M = QUANT_MM / 1000.0

finite_coord = st.floats(min_value=-5000.0, max_value=5000.0,
                         allow_nan=False, allow_infinity=False, width=32)


@st.composite
def frame_lists(draw):
    n = draw(st.integers(min_value=1, max_value=60))
    frames = []
    for i in range(n):
        pos = np.array([draw(finite_coord) for _ in range(3)], dtype=float)
        vel = np.array([draw(finite_coord) for _ in range(3)], dtype=float)
        frames.append(TelemetryFrame(
            drone_id="D-PBT",
            timestamp=float(i) * 0.1,
            position=pos,
            velocity=vel,
            battery=draw(st.floats(min_value=0.0, max_value=100.0,
                                   allow_nan=False)),
            status=draw(st.integers(min_value=0, max_value=2)),
        ))
    return frames


@settings(max_examples=250, deadline=None)
@given(frames=frame_lists())
def test_p1_frame_count_preserved(frames):
    comp = TelemetryCompressor(quantization_mm=QUANT_MM)
    restored = comp.decompress(comp.compress(frames))
    assert len(restored) == len(frames)


@settings(max_examples=250, deadline=None)
@given(frames=frame_lists())
def test_p2_status_rle_lossless(frames):
    comp = TelemetryCompressor(quantization_mm=QUANT_MM)
    restored = comp.decompress(comp.compress(frames))
    assert [f.status for f in restored] == [f.status for f in frames]


@settings(max_examples=250, deadline=None)
@given(frames=frame_lists())
def test_p3_base_frame_position_exact(frames):
    comp = TelemetryCompressor(quantization_mm=QUANT_MM)
    restored = comp.decompress(comp.compress(frames))
    np.testing.assert_array_equal(restored[0].position, frames[0].position)
    assert restored[0].drone_id == frames[0].drone_id


@settings(max_examples=250, deadline=None)
@given(frames=frame_lists())
def test_p4_position_error_bounded_by_quantization(frames):
    comp = TelemetryCompressor(quantization_mm=QUANT_MM)
    restored = comp.decompress(comp.compress(frames))
    # i번째 프레임 누적 오차 ≤ i × (q/2 + float 여유)
    for i, (orig, rest) in enumerate(zip(frames, restored)):
        bound = i * (QUANT_M / 2 + 1e-6) + 1e-9
        err = np.max(np.abs(rest.position - orig.position))
        assert err <= bound, f"frame {i}: err={err} > bound={bound}"


@settings(max_examples=100, deadline=None)
@given(frames=frame_lists(), drone_id=st.text(min_size=1, max_size=16))
def test_p5_drone_id_preserved(frames, drone_id):
    for f in frames:
        f.drone_id = drone_id
    comp = TelemetryCompressor(quantization_mm=QUANT_MM)
    stream = comp.compress(frames)
    assert stream.drone_id == drone_id
    assert all(f.drone_id == drone_id for f in comp.decompress(stream))


@settings(max_examples=50, deadline=None)
@given(collisions=st.integers(min_value=0, max_value=10_000),
       conflicts=st.integers(min_value=0, max_value=10_000))
def test_collision_resolution_rate_invariants(collisions, conflicts):
    """충돌 해결률 공식 1 - collisions/(conflicts+collisions) 불변식 (README 공시 공식)."""
    total = conflicts + collisions
    rate = 1.0 if total == 0 else 1 - collisions / total
    assert 0.0 <= rate <= 1.0
    if collisions == 0:
        assert rate == 1.0
    if conflicts == 0 and collisions > 0:
        assert rate == 0.0
