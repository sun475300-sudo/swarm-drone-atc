"""P740 디지털 트윈 동기화 엔진 검증."""
from __future__ import annotations

from src.digital_twin.sync_engine import (
    PX4_MODE_MAP,
    LatencyStats,
    TelemetrySnapshot,
    TelemetrySync,
)


def test_parse_global_position_int_scaling() -> None:
    """MAVLink 정수 스케일 → 실수 변환."""
    sync = TelemetrySync()
    snap = sync.parse_mavlink_global_position(
        drone_id="DR-001",
        time_boot_us=1_000_000,
        lat_int=375600000,    # 37.56 deg
        lon_int=1269700000,   # 126.97 deg
        alt_mm=120_000,       # 120m
        vx_cmps=1500,         # 15 m/s
        vy_cmps=0,
        vz_cmps=-100,         # -1 m/s
        hdg_cdeg=9000,        # 90 deg
        battery_pct=85.5,
        flight_mode=4,
    )
    assert snap.drone_id == "DR-001"
    assert snap.lat_deg == 37.56
    assert snap.lon_deg == 126.97
    assert snap.alt_m == 120.0
    assert snap.vx_mps == 15.0
    assert snap.vz_mps == -1.0
    assert snap.heading_deg == 90.0
    assert snap.flight_mode == "AUTO"


def test_unknown_mode_falls_back() -> None:
    """미지 모드는 'UNKNOWN'."""
    sync = TelemetrySync()
    snap = sync.parse_mavlink_global_position(
        "DR-X", 0, 0, 0, 0, 0, 0, 0, 0, flight_mode=999,
    )
    assert snap.flight_mode == "UNKNOWN"


def test_update_records_latency() -> None:
    """업데이트 후 통계 기록."""
    sync = TelemetrySync(target_latency_ms=50.0)
    snap = TelemetrySnapshot(
        drone_id="DR-001", timestamp_us=0, received_ts=0.0,
        lat_deg=37.5, lon_deg=127.0, alt_m=100.0,
        vx_mps=0, vy_mps=0, vz_mps=0, heading_deg=0,
        battery_pct=100.0, flight_mode="AUTO",
    )
    ok = sync.update(snap)
    assert ok is True
    assert sync.stats.n_received == 1
    assert sync.get_latest("DR-001") is snap


def test_latency_stats_percentiles() -> None:
    """LatencyStats p50/p99 계산."""
    stats = LatencyStats()
    for v in range(1, 101):  # 1..100
        stats.add(float(v))
    assert 49 <= stats.p50() <= 51
    assert 98 <= stats.p99() <= 100
    assert stats.mean() == 50.5


def test_to_sdacs_state_local_enu() -> None:
    """GPS → 로컬 ENU 변환."""
    sync = TelemetrySync()
    snap = TelemetrySnapshot(
        drone_id="DR-001", timestamp_us=0, received_ts=0.0,
        lat_deg=37.5601, lon_deg=126.9701, alt_m=120.0,
        vx_mps=5.0, vy_mps=0, vz_mps=0, heading_deg=45,
        battery_pct=80.0, flight_mode="AUTO",
    )
    state = sync.to_sdacs_state(snap, origin_lat=37.56, origin_lon=126.97)
    assert state["drone_id"] == "DR-001"
    assert abs(state["position"][2] - 120.0) < 0.01
    assert state["velocity"] == [5.0, 0, 0]
    assert state["battery_pct"] == 80.0


def test_mode_map_has_critical_modes() -> None:
    """핵심 PX4 모드가 매핑에 포함."""
    assert PX4_MODE_MAP[4] == "AUTO"
    assert PX4_MODE_MAP[9] == "RTL"
    assert PX4_MODE_MAP[10] == "LAND"
