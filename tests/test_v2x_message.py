"""GENESIS Phase 364 — V2X 메시지 규격 테스트.

DroneBasicSafetyMessage, EmergencyAlert, V2XCodec, V2XChannel 에 대한
검증·라운드트립·채널 시뮬레이션 테스트 (18+ 항목).
"""
from __future__ import annotations

import pytest

from simulation.v2x_message import (
    BSM,
    EVA,
    DroneBasicSafetyMessage,
    EmergencyAlert,
    V2XChannel,
    V2XChannelStats,
    V2XCodec,
    example_bsm,
    example_eva,
)


# ── 픽스처 ───────────────────────────────────────────────────────────────


def _make_bsm(**overrides) -> DroneBasicSafetyMessage:
    """기본 BSM 을 생성하고 overrides 로 필드를 덮어쓴다."""
    defaults = {
        "msg_id": "test-bsm-001",
        "msg_type": BSM,
        "timestamp_s": 1.0,
        "drone_id": "D-001",
        "position": (10.0, 20.0, 30.0),
        "velocity": (1.0, 0.0, 0.0),
        "heading_deg": 90.0,
        "altitude_m": 30.0,
        "speed_ms": 1.0,
        "intent": "cruise",
        "battery_pct": 85.0,
        "accuracy_m": 2.0,
        "ttl_hops": 1,
    }
    defaults.update(overrides)
    return DroneBasicSafetyMessage(**defaults)


def _make_eva(**overrides) -> EmergencyAlert:
    """기본 EVA 를 생성하고 overrides 로 필드를 덮어쓴다."""
    defaults = {
        "msg_id": "test-eva-001",
        "msg_type": EVA,
        "timestamp_s": 2.0,
        "drone_id": "D-002",
        "position": (50.0, 60.0, 40.0),
        "emergency_type": "low_battery",
        "severity": "warning",
        "recommended_action": "avoid_area",
        "affected_radius_m": 100.0,
    }
    defaults.update(overrides)
    return EmergencyAlert(**defaults)


# ── 1. BSM 생성 및 검증 ─────────────────────────────────────────────────


class TestDroneBasicSafetyMessage:
    """DroneBasicSafetyMessage 생성·검증 테스트."""

    def test_bsm_creation(self):
        """유효한 BSM 이 정상 생성된다."""
        bsm = _make_bsm()
        assert bsm.msg_id == "test-bsm-001"
        assert bsm.msg_type == BSM
        assert bsm.position == (10.0, 20.0, 30.0)
        assert bsm.intent == "cruise"

    def test_invalid_heading_rejected(self):
        """heading_deg 범위 이탈 시 ValueError."""
        with pytest.raises(ValueError, match="heading_deg"):
            _make_bsm(heading_deg=-1.0)
        with pytest.raises(ValueError, match="heading_deg"):
            _make_bsm(heading_deg=361.0)

    def test_invalid_battery_rejected(self):
        """battery_pct 범위 이탈 시 ValueError."""
        with pytest.raises(ValueError, match="battery_pct"):
            _make_bsm(battery_pct=-1.0)
        with pytest.raises(ValueError, match="battery_pct"):
            _make_bsm(battery_pct=101.0)

    def test_invalid_ttl_rejected(self):
        """ttl_hops < 1 이면 ValueError."""
        with pytest.raises(ValueError, match="ttl_hops"):
            _make_bsm(ttl_hops=0)

    def test_invalid_speed_rejected(self):
        """speed_ms < 0 이면 ValueError."""
        with pytest.raises(ValueError, match="speed_ms"):
            _make_bsm(speed_ms=-0.1)

    def test_bsm_intent_validation(self):
        """허용되지 않은 intent 면 ValueError, 허용된 값은 모두 통과."""
        with pytest.raises(ValueError, match="intent"):
            _make_bsm(intent="teleporting")
        for intent in ("cruise", "ascending", "descending", "hovering", "landing", "emergency"):
            bsm = _make_bsm(intent=intent)
            assert bsm.intent == intent


# ── 2. EVA 생성 및 검증 ─────────────────────────────────────────────────


class TestEmergencyAlert:
    """EmergencyAlert 생성·검증 테스트."""

    def test_eva_creation(self):
        """유효한 EVA 가 정상 생성된다."""
        eva = _make_eva()
        assert eva.msg_type == EVA
        assert eva.emergency_type == "low_battery"
        assert eva.severity == "warning"

    def test_eva_severity_validation(self):
        """severity 검증 — 유효 값은 통과, 잘못된 값은 ValueError."""
        with pytest.raises(ValueError, match="severity"):
            _make_eva(severity="panic")
        for sev in ("warning", "critical", "mayday"):
            assert _make_eva(severity=sev).severity == sev

    def test_eva_emergency_type_validation(self):
        """emergency_type 검증 — 유효 값은 통과, 잘못된 값은 ValueError."""
        with pytest.raises(ValueError, match="emergency_type"):
            _make_eva(emergency_type="alien_attack")
        for et in ("low_battery", "motor_failure", "gps_lost",
                    "geofence_breach", "collision_imminent", "forced_landing"):
            assert _make_eva(emergency_type=et).emergency_type == et


# ── 3. 코덱 JSON 라운드트립 ─────────────────────────────────────────────


class TestV2XCodecJSON:
    """V2XCodec JSON encode/decode 라운드트립 테스트."""

    def test_bsm_json_round_trip(self):
        """BSM JSON 라운드트립: decode(encode(msg)) == msg."""
        bsm = _make_bsm()
        assert V2XCodec.decode(V2XCodec.encode(bsm)) == bsm

    def test_eva_json_round_trip(self):
        """EVA JSON 라운드트립: decode(encode(msg)) == msg."""
        eva = _make_eva()
        assert V2XCodec.decode(V2XCodec.encode(eva)) == eva

    def test_unknown_msg_type_decode_raises(self):
        """알 수 없는 msg_type 디코드 시 ValueError."""
        with pytest.raises(ValueError, match="msg_type"):
            V2XCodec.decode({"msg_type": "unknown_type"})


# ── 4. 코덱 바이너리 라운드트립 ──────────────────────────────────────────


class TestV2XCodecBinary:
    """V2XCodec binary encode/decode 라운드트립 테스트."""

    def test_bsm_binary_round_trip(self):
        """BSM 바이너리 라운드트립: decode_binary(encode_binary(msg)) == msg."""
        bsm = _make_bsm()
        assert V2XCodec.decode_binary(V2XCodec.encode_binary(bsm)) == bsm

    def test_eva_binary_round_trip(self):
        """EVA 바이너리 라운드트립: decode_binary(encode_binary(msg)) == msg."""
        eva = _make_eva()
        assert V2XCodec.decode_binary(V2XCodec.encode_binary(eva)) == eva

    def test_binary_size_consistency(self):
        """바이너리 크기가 binary_size 와 일치한다."""
        bsm = _make_bsm()
        eva = _make_eva()
        assert len(V2XCodec.encode_binary(bsm)) == V2XCodec.binary_size(BSM)
        assert len(V2XCodec.encode_binary(eva)) == V2XCodec.binary_size(EVA)


# ── 5. V2XChannel 테스트 ─────────────────────────────────────────────────


class TestV2XChannel:
    """V2XChannel 브로드캐스트·통계 테스트."""

    def test_range_filtering(self):
        """범위 내 드론만 수신한다."""
        ch = V2XChannel(range_m=100.0, loss_rate=0.0, seed=42)
        bsm = _make_bsm()
        drones = [
            ("D-near", (50.0, 0.0, 0.0)),
            ("D-far", (200.0, 0.0, 0.0)),
        ]
        received = ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        ids = [r[0] for r in received]
        assert "D-near" in ids
        assert "D-far" not in ids

    def test_loss_rate_deterministic_drops(self):
        """loss_rate > 0 + seed 로 결정적 드롭이 발생한다."""
        ch = V2XChannel(range_m=500.0, loss_rate=0.5, seed=42)
        bsm = _make_bsm()
        drones = [(f"D-{i}", (float(i * 10), 0.0, 0.0)) for i in range(20)]
        received = ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        assert 0 < len(received) < 20

    def test_stats_tracking(self):
        """broadcast 후 stats 가 올바르게 갱신된다."""
        ch = V2XChannel(range_m=100.0, loss_rate=0.0, seed=42)
        bsm = _make_bsm()
        drones = [("D-in", (50.0, 0.0, 0.0)), ("D-out", (200.0, 0.0, 0.0))]
        ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        s = ch.stats()
        assert s.total_sent == 2
        assert s.total_received == 1
        assert s.total_lost == 1
        assert s.delivery_rate == pytest.approx(0.5)

    def test_zero_loss_delivers_all_in_range(self):
        """loss_rate=0 이면 범위 내 모든 드론이 수신한다."""
        ch = V2XChannel(range_m=500.0, loss_rate=0.0, seed=42)
        bsm = _make_bsm()
        drones = [("D-1", (100.0, 0.0, 0.0)), ("D-2", (200.0, 0.0, 0.0))]
        received = ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        assert len(received) == 2

    def test_no_drones_in_range(self):
        """범위 내 드론이 없으면 빈 리스트를 반환한다."""
        ch = V2XChannel(range_m=10.0, loss_rate=0.0, seed=42)
        bsm = _make_bsm()
        drones = [("D-far", (1000.0, 1000.0, 1000.0))]
        received = ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        assert received == []

    def test_multiple_broadcasts_accumulate_stats(self):
        """여러 번 broadcast 하면 stats 가 누적된다."""
        ch = V2XChannel(range_m=500.0, loss_rate=0.0, seed=42)
        bsm = _make_bsm()
        drones = [("D-1", (100.0, 0.0, 0.0))]
        ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        ch.broadcast((0.0, 0.0, 0.0), bsm, drones)
        s = ch.stats()
        assert s.total_sent == 3
        assert s.total_received == 3

    def test_determinism_same_seed(self):
        """같은 시드를 사용하면 같은 결과가 나온다."""
        drones = [(f"D-{i}", (float(i * 10), 0.0, 0.0)) for i in range(30)]
        bsm = _make_bsm()

        ch1 = V2XChannel(range_m=500.0, loss_rate=0.3, seed=12345)
        r1 = ch1.broadcast((0.0, 0.0, 0.0), bsm, drones)

        ch2 = V2XChannel(range_m=500.0, loss_rate=0.3, seed=12345)
        r2 = ch2.broadcast((0.0, 0.0, 0.0), bsm, drones)

        assert [r[0] for r in r1] == [r[0] for r in r2]
