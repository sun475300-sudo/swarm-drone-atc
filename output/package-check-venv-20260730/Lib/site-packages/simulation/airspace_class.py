"""Phase 408 (ODYSSEY): ICAO 공역 클래스 A-G 자동 매핑 — 결정적 산정 API.

`docs/certification/AIRSPACE_CLASS_MAPPING.md` §6에서 "차기 격상 제안 (API 신설)"로
명시한 `airspaceClass(altitude, lon?, lat?)` 후보를 결정적 Python 구현으로 격상한다.
외부 호출·난수 없이 입력 검증 + 한국 특화 결정 규칙으로 ICAO 클래스를 산정한다.

판정 근거 (AIRSPACE_CLASS_MAPPING.md §3 매핑 매트릭스 + §6 결정 규칙):
  1) 군 작전 공역(restricted) NFZ 내부              → 'R'
  2) 공항 NFZ 내부, 특별승인 없음                    → 'B' (운영 금지/차단)
  3) 공항 NFZ 내부, 특별승인 있음                    → 'D' (관제권 진입)
  4) 고도 > 240 m AGL (시뮬/운용 상한 초과)          → 'B'
  5) 고도 150 m < h ≤ 240 m (통제구역 진입)          → 'E' (특별승인)
  6) 고도 0 ≤ h ≤ 150 m, NFZ 외부 (비통제)           → 'G'

가정 (명시): 문서 §3은 "180 m+ → D/C" 서술과 §6은 "(150,240] → E"로 일부 상이하다.
본 구현은 API 계약인 §6 결정 규칙을 권위 있는 알고리즘으로 채택한다. ICAO Class A·C·F는
무인비행장치 운용 고도 영역(≤240 m AGL) 밖이거나 한국 미운용(F)이라 산정 대상에서 제외한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# SDACS 9층 고도 레이어 (단위: m AGL) — AIRSPACE_CLASS_MAPPING.md §2
ALTITUDE_LAYERS = (0, 30, 60, 90, 120, 150, 180, 210, 240)

# 고도 임계값 (m AGL)
LEGAL_CEILING_AGL_M = 150.0  # 무인비행장치 법정 상한 (Class G 경계)
SIM_CEILING_AGL_M = 240.0  # 시뮬레이션/운용 상한 (L8)

# ICAO 공역 클래스 메타데이터 — AIRSPACE_CLASS_MAPPING.md §1 (한국 운용: A·B·C·D·E·G)
ICAO_CLASS_INFO: dict[str, dict[str, object]] = {
    "B": {"ifr": True, "vfr": True, "control": "강제", "separation": "모두-모두"},
    "D": {"ifr": True, "vfr": True, "control": "강제", "separation": "IFR-IFR"},
    "E": {"ifr": True, "vfr": True, "control": "IFR 강제·VFR 자유", "separation": "IFR-IFR"},
    "G": {"ifr": True, "vfr": True, "control": "비통제", "separation": "없음"},
    "R": {"ifr": True, "vfr": False, "control": "제한/금지", "separation": "운영 금지"},
}

# 클래스별 SDACS 충족 요건 — AIRSPACE_CLASS_MAPPING.md §4
_G_REQUIREMENTS = (
    "Remote ID 송출 (ASTM F3411 v2.0)",
    "5계층 안전망 (CPA 90초 + APF + CBS 협조)",
    "NOTAM 준수 (동적 NFZ)",
)
_E_REQUIREMENTS = _G_REQUIREMENTS + (
    "사전 비행승인 (UTM)",
    "BVLOS/야간 특별비행승인",
)
_D_REQUIREMENTS = _E_REQUIREMENTS + (
    "ATC 통신 의무 (atcCommand 9종 + TTS)",
    "SORA SAIL III+ 인증",
)
_B_REQUIREMENTS = ("운영 금지 — NFZ 지오펜스 + UTM 차단",)
_R_REQUIREMENTS = ("운영 금지/특별승인·면제 — 군 작전 공역, 동적 NFZ/NOTAM",)

CLASS_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "G": _G_REQUIREMENTS,
    "E": _E_REQUIREMENTS,
    "D": _D_REQUIREMENTS,
    "B": _B_REQUIREMENTS,
    "R": _R_REQUIREMENTS,
}


@dataclass(frozen=True)
class NoFlyZone:
    """공역 제한 구역 정의 (공항 관제권 또는 군 작전 공역)."""

    name: str
    center_lon: float
    center_lat: float
    radius_m: float
    kind: str = "airport"  # 'airport' (관제권) | 'military' (제한·금지)

    def __post_init__(self) -> None:
        if self.kind not in ("airport", "military"):
            raise ValueError(f"NoFlyZone.kind must be 'airport' or 'military', got {self.kind!r}")
        if not math.isfinite(self.radius_m) or self.radius_m <= 0:
            raise ValueError(f"NoFlyZone.radius_m must be positive finite, got {self.radius_m!r}")


@dataclass(frozen=True)
class AirspaceClassification:
    """공역 클래스 산정 결과."""

    icao_class: str  # 'B' | 'D' | 'E' | 'G' | 'R'
    controlled: bool  # 관제 공역 여부
    approval_required: bool  # 비행승인/특별승인 필요 여부
    layer_index: int | None  # SDACS 9층 레이어 인덱스 (0..8), 상한 초과 시 None
    reason: str  # 산정 근거 (한국어)
    requirements: tuple[str, ...] = field(default_factory=tuple)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 위경도 좌표 간 대권 거리 (m). WGS84 평균 반경 사용."""
    earth_radius_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * earth_radius_m * math.asin(math.sqrt(a))


def sdacs_layer_index(altitude_m: float) -> int | None:
    """고도(m AGL)를 포함하는 SDACS 레이어 인덱스를 반환한다.

    레이어 경계 [L_i, L_{i+1}) 구간으로 판정하며, 상한(240 m) 이상은 None.
    """
    if altitude_m < 0:
        raise ValueError(f"altitude_m must be >= 0, got {altitude_m!r}")
    for i in range(len(ALTITUDE_LAYERS) - 1):
        if ALTITUDE_LAYERS[i] <= altitude_m < ALTITUDE_LAYERS[i + 1]:
            return i
    if altitude_m == ALTITUDE_LAYERS[-1]:
        return len(ALTITUDE_LAYERS) - 1
    return None  # 240 m 초과 (시뮬 한계 밖)


def _zone_containing(
    lon: float, lat: float, nfz_zones: tuple[NoFlyZone, ...], kind: str
) -> NoFlyZone | None:
    """주어진 좌표를 포함하는 첫 번째 NFZ(kind 일치)를 반환한다."""
    for zone in nfz_zones:
        if zone.kind != kind:
            continue
        if _haversine_m(lat, lon, zone.center_lat, zone.center_lon) <= zone.radius_m:
            return zone
    return None


def classify_airspace(
    altitude_m: float,
    lon: float | None = None,
    lat: float | None = None,
    nfz_zones: tuple[NoFlyZone, ...] | None = None,
    has_special_approval: bool = False,
) -> AirspaceClassification:
    """고도와 (선택적) 좌표로부터 ICAO 공역 클래스를 결정적으로 산정한다.

    Args:
        altitude_m: 고도 (m AGL). 0 이상 유한값이어야 한다.
        lon, lat: 위경도 (deg). NFZ 판정에 사용. 둘 다 주어지거나 둘 다 생략.
        nfz_zones: 공역 제한 구역 목록. 생략 시 NFZ 판정 없이 고도만으로 산정.
        has_special_approval: 공항 NFZ 진입 특별승인 보유 여부.

    Returns:
        AirspaceClassification — 산정된 클래스·관제 여부·승인 필요·근거·요건.

    Raises:
        ValueError: altitude_m 가 음수/비유한, 또는 lon/lat 중 하나만 주어진 경우.
    """
    if not math.isfinite(altitude_m) or altitude_m < 0:
        raise ValueError(f"altitude_m must be a finite value >= 0, got {altitude_m!r}")
    if (lon is None) != (lat is None):
        raise ValueError("lon and lat must be provided together or both omitted")

    layer = sdacs_layer_index(altitude_m)
    zones = tuple(nfz_zones) if nfz_zones else ()

    # 1) 좌표 기반 NFZ 판정 (군 작전 → 공항 순)
    if lon is not None and lat is not None and zones:
        military = _zone_containing(lon, lat, zones, "military")
        if military is not None:
            return _result("R", layer, f"군 작전 공역 '{military.name}' 내부 — 운영 제한/금지")
        airport = _zone_containing(lon, lat, zones, "airport")
        if airport is not None:
            if has_special_approval:
                return _result(
                    "D", layer, f"공항 관제권 '{airport.name}' 진입 — 특별승인 보유 (ATC 통신 의무)"
                )
            return _result("B", layer, f"공항 관제권 '{airport.name}' 내부 — 운영 금지 (특별승인 없음)")

    # 2) 고도 기반 판정
    if altitude_m > SIM_CEILING_AGL_M:
        return _result("B", layer, f"고도 {altitude_m:.0f} m — 운용 상한({SIM_CEILING_AGL_M:.0f} m) 초과")
    if altitude_m > LEGAL_CEILING_AGL_M:
        return _result(
            "E", layer, f"고도 {altitude_m:.0f} m — 법정 상한({LEGAL_CEILING_AGL_M:.0f} m) 초과, 통제구역 진입"
        )
    return _result("G", layer, f"고도 {altitude_m:.0f} m — 비통제 공역 (Class G)")


def _result(icao_class: str, layer: int | None, reason: str) -> AirspaceClassification:
    """클래스 메타데이터를 조합해 결과 객체를 생성한다."""
    controlled = icao_class in ("B", "C", "D", "E", "R")
    approval_required = icao_class != "G"
    return AirspaceClassification(
        icao_class=icao_class,
        controlled=controlled,
        approval_required=approval_required,
        layer_index=layer,
        reason=reason,
        requirements=CLASS_REQUIREMENTS[icao_class],
    )
