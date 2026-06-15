"""P740 디지털 트윈 동기화 엔진 검증."""
from __future__ import annotations

import math

import pytest

from src.digital_twin.sync_engine import (
    PX4_MODE_MAP,
    LatencyStats,
    TelemetrySnapshot,
    TelemetrySync,
    geodetic_to_enu,
)

# WGS84 (테스트 독립 기준 계산용)
_A = 6_378_137.0
_E2 = 6.694_379_990_14e-3


def _linear_enu(lat, lon, ref_lat, ref_lon):
    """독립 기준: 기준점 위도의 WGS84 곡률반경 기반 선형 접평면 근사.

    운용 범위(≤2km)에서 엄밀 ECEF→ENU와 ±0.5m 이내로 일치하므로
    Phase 226 정밀도 검증의 교차 기준점으로 사용한다.
    """
    la = math.radians(ref_lat)
    w = math.sqrt(1.0 - _E2 * math.sin(la) ** 2)
    meridian = _A * (1.0 - _E2) / w ** 3      # 자오선 곡률반경
    prime_vert = _A / w                        # 묘유선 곡률반경
    north_per_deg = math.radians(1.0) * meridian
    east_per_deg = math.radians(1.0) * prime_vert * math.cos(la)
    return (lon - ref_lon) * east_per_deg, (lat - ref_lat) * north_per_deg


def _dest_point(ref_lat, ref_lon, dist_m, bearing_deg):
    """구면 전방 측지: 기준점에서 거리·방위로 목표 위경도 생성(테스트 표본용)."""
    r = 6_371_000.0
    la, lo = math.radians(ref_lat), math.radians(ref_lon)
    b, ang = math.radians(bearing_deg), dist_m / r
    la2 = math.asin(math.sin(la) * math.cos(ang) + math.cos(la) * math.sin(ang) * math.cos(b))
    lo2 = lo + math.atan2(
        math.sin(b) * math.sin(ang) * math.cos(la),
        math.cos(ang) - math.sin(la) * math.sin(la2),
    )
    return math.degrees(la2), math.degrees(lo2)


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


@pytest.mark.parametrize("dist_m", [500.0, 1000.0, 2000.0])
@pytest.mark.parametrize("bearing", [0.0, 45.0, 90.0, 135.0, 225.0, 315.0])
def test_enu_horizontal_within_half_meter_at_operational_range(dist_m, bearing) -> None:
    """GPS→ENU 수평 변환이 운용 범위(≤2km)에서 ±0.5m 이내 (Phase 226)."""
    ref_lat, ref_lon = 34.79, 126.39  # 목포 해역 기준점
    lat, lon = _dest_point(ref_lat, ref_lon, dist_m, bearing)

    east, north, _ = geodetic_to_enu(lat, lon, 0.0, ref_lat, ref_lon, 0.0)
    lin_e, lin_n = _linear_enu(lat, lon, ref_lat, ref_lon)

    err = math.hypot(east - lin_e, north - lin_n)
    assert err < 0.5, f"{dist_m}m/{bearing}deg ENU 오차 {err:.3f}m 가 ±0.5m 초과"


def test_enu_applies_longitude_cosine_correction() -> None:
    """경도 방향 변환에 cos(lat) 보정이 적용된다 (기존 평면 버그 회귀 가드)."""
    ref_lat, ref_lon = 34.79, 126.39
    # 정동(due east)으로 0.01° 떨어진 점
    lat, lon = ref_lat, ref_lon + 0.01

    east, north, up = geodetic_to_enu(lat, lon, 0.0, ref_lat, ref_lon, 0.0)

    # north·up 성분은 0에 가깝다
    assert abs(north) < 0.5
    assert abs(up) < 0.5

    # east 는 묘유선 곡률반경 × cos(lat) 기반 값과 일치 (mm 수준)
    la = math.radians(ref_lat)
    w = math.sqrt(1.0 - _E2 * math.sin(la) ** 2)
    expected_east = math.radians(0.01) * (_A / w) * math.cos(la)
    assert abs(east - expected_east) < 0.01

    # cos(lat) 미보정(버그) 값과는 18% 이상 차이가 나야 한다
    buggy_east = 0.01 * 111_320.0
    assert abs(east - buggy_east) / buggy_east > 0.15


def test_to_sdacs_state_keeps_altitude_as_z() -> None:
    """z 좌표는 ENU up 이 아니라 기체 고도(alt_m)를 그대로 사용한다."""
    sync = TelemetrySync()
    snap = TelemetrySnapshot(
        drone_id="DR-001", timestamp_us=0, received_ts=0.0,
        lat_deg=34.80, lon_deg=126.40, alt_m=85.0,
        vx_mps=0, vy_mps=0, vz_mps=0, heading_deg=0,
        battery_pct=70.0, flight_mode="AUTO",
    )
    state = sync.to_sdacs_state(snap, origin_lat=34.79, origin_lon=126.39)
    assert state["position"][2] == 85.0
    # 동쪽(lon 증가)·북쪽(lat 증가)으로 양(+) 변위
    assert state["position"][0] > 0
    assert state["position"][1] > 0


def test_mode_map_has_critical_modes() -> None:
    """핵심 PX4 모드가 매핑에 포함."""
    assert PX4_MODE_MAP[4] == "AUTO"
    assert PX4_MODE_MAP[9] == "RTL"
    assert PX4_MODE_MAP[10] == "LAND"
