"""GENESIS Phase 323 — 외부 시뮬레이터 어댑터 (External Simulator Adapter).

SDACS 시나리오를 공개 ATM/UTM 시뮬레이터 두 곳과 **상호 변환**한다.

- **BlueSky** — TU Delft 오픈소스 항공교통 시뮬레이터(GPLv3). 시나리오 파일
  ``.scn`` 은 시각 접두(``HH:MM:SS.ss>``) 뒤에 스택 명령(``CRE``/``ADDWPT``/
  ``DEST``)을 붙이는 텍스트 포맷이다. 본 어댑터는 그 부분집합을 결정적으로
  생성·파싱한다. (Hoekstra & Ellerbroek, ICRAT 2016)
- **U-TRAFMAN** — 멀티에이전트 UAS 교통관리(UTM) 연구 시뮬레이터. 공개 단일
  정규 스키마가 없으므로, 본 모듈은 U-TRAFMAN 의 *운항(operation)·비행계획
  (flight plan)* 개념에 정렬한 **SDACS 호환 JSON 교환 포맷**을 정의한다.
  특정 릴리스의 바이트 동일 복제가 아니라 개념 정렬 교환 포맷이다(정직 공시).

정직성 공시
-----------
이 어댑터는 **포맷 변환기**다. 외부 시뮬레이터를 실제로 구동·검증하지 않는다.
BlueSky 측은 공개 문서화된 ``.scn`` 명령 문법을, U-TRAFMAN 측은 공개 기술 기반
교환 포맷을 대상으로 한다. 핵심 보증은 *왕복 항등*(SDACS→외부→SDACS 시 의미
보존)과 *결정성*(무작위성·부수효과 0)이다.

좌표계
------
정규 표현은 측지좌표(WGS84 lat/lon/alt)다 — BlueSky·U-TRAFMAN 양쪽이 측지계를
쓴다. SDACS 내부는 로컬 ENU 미터를 쓰므로, 기준점(ref) 기반 ENU↔측지 변환을
제공해 SDACS 시나리오를 어느 쪽으로든 다리 놓는다.

CLI:
    python simulation/external_sim_adapter.py --demo
    python simulation/external_sim_adapter.py --demo --format bluesky
    python simulation/external_sim_adapter.py --demo --format utrafman
    python simulation/external_sim_adapter.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any

# ── 단위 변환 상수 (SI ↔ 항공 관용 단위) ──────────────────────────────────
_M_PER_FT = 0.3048           # 1 ft = 0.3048 m (정의값)
_MPS_PER_KT = 1852.0 / 3600.0  # 1 knot = 1852 m / 3600 s (ICAO 정의, 절단 없음)
_FT_PER_M = 1.0 / _M_PER_FT
_KT_PER_MPS = 1.0 / _MPS_PER_KT

# ── WGS84 타원체 상수 (측지 ↔ ECEF ↔ ENU) ────────────────────────────────
_WGS84_A = 6_378_137.0           # 장반경 (m)
_WGS84_E2 = 6.694_379_990_14e-3  # 제1 이심률 제곱
_WGS84_B = _WGS84_A * math.sqrt(1.0 - _WGS84_E2)  # 단반경 (m)
_WGS84_EP2 = _WGS84_E2 / (1.0 - _WGS84_E2)        # 제2 이심률 제곱

# BlueSky .scn 모든 명령 앞에 붙는 시각 접두 (t=0 일괄 스폰).
_SCN_EPOCH = "00:00:00.00>"
# SDACS 전용 메타 주석 (BlueSky 는 '#' 시작 줄을 무시 → 왕복 시 ref/name 보존).
_SCN_META_REF = "# SDACS-REF"
_SCN_META_NAME = "# SDACS-SCENARIO"

# U-TRAFMAN 교환 포맷 버전.
_UTRAFMAN_FORMAT_VERSION = "1.0"


# ════════════════════════════════════════════════════════════════════════
#  좌표 변환 (측지 ↔ ENU). 자기완결 — 외부 패키지 의존 없음.
# ════════════════════════════════════════════════════════════════════════
def _geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> tuple[float, float, float]:
    """측지좌표 → ECEF(지구중심고정) 직교좌표."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    n = _WGS84_A / math.sqrt(1.0 - _WGS84_E2 * math.sin(lat) ** 2)
    x = (n + alt_m) * math.cos(lat) * math.cos(lon)
    y = (n + alt_m) * math.cos(lat) * math.sin(lon)
    z = (n * (1.0 - _WGS84_E2) + alt_m) * math.sin(lat)
    return x, y, z


def _ecef_to_geodetic(x: float, y: float, z: float) -> tuple[float, float, float]:
    """ECEF → 측지좌표 (Bowring 폐형해). 반복 없이 mm 정밀도."""
    p = math.hypot(x, y)
    if p == 0.0:  # 극점 특이 처리
        lat = math.copysign(math.pi / 2.0, z)
        return math.degrees(lat), 0.0, abs(z) - _WGS84_B
    theta = math.atan2(z * _WGS84_A, p * _WGS84_B)
    sin_t, cos_t = math.sin(theta), math.cos(theta)
    lat = math.atan2(
        z + _WGS84_EP2 * _WGS84_B * sin_t ** 3,
        p - _WGS84_E2 * _WGS84_A * cos_t ** 3,
    )
    lon = math.atan2(y, x)
    n = _WGS84_A / math.sqrt(1.0 - _WGS84_E2 * math.sin(lat) ** 2)
    # 고극 위도에서 cos(lat)→0 으로 ``p/cos`` 가 불안정 → 저위도는 cos, 고위도는 sin 분기.
    if abs(lat) < math.radians(45.0):
        alt = p / math.cos(lat) - n
    else:
        alt = z / math.sin(lat) - n * (1.0 - _WGS84_E2)
    return math.degrees(lat), math.degrees(lon), alt


def geodetic_to_enu(
    lat_deg: float, lon_deg: float, alt_m: float,
    ref_lat_deg: float, ref_lon_deg: float, ref_alt_m: float,
) -> tuple[float, float, float]:
    """측지좌표 → 기준점 기반 로컬 ENU (east, north, up) 미터."""
    ex, ey, ez = _geodetic_to_ecef(lat_deg, lon_deg, alt_m)
    rx, ry, rz = _geodetic_to_ecef(ref_lat_deg, ref_lon_deg, ref_alt_m)
    dx, dy, dz = ex - rx, ey - ry, ez - rz
    lat, lon = math.radians(ref_lat_deg), math.radians(ref_lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    east = -sin_lon * dx + cos_lon * dy
    north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    up = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    return east, north, up


def enu_to_geodetic(
    east: float, north: float, up: float,
    ref_lat_deg: float, ref_lon_deg: float, ref_alt_m: float,
) -> tuple[float, float, float]:
    """로컬 ENU (east, north, up) → 측지좌표. ``geodetic_to_enu`` 의 역변환."""
    lat, lon = math.radians(ref_lat_deg), math.radians(ref_lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    # ENU→ECEF 변위 (전방 회전행렬의 전치).
    dx = -sin_lon * east - sin_lat * cos_lon * north + cos_lat * cos_lon * up
    dy = cos_lon * east - sin_lat * sin_lon * north + cos_lat * sin_lon * up
    dz = cos_lat * north + sin_lat * up
    rx, ry, rz = _geodetic_to_ecef(ref_lat_deg, ref_lon_deg, ref_alt_m)
    return _ecef_to_geodetic(rx + dx, ry + dy, rz + dz)


# ════════════════════════════════════════════════════════════════════════
#  정규 표현 (측지 기반, SI 단위)
# ════════════════════════════════════════════════════════════════════════
def _check_finite(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} 는 실수여야 합니다: {value!r}")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"{name} 는 유한값이어야 합니다: {f!r}")
    return f


def _require_keys(mapping: Any, keys: tuple[str, ...], context: str) -> None:
    """``mapping`` 에 필수 키가 모두 있는지 확인 — 없으면 ValueError(경계 fail-fast)."""
    if not isinstance(mapping, dict):
        raise ValueError(f"{context} 는 객체여야 합니다: {mapping!r}")
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ValueError(f"{context} 에 필수 키가 없습니다: {missing}")


def _check_lat(lat: float) -> float:
    lat = _check_finite(lat, "lat_deg")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat_deg 범위 초과 [-90, 90]: {lat}")
    return lat


def _check_lon(lon: float) -> float:
    lon = _check_finite(lon, "lon_deg")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon_deg 범위 초과 [-180, 180]: {lon}")
    return lon


@dataclass(frozen=True)
class Waypoint:
    """경로점 (측지좌표, SI)."""

    lat_deg: float
    lon_deg: float
    alt_m: float
    spd_mps: float | None = None  # 레그별 속도(선택). None → 항공기 순항속도 유지.

    def __post_init__(self) -> None:
        object.__setattr__(self, "lat_deg", _check_lat(self.lat_deg))
        object.__setattr__(self, "lon_deg", _check_lon(self.lon_deg))
        object.__setattr__(self, "alt_m", _check_finite(self.alt_m, "alt_m"))
        if self.spd_mps is not None:
            spd = _check_finite(self.spd_mps, "spd_mps")
            if spd < 0.0:
                raise ValueError(f"spd_mps 는 음수일 수 없습니다: {spd}")
            object.__setattr__(self, "spd_mps", spd)


@dataclass(frozen=True)
class Aircraft:
    """단일 항공기(드론) 스폰 상태 + 경로."""

    acid: str           # 호출부호/식별자 (BlueSky CRE 첫 인자)
    actype: str         # 기종 (BlueSky 항공기 성능 모델명, 예: M600)
    lat_deg: float
    lon_deg: float
    alt_m: float
    hdg_deg: float      # 기수방위 [0, 360)
    spd_mps: float      # 순항속도 (CAS 근사)
    waypoints: tuple[Waypoint, ...] = ()

    def __post_init__(self) -> None:
        if not self.acid or not str(self.acid).strip():
            raise ValueError("acid 는 비어 있을 수 없습니다")
        if not self.actype or not str(self.actype).strip():
            raise ValueError("actype 는 비어 있을 수 없습니다")
        object.__setattr__(self, "lat_deg", _check_lat(self.lat_deg))
        object.__setattr__(self, "lon_deg", _check_lon(self.lon_deg))
        object.__setattr__(self, "alt_m", _check_finite(self.alt_m, "alt_m"))
        hdg = _check_finite(self.hdg_deg, "hdg_deg") % 360.0
        object.__setattr__(self, "hdg_deg", hdg)
        spd = _check_finite(self.spd_mps, "spd_mps")
        if spd < 0.0:
            raise ValueError(f"spd_mps 는 음수일 수 없습니다: {spd}")
        object.__setattr__(self, "spd_mps", spd)
        object.__setattr__(self, "waypoints", tuple(self.waypoints))


@dataclass(frozen=True)
class AdapterScenario:
    """외부 시뮬레이터 변환을 위한 SDACS 정규 시나리오."""

    name: str
    ref_lat_deg: float       # ENU 브리지용 기준 원점
    ref_lon_deg: float
    ref_alt_m: float
    aircraft: tuple[Aircraft, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name or not str(self.name).strip():
            raise ValueError("name 은 비어 있을 수 없습니다")
        object.__setattr__(self, "ref_lat_deg", _check_lat(self.ref_lat_deg))
        object.__setattr__(self, "ref_lon_deg", _check_lon(self.ref_lon_deg))
        object.__setattr__(self, "ref_alt_m", _check_finite(self.ref_alt_m, "ref_alt_m"))
        object.__setattr__(self, "aircraft", tuple(self.aircraft))
        ids = [a.acid for a in self.aircraft]
        if len(ids) != len(set(ids)):
            raise ValueError("acid 가 중복되었습니다")


# ════════════════════════════════════════════════════════════════════════
#  BlueSky .scn  ⇄  AdapterScenario
# ════════════════════════════════════════════════════════════════════════
def _fmt(value: float, decimals: int) -> str:
    """결정적 고정소수 포맷 (음수 0 정규화)."""
    s = f"{value:.{decimals}f}"
    return "0." + "0" * decimals if s.startswith("-0.") and float(s) == 0.0 else s


def to_bluesky_scn(scenario: AdapterScenario) -> str:
    """정규 시나리오 → BlueSky ``.scn`` 명령 스택 텍스트.

    각 항공기는 ``CRE`` 로 스폰하고 경로점은 ``ADDWPT`` 로 추가한다.
    BlueSky 관용 단위(고도 ft·속도 kt·기수 deg)로 변환해 출력한다.
    SDACS 기준점·시나리오명은 '#' 메타 주석으로 보존한다(왕복 가능).
    """
    lines = [
        f"{_SCN_META_NAME} {scenario.name}",
        f"{_SCN_META_REF} {_fmt(scenario.ref_lat_deg, 8)} "
        f"{_fmt(scenario.ref_lon_deg, 8)} {_fmt(scenario.ref_alt_m, 3)}",
    ]
    for ac in scenario.aircraft:
        alt_ft = ac.alt_m * _FT_PER_M
        spd_kt = ac.spd_mps * _KT_PER_MPS
        lines.append(
            f"{_SCN_EPOCH}CRE {ac.acid},{ac.actype},"
            f"{_fmt(ac.lat_deg, 8)},{_fmt(ac.lon_deg, 8)},"
            f"{_fmt(ac.hdg_deg, 4)},{_fmt(alt_ft, 4)},{_fmt(spd_kt, 4)}"
        )
        for wp in ac.waypoints:
            wp_alt_ft = wp.alt_m * _FT_PER_M
            cmd = (
                f"{_SCN_EPOCH}ADDWPT {ac.acid},"
                f"{_fmt(wp.lat_deg, 8)},{_fmt(wp.lon_deg, 8)},{_fmt(wp_alt_ft, 4)}"
            )
            if wp.spd_mps is not None:
                cmd += f",{_fmt(wp.spd_mps * _KT_PER_MPS, 4)}"
            lines.append(cmd)
    return "\n".join(lines) + "\n"


def _split_scn_command(rest: str) -> tuple[str, list[str]]:
    """'CMD arg1,arg2,...' → (CMD, [args]). BlueSky 는 쉼표/공백 혼용 허용."""
    rest = rest.strip()
    head, _, tail = rest.partition(" ")
    verb = head.strip().upper()
    args = [a.strip() for a in tail.replace(" ", ",").split(",") if a.strip()]
    return verb, args


def from_bluesky_scn(text: str) -> AdapterScenario:
    """BlueSky ``.scn`` 텍스트 → 정규 시나리오.

    ``CRE``/``ADDWPT`` 명령과 SDACS 메타 주석을 파싱한다. 기준점·시나리오명
    메타가 없으면 각각 (0,0,0)·``"imported"`` 로 채운다(측지 정규형은 메타에
    무관하게 보존됨).
    """
    name = "imported"
    ref = (0.0, 0.0, 0.0)
    builders: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(_SCN_META_NAME):
            name = line[len(_SCN_META_NAME):].strip() or name
            continue
        if line.startswith(_SCN_META_REF):
            parts = line[len(_SCN_META_REF):].split()
            if len(parts) >= 3:
                ref = (float(parts[0]), float(parts[1]), float(parts[2]))
            continue
        if line.startswith("#"):
            continue
        body = line.split(">", 1)[1] if ">" in line else line
        verb, args = _split_scn_command(body)
        if verb == "CRE":
            if len(args) < 7:
                raise ValueError(f"CRE 인자 부족(7개 필요): {line}")
            acid = args[0]
            if acid in builders:
                raise ValueError(f"CRE acid 중복: {acid!r}")
            builders[acid] = {
                "acid": acid,
                "actype": args[1],
                "lat_deg": float(args[2]),
                "lon_deg": float(args[3]),
                "hdg_deg": float(args[4]),
                "alt_m": float(args[5]) * _M_PER_FT,
                "spd_mps": float(args[6]) * _MPS_PER_KT,
                "waypoints": [],
            }
            if acid not in order:
                order.append(acid)
        elif verb == "ADDWPT":
            if len(args) < 4:
                raise ValueError(f"ADDWPT 인자 부족(acid+lat+lon+alt 4개 필요): {line}")
            acid = args[0]
            if acid not in builders:
                raise ValueError(f"ADDWPT 대상 항공기 미정의: {acid}")
            spd = float(args[4]) * _MPS_PER_KT if len(args) >= 5 else None
            builders[acid]["waypoints"].append(
                Waypoint(float(args[1]), float(args[2]), float(args[3]) * _M_PER_FT, spd)
            )
        # 그 외 명령(DEST 등)은 정규 표현에 영향 없어 무시한다.

    aircraft = tuple(
        Aircraft(
            acid=b["acid"], actype=b["actype"],
            lat_deg=b["lat_deg"], lon_deg=b["lon_deg"], alt_m=b["alt_m"],
            hdg_deg=b["hdg_deg"], spd_mps=b["spd_mps"],
            waypoints=tuple(b["waypoints"]),
        )
        for b in (builders[a] for a in order)
    )
    return AdapterScenario(name, ref[0], ref[1], ref[2], aircraft)


# ════════════════════════════════════════════════════════════════════════
#  U-TRAFMAN JSON  ⇄  AdapterScenario
# ════════════════════════════════════════════════════════════════════════
def to_utrafman_dict(scenario: AdapterScenario) -> dict[str, Any]:
    """정규 시나리오 → U-TRAFMAN-호환 교환 딕셔너리 (SI 단위 유지)."""
    operations = []
    for ac in scenario.aircraft:
        plan = [
            {
                "lat": ac.lat_deg, "lon": ac.lon_deg, "alt_m": ac.alt_m,
                "spd_mps": ac.spd_mps,
            }
        ]
        for wp in ac.waypoints:
            leg = {"lat": wp.lat_deg, "lon": wp.lon_deg, "alt_m": wp.alt_m}
            if wp.spd_mps is not None:
                leg["spd_mps"] = wp.spd_mps
            plan.append(leg)
        operations.append({
            "uav_id": ac.acid,
            "uav_type": ac.actype,
            "heading_deg": ac.hdg_deg,
            "cruise_spd_mps": ac.spd_mps,
            "flight_plan": plan,
        })
    return {
        "format": "utrafman-compat",
        "format_version": _UTRAFMAN_FORMAT_VERSION,
        "scenario": scenario.name,
        "reference": {
            "lat": scenario.ref_lat_deg,
            "lon": scenario.ref_lon_deg,
            "alt_m": scenario.ref_alt_m,
        },
        "operations": operations,
    }


def to_utrafman_json(scenario: AdapterScenario, *, indent: int | None = 2) -> str:
    """정규 시나리오 → U-TRAFMAN-호환 JSON 문자열 (결정적·키 정렬)."""
    return json.dumps(
        to_utrafman_dict(scenario), indent=indent, sort_keys=True, ensure_ascii=False
    )


def from_utrafman_dict(data: dict[str, Any]) -> AdapterScenario:
    """U-TRAFMAN-호환 딕셔너리 → 정규 시나리오."""
    if not isinstance(data, dict):
        raise TypeError("최상위는 객체(dict)여야 합니다")
    if data.get("format") != "utrafman-compat":
        raise ValueError(f"format 이 'utrafman-compat' 가 아닙니다: {data.get('format')!r}")
    ref = data.get("reference") or {}
    ops = data.get("operations")
    if not isinstance(ops, list):
        raise ValueError("operations 는 리스트여야 합니다")

    aircraft = []
    for op in ops:
        if not isinstance(op, dict):
            raise ValueError(f"operations 항목은 객체여야 합니다: {op!r}")
        _require_keys(op, ("uav_id", "uav_type", "heading_deg", "cruise_spd_mps"), "operations 항목")
        plan = op.get("flight_plan") or []
        if not plan:
            raise ValueError(f"flight_plan 이 비어 있습니다: uav_id={op.get('uav_id')!r}")
        for leg in plan:
            _require_keys(leg, ("lat", "lon", "alt_m"), "flight_plan leg")
        spawn = plan[0]
        waypoints = tuple(
            # spawn["spd_mps"] 는 의도적으로 미사용 — 스폰 속도는 cruise_spd_mps 가 정본.
            Waypoint(leg["lat"], leg["lon"], leg["alt_m"], leg.get("spd_mps"))
            for leg in plan[1:]
        )
        aircraft.append(Aircraft(
            acid=op["uav_id"], actype=op["uav_type"],
            lat_deg=spawn["lat"], lon_deg=spawn["lon"], alt_m=spawn["alt_m"],
            hdg_deg=op["heading_deg"], spd_mps=op["cruise_spd_mps"],
            waypoints=waypoints,
        ))
    return AdapterScenario(
        name=str(data.get("scenario", "imported")),
        ref_lat_deg=float(ref.get("lat", 0.0)),
        ref_lon_deg=float(ref.get("lon", 0.0)),
        ref_alt_m=float(ref.get("alt_m", 0.0)),
        aircraft=tuple(aircraft),
    )


def from_utrafman_json(text: str) -> AdapterScenario:
    """U-TRAFMAN-호환 JSON 문자열 → 정규 시나리오."""
    return from_utrafman_dict(json.loads(text))


# ════════════════════════════════════════════════════════════════════════
#  SDACS ENU 브리지
# ════════════════════════════════════════════════════════════════════════
def scenario_to_enu(scenario: AdapterScenario) -> list[dict[str, Any]]:
    """정규 시나리오 → SDACS 로컬 ENU 상태 목록 (시나리오 기준점 기준)."""
    out = []
    for ac in scenario.aircraft:
        e, n, u = geodetic_to_enu(
            ac.lat_deg, ac.lon_deg, ac.alt_m,
            scenario.ref_lat_deg, scenario.ref_lon_deg, scenario.ref_alt_m,
        )
        out.append({
            "acid": ac.acid, "actype": ac.actype,
            "east_m": e, "north_m": n, "up_m": u,
            "hdg_deg": ac.hdg_deg, "spd_mps": ac.spd_mps,
        })
    return out


# ════════════════════════════════════════════════════════════════════════
#  데모 / CLI
# ════════════════════════════════════════════════════════════════════════
def _demo_scenario() -> AdapterScenario:
    """목포 해역 인근 2기 데모 시나리오 (결정적)."""
    return AdapterScenario(
        name="demo_mokpo",
        ref_lat_deg=34.7936, ref_lon_deg=126.3886, ref_alt_m=0.0,
        aircraft=(
            Aircraft(
                acid="SD001", actype="M600", lat_deg=34.7936, lon_deg=126.3886,
                alt_m=80.0, hdg_deg=90.0, spd_mps=12.0,
                waypoints=(
                    Waypoint(34.7950, 126.3920, 80.0),
                    Waypoint(34.7970, 126.3950, 100.0, spd_mps=8.0),
                ),
            ),
            Aircraft(
                acid="SD002", actype="M300", lat_deg=34.7900, lon_deg=126.3850,
                alt_m=60.0, hdg_deg=270.0, spd_mps=10.0,
                waypoints=(Waypoint(34.7880, 126.3820, 60.0),),
            ),
        ),
    )


def _aircraft_match(a: Aircraft, b: Aircraft) -> bool:
    """두 항공기가 왕복 허용오차 내에서 일치하는가 (전 필드·경로점 포함)."""
    if a.acid != b.acid or a.actype != b.actype:
        return False
    if abs(a.lat_deg - b.lat_deg) > 1e-6 or abs(a.lon_deg - b.lon_deg) > 1e-6:
        return False
    if abs(a.alt_m - b.alt_m) > 1e-2 or abs(a.spd_mps - b.spd_mps) > 1e-2:
        return False
    if abs((a.hdg_deg - b.hdg_deg + 180.0) % 360.0 - 180.0) > 1e-3:
        return False
    if len(a.waypoints) != len(b.waypoints):
        return False
    for wa, wb in zip(a.waypoints, b.waypoints, strict=False):
        if abs(wa.lat_deg - wb.lat_deg) > 1e-6 or abs(wa.lon_deg - wb.lon_deg) > 1e-6 \
           or abs(wa.alt_m - wb.alt_m) > 1e-2:
            return False
    return True


def _self_test() -> bool:
    """왕복 항등 자가 점검 (BlueSky·U-TRAFMAN, 전 필드·경로점 비교)."""
    sc = _demo_scenario()
    bsky = from_bluesky_scn(to_bluesky_scn(sc))
    utm = from_utrafman_json(to_utrafman_json(sc))
    ok = True
    for tag, rt in (("bluesky", bsky), ("utrafman", utm)):
        if len(rt.aircraft) != len(sc.aircraft):
            print(f"[FAIL] {tag}: 항공기 수 불일치")
            ok = False
            continue
        for a, b in zip(sc.aircraft, rt.aircraft, strict=False):
            if not _aircraft_match(a, b):
                print(f"[FAIL] {tag}: {a.acid} 왕복 불일치")
                ok = False
    print("[OK] 왕복 항등 통과" if ok else "[FAIL] 왕복 항등 실패")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SDACS 외부 시뮬레이터 어댑터 (Phase 323)")
    parser.add_argument("--demo", action="store_true", help="데모 시나리오 변환 출력")
    parser.add_argument(
        "--format", choices=("bluesky", "utrafman", "both"), default="both",
        help="출력 포맷",
    )
    parser.add_argument("--self-test", action="store_true", help="왕복 항등 자가 점검")
    args = parser.parse_args(argv)

    if args.self_test:
        return 0 if _self_test() else 1

    if args.demo:
        sc = _demo_scenario()
        if args.format in ("bluesky", "both"):
            print("# ── BlueSky .scn ──")
            print(to_bluesky_scn(sc), end="")
        if args.format in ("utrafman", "both"):
            print("# ── U-TRAFMAN JSON ──")
            print(to_utrafman_json(sc))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
