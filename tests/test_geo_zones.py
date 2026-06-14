"""ODYSSEY Phase 406 — 다국 좌표계·시간대 자동 판정.

전 세계 위·경도를 UTM(Universal Transverse Mercator) 그리드 존·반구·MGRS 위도
밴드·EPSG 코드로 결정적 변환하고, 경도 기반 공칭 시간대를 산출하는지 검증한다.
ODYSSEY 국제 확장 트랙(한·미·EU·일 동시 운용)에서 좌표계 정렬의 기준이 된다.
"""
from __future__ import annotations

import math

import pytest

from simulation.geo_zones import UTMZone, classify, timezone_offset, utm_zone


class TestUtmZoneMajorCities:
    """대표 도시 좌표가 표준 UTM 존으로 매핑되는지 검증."""

    @pytest.mark.parametrize(
        "lat, lon, zone, band, epsg",
        [
            (37.5665, 126.9780, 52, "S", 32652),  # 서울
            (40.7128, -74.0060, 18, "T", 32618),  # 뉴욕
            (48.8566, 2.3522, 31, "U", 32631),    # 파리
            (35.6762, 139.6503, 54, "S", 32654),  # 도쿄
            (-33.8688, 151.2093, 56, "H", 32756), # 시드니 (남반구)
        ],
    )
    def test_known_cities_map_to_expected_zone(self, lat, lon, zone, band, epsg):
        z = utm_zone(lat, lon)
        assert z.zone == zone
        assert z.band == band
        assert z.epsg == epsg

    def test_southern_hemisphere_flag(self):
        assert utm_zone(-33.8688, 151.2093).hemisphere == "S"

    def test_northern_hemisphere_flag(self):
        assert utm_zone(37.5665, 126.9780).hemisphere == "N"


class TestCentralMeridian:
    """중앙 자오선이 존 번호와 정합하는지 검증."""

    def test_central_meridian_formula(self):
        # 존 n 의 중앙 자오선 = 6n - 183
        for lon in (-179.0, -1.0, 0.0, 1.0, 129.0, 179.0):
            z = utm_zone(0.0, lon)
            assert z.central_meridian == 6 * z.zone - 183

    def test_central_meridian_within_zone(self):
        z = utm_zone(37.5, 127.0)
        assert abs(z.central_meridian - 127.0) <= 3.0


class TestAntimeridian:
    """자오선(lon=±180) 경계 — 공식 wrap 회귀 방지."""

    def test_lon_180_maps_to_zone_60(self):
        z = utm_zone(0.0, 180.0)
        assert z.zone == 60
        assert z.central_meridian == 177.0
        assert z.epsg == 32660

    def test_lon_minus_180_maps_to_zone_1(self):
        z = utm_zone(0.0, -180.0)
        assert z.zone == 1
        assert z.central_meridian == -177.0
        assert z.epsg == 32601


class TestUtmStandardExceptions:
    """노르웨이(32V)·스발바르 UTM 표준 예외 처리."""

    def test_norway_zone_32v_extends_west(self):
        # 베르겐(60.39N, 5.32E)은 표준 공식상 31존이지만 예외로 32존
        assert utm_zone(60.39, 5.32).zone == 32

    def test_norway_exception_only_in_band_v(self):
        # 밴드 V(56-64) 밖에서는 예외 미적용 — 5.32E 는 31존
        assert utm_zone(50.0, 5.32).zone == 31

    def test_norway_band_v_west_of_3e_stays_31(self):
        # 밴드 V 안이지만 3°E 서쪽 — 31V 유지(예외 미적용)
        assert utm_zone(60.0, 2.0).zone == 31

    def test_norway_band_v_east_boundary_resumes_33(self):
        # 32V는 12°E에서 끝나고 동쪽은 표준 33존 재개
        assert utm_zone(60.0, 12.0).zone == 33

    @pytest.mark.parametrize(
        "lon, zone",
        [(7.0, 31), (10.0, 33), (25.0, 35), (35.0, 37)],
    )
    def test_svalbard_widened_zones(self, lon, zone):
        # 스발바르(밴드 X, 72-84N)는 31/33/35/37 존만 사용
        assert utm_zone(78.0, lon).zone == zone

    def test_band_x_negative_longitude_uses_standard_formula(self):
        # 밴드 X라도 음수 경도(그린란드 등)는 예외 미적용 — 표준 공식
        assert utm_zone(78.0, -10.0).zone == 29


class TestTimezoneOffset:
    """경도 기반 공칭 시간대(정수 UTC 오프셋) 산출."""

    @pytest.mark.parametrize(
        "lon, offset",
        [
            (0.0, 0),
            (-74.0060, -5),   # 뉴욕
            (139.6503, 9),    # 도쿄
            (151.2093, 10),   # 시드니
            (179.0, 12),
            (-179.0, -12),
        ],
    )
    def test_offset_from_longitude(self, lon, offset):
        assert timezone_offset(lon) == offset

    def test_offset_bounds(self):
        for lon in (-180.0, 180.0):
            assert -12 <= timezone_offset(lon) <= 12

    @pytest.mark.parametrize("lon", [math.nan, math.inf, -181.0, 181.0])
    def test_invalid_longitude_rejected(self, lon):
        with pytest.raises(ValueError):
            timezone_offset(lon)


class TestValidation:
    """경계 입력 검증 — UTM 정의역(-80..84 위도) 밖은 거부."""

    def test_polar_north_rejected(self):
        with pytest.raises(ValueError):
            utm_zone(85.0, 0.0)

    def test_polar_south_rejected(self):
        with pytest.raises(ValueError):
            utm_zone(-81.0, 0.0)

    @pytest.mark.parametrize("lon", [-181.0, 181.0, math.inf])
    def test_longitude_out_of_range_rejected(self, lon):
        with pytest.raises(ValueError):
            utm_zone(0.0, lon)

    def test_nan_rejected(self):
        with pytest.raises(ValueError):
            utm_zone(math.nan, 0.0)


class TestClassify:
    """통합 분류 결과(딕셔너리)의 계약 검증."""

    def test_classify_contains_zone_and_timezone(self):
        result = classify(37.5665, 126.9780)
        assert result["utm"] == "52S"
        assert result["epsg"] == 32652
        assert result["hemisphere"] == "N"
        assert result["timezone_offset"] == 8  # 경도 126.98 → 공칭 +8 (정치 KST=+9와 별개)
        assert result["central_meridian"] == 129.0

    def test_classify_round_trips_to_dataclass(self):
        result = classify(48.8566, 2.3522)
        z = utm_zone(48.8566, 2.3522)
        assert result["utm"] == f"{z.zone}{z.band}"
        assert isinstance(z, UTMZone)
