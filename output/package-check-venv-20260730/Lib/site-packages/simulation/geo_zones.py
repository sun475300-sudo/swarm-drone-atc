"""ODYSSEY Phase 406 — 다국 좌표계·시간대 자동 판정.

전 세계 위·경도를 UTM(Universal Transverse Mercator) 그리드 존으로 결정적
변환한다. ODYSSEY 국제 확장(EASA U-space·FAA UTM·K-UTM 동시 호환)에서 드론이
국가 경계를 넘을 때 좌표계·EPSG·공칭 시간대를 일관되게 식별하기 위한 기준 모듈.

순수 함수 — 외부 의존성 없음. 극지(±80° 밖)는 UTM 정의역 밖이라 거부한다(UPS 사용).
시간대는 경도 기반 *공칭* 오프셋으로, 정치적 시간대(서머타임·국가 경계)와 다를 수 있다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# MGRS 위도 밴드 문자 (A·B·I·O·Y·Z 제외). C(-80°)부터 X(72~84°)까지.
_LATITUDE_BANDS = "CDEFGHJKLMNPQRSTUVWX"

# UTM 정의역 (위도). 극지는 UPS(Universal Polar Stereographic) 영역.
_LAT_MIN = -80.0
_LAT_MAX = 84.0

_EPSG_NORTH_BASE = 32600
_EPSG_SOUTH_BASE = 32700

_DEGREES_PER_HOUR = 15.0


@dataclass(frozen=True)
class UTMZone:
    """UTM 그리드 존 분류 결과 (불변)."""

    zone: int               # 그리드 존 번호 1-60
    hemisphere: str         # 'N' | 'S'
    band: str               # MGRS 위도 밴드 문자 C-X
    central_meridian: float # 중앙 자오선 (도)
    epsg: int               # EPSG 코드 (북반구 326xx / 남반구 327xx)


def _validate(lat: float, lon: float) -> None:
    """위·경도 유효성 검사 — 시스템 경계에서 fail-fast."""
    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError(f"위·경도는 유한값이어야 합니다: lat={lat}, lon={lon}")
    if not (_LAT_MIN <= lat <= _LAT_MAX):
        raise ValueError(
            f"위도 {lat}는 UTM 정의역 [{_LAT_MIN}, {_LAT_MAX}] 밖입니다 (극지는 UPS 사용)"
        )
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"경도 {lon}는 [-180, 180] 밖입니다")


def _latitude_band(lat: float) -> str:
    """위도 → MGRS 밴드 문자. X 밴드(72~84°)는 12° 폭이라 클램프한다."""
    index = min(int((lat - _LAT_MIN) / 8.0), len(_LATITUDE_BANDS) - 1)
    return _LATITUDE_BANDS[index]


def _zone_number(lat: float, lon: float, band: str) -> int:
    """그리드 존 번호 — 노르웨이(32V)·스발바르 표준 예외 포함."""
    zone = int((lon + 180.0) / 6.0) % 60 + 1
    # 자오선(lon=180)은 공식이 0으로 wrap → 존 60(중앙 자오선 177°)이 정답.
    if lon == 180.0:
        zone = 60

    # 노르웨이 예외: 밴드 V(56~64°)에서 존 32가 서쪽(3°E)까지 확장.
    if band == "V" and 3.0 <= lon < 12.0:
        return 32

    # 스발바르 예외: 밴드 X(72~84°)는 31/33/35/37 존만 사용.
    if band == "X" and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    return zone


def utm_zone(lat: float, lon: float) -> UTMZone:
    """위·경도를 UTM 존 분류로 변환한다."""
    _validate(lat, lon)
    band = _latitude_band(lat)
    zone = _zone_number(lat, lon, band)
    hemisphere = "N" if lat >= 0 else "S"
    central_meridian = float(6 * zone - 183)
    epsg = (_EPSG_NORTH_BASE if hemisphere == "N" else _EPSG_SOUTH_BASE) + zone
    return UTMZone(
        zone=zone,
        hemisphere=hemisphere,
        band=band,
        central_meridian=central_meridian,
        epsg=epsg,
    )


def timezone_offset(lon: float) -> int:
    """경도 기반 공칭 UTC 오프셋(정수 시간). 정치적 시간대와 다를 수 있다."""
    if not math.isfinite(lon) or not (-180.0 <= lon <= 180.0):
        raise ValueError(f"경도 {lon}는 [-180, 180] 밖입니다")
    offset = int(round(lon / _DEGREES_PER_HOUR))
    return max(-12, min(12, offset))


def classify(lat: float, lon: float) -> dict:
    """UTM 존 + 공칭 시간대를 통합한 분류 딕셔너리를 반환한다."""
    z = utm_zone(lat, lon)
    return {
        "utm": f"{z.zone}{z.band}",
        "zone": z.zone,
        "band": z.band,
        "hemisphere": z.hemisphere,
        "central_meridian": z.central_meridian,
        "epsg": z.epsg,
        "timezone_offset": timezone_offset(lon),
    }
