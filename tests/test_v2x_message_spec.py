"""GENESIS Phase 364 — V2X 메시지 와이어 스펙 단위 테스트.

외부 의존성 0(순수 결정적). 드론↔드론 BSM 유사 메시지의 정규 와이어 포맷이 갖춰야 할
불변식을 고정한다:
  (1) 왕복 항등 — ``decode(encode(m)) == m``.
  (2) 양자화 오차 유계 — `|복원값 - 원본| <= 0.5*해상도`.
  (3) 인코딩 결정성 — 반복 인코딩은 바이트 동일.
  (4) 고정 길이 프레임 + CRC 가 단일 비트 변조 검출.
  (5) 정규 dict 키 순서 고정.
  (6) 범위 초과 필드 → ValueError fail-fast.
  (7) magic/version 불일치 디코딩 거부.
"""

from __future__ import annotations

import struct

import pytest

from simulation.v2x_message_spec import (
    FRAME_SIZE,
    HEADING_RES_DEG,
    MAGIC,
    POSITION_RES_M,
    PROTOCOL_VERSION,
    VELOCITY_RES_MS,
    BsmMessage,
    decode,
    from_v2x_message,
)

# --- 픽스처 -----------------------------------------------------------------


def _sample() -> BsmMessage:
    return BsmMessage(
        station_id=4242,
        sequence=17,
        timestamp_ms=123_456,
        x_m=152.37,
        y_m=-88.04,
        z_m=42.5,
        vx_ms=12.34,
        vy_ms=-3.5,
        vz_ms=0.8,
        heading_deg=271.25,
        msg_type="basic_safety_message",
    )


# --- (1) 왕복 항등 ----------------------------------------------------------


def test_round_trip_identity_on_quantized_grid():
    # 해상도 격자에 정확히 정렬된 값은 손실 없이 왕복한다.
    msg = BsmMessage(
        station_id=1, sequence=2, timestamp_ms=1000,
        x_m=10.00, y_m=-20.00, z_m=5.00,
        vx_ms=1.00, vy_ms=-2.00, vz_ms=0.50,
        heading_deg=90.0,
    )
    assert decode(msg.encode()) == msg


def test_round_trip_is_idempotent_after_first_decode():
    # 한 번 디코딩된(양자화 정렬된) 메시지는 이후 무손실 왕복한다.
    once = decode(_sample().encode())
    assert decode(once.encode()) == once


# --- (2) 양자화 오차 유계 ---------------------------------------------------


def test_quantization_error_bounded_by_half_resolution():
    msg = _sample()
    out = decode(msg.encode())
    assert abs(out.x_m - msg.x_m) <= 0.5 * POSITION_RES_M
    assert abs(out.y_m - msg.y_m) <= 0.5 * POSITION_RES_M
    assert abs(out.z_m - msg.z_m) <= 0.5 * POSITION_RES_M
    assert abs(out.vx_ms - msg.vx_ms) <= 0.5 * VELOCITY_RES_MS
    assert abs(out.vy_ms - msg.vy_ms) <= 0.5 * VELOCITY_RES_MS
    assert abs(out.vz_ms - msg.vz_ms) <= 0.5 * VELOCITY_RES_MS
    assert abs(out.heading_deg - msg.heading_deg) <= 0.5 * HEADING_RES_DEG


# --- (3) 인코딩 결정성 ------------------------------------------------------


def test_encoding_is_deterministic():
    msg = _sample()
    assert msg.encode() == msg.encode()
    # 동일 값으로 따로 생성해도 바이트 동일
    assert msg.encode() == _sample().encode()


def test_frame_has_fixed_size():
    assert len(_sample().encode()) == FRAME_SIZE
    assert FRAME_SIZE == 36  # 본문 32 + CRC 4 (스펙 고정값)


# --- (4) CRC 무결성 ---------------------------------------------------------


def test_crc_detects_single_bit_tamper():
    frame = bytearray(_sample().encode())
    frame[5] ^= 0x01  # 본문 한 바이트의 한 비트 뒤집기
    with pytest.raises(ValueError, match="CRC"):
        decode(bytes(frame))


def test_crc_trailer_tamper_also_rejected():
    frame = bytearray(_sample().encode())
    frame[-1] ^= 0x01  # CRC 트레일러 변조
    with pytest.raises(ValueError, match="CRC"):
        decode(bytes(frame))


def test_wrong_frame_length_rejected():
    with pytest.raises(ValueError, match="프레임 길이"):
        decode(_sample().encode()[:-1])


# --- (5) 정규 dict 키 순서 고정 --------------------------------------------


def test_canonical_dict_key_order_is_fixed():
    d = _sample().to_canonical_dict()
    assert list(d.keys()) == [
        "protocol_version", "msg_type", "station_id", "sequence",
        "timestamp_ms", "x_m", "y_m", "z_m", "vx_ms", "vy_ms", "vz_ms",
        "heading_deg",
    ]
    assert d["protocol_version"] == PROTOCOL_VERSION


def test_canonical_dict_reflects_quantized_values():
    # dict 값은 복원(양자화) 후 값이라 encode→decode 결과와 정합.
    d = _sample().to_canonical_dict()
    out = decode(_sample().encode())
    assert d["x_m"] == pytest.approx(out.x_m)
    assert d["heading_deg"] == pytest.approx(out.heading_deg)


# --- (6) 범위·유효성 검증 ---------------------------------------------------


@pytest.mark.parametrize("field,value", [
    ("station_id", -1),
    ("station_id", 65536),
    ("sequence", 70000),
    ("timestamp_ms", -1),
])
def test_identifier_range_validation(field, value):
    kwargs = dict(station_id=1, sequence=1, timestamp_ms=0, x_m=0, y_m=0, z_m=0)
    kwargs[field] = value
    with pytest.raises(ValueError):
        BsmMessage(**kwargs)


def test_position_out_of_wire_range_rejected():
    with pytest.raises(ValueError, match="x_m"):
        BsmMessage(station_id=1, sequence=1, timestamp_ms=0,
                   x_m=1e9, y_m=0, z_m=0)  # 1e9 m → 양자화 시 int32 초과


def test_velocity_out_of_wire_range_rejected():
    with pytest.raises(ValueError, match="vx_ms"):
        BsmMessage(station_id=1, sequence=1, timestamp_ms=0,
                   x_m=0, y_m=0, z_m=0, vx_ms=10_000.0)  # int16 초과


def test_unknown_msg_type_rejected():
    with pytest.raises(ValueError, match="msg_type"):
        BsmMessage(station_id=1, sequence=1, timestamp_ms=0,
                   x_m=0, y_m=0, z_m=0, msg_type="not_a_type")


def test_float_timestamp_rejected():
    # int 로 표기됐지만 float 가 들어오면 struct 전에 fail-fast.
    with pytest.raises(ValueError, match="timestamp_ms"):
        BsmMessage(station_id=1, sequence=1, timestamp_ms=12.5,
                   x_m=0, y_m=0, z_m=0)


# --- 기수 정규화 ------------------------------------------------------------


def test_heading_normalized_to_unit_circle():
    m = BsmMessage(station_id=1, sequence=1, timestamp_ms=0,
                   x_m=0, y_m=0, z_m=0, heading_deg=361.25)
    assert m.heading_deg == pytest.approx(1.25)
    neg = BsmMessage(station_id=1, sequence=1, timestamp_ms=0,
                     x_m=0, y_m=0, z_m=0, heading_deg=-90.0)
    assert neg.heading_deg == pytest.approx(270.0)


# --- (7) magic/version 불일치 거부 -----------------------------------------


def test_bad_magic_rejected():
    # 잘못된 magic 으로 본문을 재구성 + 유효 CRC 부여 → magic 검증에서 거부.
    import zlib
    from simulation.v2x_message_spec import _BODY_FMT, _CRC_FMT
    body = struct.pack(_BODY_FMT, 0x0000, PROTOCOL_VERSION, 0, 1, 1, 0,
                       0, 0, 0, 0, 0, 0, 0)
    frame = body + struct.pack(_CRC_FMT, zlib.crc32(body) & 0xFFFFFFFF)
    with pytest.raises(ValueError, match="magic"):
        decode(frame)


def test_unsupported_version_rejected():
    import zlib
    from simulation.v2x_message_spec import _BODY_FMT, _CRC_FMT
    body = struct.pack(_BODY_FMT, MAGIC, 99, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0)
    frame = body + struct.pack(_CRC_FMT, zlib.crc32(body) & 0xFFFFFFFF)
    with pytest.raises(ValueError, match="version"):
        decode(frame)


# --- v2x_communication.V2XMessage 어댑터 -----------------------------------


def test_adapter_from_v2x_message_preserves_position():
    np = pytest.importorskip("numpy")
    from simulation.v2x_communication import MessageType, V2XMessage, V2XMode

    v = V2XMessage(
        msg_id="BSM-000001",
        sender="drone-7",
        msg_type=MessageType.BSM,
        mode=V2XMode.V2V,
        position=np.array([100.5, -50.25, 30.0]),
        velocity=np.array([5.0, -2.0, 0.0]),
        timestamp=12.5,
    )
    bsm = from_v2x_message(v, station_id=7, sequence=1)
    out = decode(bsm.encode())
    assert out.station_id == 7
    assert out.timestamp_ms == 12_500
    assert out.msg_type == "basic_safety_message"
    assert abs(out.x_m - 100.5) <= 0.5 * POSITION_RES_M
    assert abs(out.y_m + 50.25) <= 0.5 * POSITION_RES_M
    assert abs(out.vx_ms - 5.0) <= 0.5 * VELOCITY_RES_MS


def test_adapter_maps_non_bsm_type():
    np = pytest.importorskip("numpy")
    from simulation.v2x_communication import MessageType, V2XMessage, V2XMode

    v = V2XMessage(
        msg_id="HB-000001",
        sender="drone-3",
        msg_type=MessageType.HEARTBEAT,
        mode=V2XMode.V2V,
        position=np.zeros(3),
        velocity=np.zeros(3),
        timestamp=1.0,
    )
    bsm = from_v2x_message(v, station_id=3, sequence=1)
    assert bsm.msg_type == "heartbeat"
    assert decode(bsm.encode()).msg_type == "heartbeat"
