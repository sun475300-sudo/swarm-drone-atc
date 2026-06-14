"""ODYSSEY Phase 422 — 운영 의도 4D 볼륨 교환 포맷 테스트."""
from __future__ import annotations

import pytest

from simulation.operational_intent import (
    OperationalIntent,
    Volume4D,
    intents_conflict,
    volumes_intersect,
)


def _square(lat0: float, lon0: float, size: float = 0.02) -> tuple[tuple[float, float], ...]:
    """주어진 좌하단 모서리에서 정사각형 외곽선을 만든다."""
    return (
        (lat0, lon0),
        (lat0 + size, lon0),
        (lat0 + size, lon0 + size),
        (lat0, lon0 + size),
    )


def _volume(
    lat0: float = 34.79,
    lon0: float = 126.39,
    alt=(0.0, 120.0),
    t=(0.0, 60.0),
) -> Volume4D:
    return Volume4D(
        outline=_square(lat0, lon0),
        altitude_lower_m=alt[0],
        altitude_upper_m=alt[1],
        time_start_s=t[0],
        time_end_s=t[1],
    )


# --- Volume4D 검증 ---------------------------------------------------------


def test_volume_requires_at_least_three_vertices():
    with pytest.raises(ValueError, match="꼭짓점"):
        Volume4D(
            outline=((34.79, 126.39), (34.81, 126.39)),
            altitude_lower_m=0.0,
            altitude_upper_m=120.0,
            time_start_s=0.0,
            time_end_s=60.0,
        )


def test_volume_rejects_latitude_out_of_range():
    with pytest.raises(ValueError, match="위도"):
        Volume4D(
            outline=((91.0, 126.39), (34.81, 126.39), (34.81, 126.41)),
            altitude_lower_m=0.0,
            altitude_upper_m=120.0,
            time_start_s=0.0,
            time_end_s=60.0,
        )


def test_volume_rejects_longitude_out_of_range():
    with pytest.raises(ValueError, match="경도"):
        Volume4D(
            outline=((34.79, 181.0), (34.81, 126.39), (34.81, 126.41)),
            altitude_lower_m=0.0,
            altitude_upper_m=120.0,
            time_start_s=0.0,
            time_end_s=60.0,
        )


def test_volume_rejects_inverted_altitude():
    with pytest.raises(ValueError, match="고도"):
        _volume(alt=(120.0, 0.0))


def test_volume_rejects_inverted_time_window():
    with pytest.raises(ValueError, match="시각"):
        _volume(t=(60.0, 0.0))


def test_volume_is_frozen():
    vol = _volume()
    with pytest.raises(Exception):
        vol.altitude_lower_m = 50.0  # type: ignore[misc]


def test_bbox_computes_min_max():
    vol = _volume(lat0=34.79, lon0=126.39)
    lat_min, lat_max, lon_min, lon_max = vol.bbox()
    assert lat_min == pytest.approx(34.79)
    assert lat_max == pytest.approx(34.81)
    assert lon_min == pytest.approx(126.39)
    assert lon_max == pytest.approx(126.41)


# --- 직렬화 라운드트립 -----------------------------------------------------


def test_volume_dict_roundtrip():
    vol = _volume()
    assert Volume4D.from_dict(vol.to_dict()) == vol


def test_volume_from_dict_rejects_missing_field():
    with pytest.raises(ValueError, match="역직렬화 실패"):
        Volume4D.from_dict({"outline": [[34.79, 126.39]]})


def test_volume_from_dict_wraps_semantic_error():
    # 구조는 유효하나 값이 잘못된 경우(고도 역전)도 일관되게 래핑되어야 한다
    payload = _volume().to_dict()
    payload["altitude_lower_m"] = 200.0
    payload["altitude_upper_m"] = 0.0
    with pytest.raises(ValueError, match="역직렬화 실패"):
        Volume4D.from_dict(payload)


def test_intent_dict_roundtrip():
    oi = OperationalIntent(
        intent_id="OI-001",
        state="ACCEPTED",
        priority=3,
        volumes=(_volume(), _volume(t=(60.0, 120.0))),
    )
    assert OperationalIntent.from_dict(oi.to_dict()) == oi


def test_intent_to_dict_is_json_serializable():
    import json

    oi = OperationalIntent(intent_id="OI-001", state="ACTIVATED", priority=1, volumes=(_volume(),))
    # 예외 없이 직렬화되어야 한다
    encoded = json.dumps(oi.to_dict())
    assert "OI-001" in encoded


# --- OperationalIntent 검증 ------------------------------------------------


def test_intent_rejects_empty_id():
    with pytest.raises(ValueError, match="intent_id"):
        OperationalIntent(intent_id="", state="ACCEPTED", priority=3, volumes=(_volume(),))


def test_intent_rejects_unknown_state():
    with pytest.raises(ValueError, match="상태"):
        OperationalIntent(intent_id="OI-1", state="PENDING", priority=3, volumes=(_volume(),))


def test_intent_rejects_nonpositive_priority():
    with pytest.raises(ValueError, match="priority"):
        OperationalIntent(intent_id="OI-1", state="ACCEPTED", priority=0, volumes=(_volume(),))


def test_intent_requires_at_least_one_volume():
    with pytest.raises(ValueError, match="볼륨"):
        OperationalIntent(intent_id="OI-1", state="ACCEPTED", priority=3, volumes=())


# --- 4D 교차 판정 ----------------------------------------------------------


def test_volumes_intersect_when_all_axes_overlap():
    a = _volume(lat0=34.79, lon0=126.39, alt=(0.0, 120.0), t=(0.0, 60.0))
    b = _volume(lat0=34.80, lon0=126.40, alt=(50.0, 150.0), t=(30.0, 90.0))
    assert volumes_intersect(a, b) is True


def test_identical_volumes_intersect():
    a = _volume()
    assert volumes_intersect(a, _volume()) is True


def test_volumes_intersect_is_symmetric():
    a = _volume(lat0=34.79, lon0=126.39, alt=(0.0, 120.0), t=(0.0, 60.0))
    b = _volume(lat0=34.80, lon0=126.40, alt=(50.0, 150.0), t=(30.0, 90.0))
    assert volumes_intersect(a, b) == volumes_intersect(b, a)


def test_volumes_disjoint_in_time_do_not_intersect():
    a = _volume(t=(0.0, 60.0))
    b = _volume(t=(60.0, 120.0))  # 경계 접촉 = 비충돌
    assert volumes_intersect(a, b) is False


def test_volumes_disjoint_in_altitude_do_not_intersect():
    a = _volume(alt=(0.0, 100.0))
    b = _volume(alt=(100.0, 200.0))
    assert volumes_intersect(a, b) is False


def test_volumes_disjoint_geographically_do_not_intersect():
    a = _volume(lat0=34.79, lon0=126.39)
    b = _volume(lat0=35.50, lon0=127.50)
    assert volumes_intersect(a, b) is False


def test_intents_conflict_detects_overlapping_volume_pair():
    a = OperationalIntent(
        intent_id="A", state="ACTIVATED", priority=2, volumes=(_volume(t=(0.0, 60.0)),)
    )
    b = OperationalIntent(
        intent_id="B",
        state="ACCEPTED",
        priority=3,
        volumes=(_volume(t=(120.0, 180.0)), _volume(t=(30.0, 90.0))),
    )
    assert intents_conflict(a, b) is True
    assert intents_conflict(b, a) is True  # 대칭성


def test_ended_intent_never_conflicts():
    a = OperationalIntent(intent_id="A", state="ENDED", priority=2, volumes=(_volume(),))
    b = OperationalIntent(intent_id="B", state="ACTIVATED", priority=3, volumes=(_volume(),))
    assert intents_conflict(a, b) is False
