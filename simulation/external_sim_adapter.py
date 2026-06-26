"""
외부 시뮬레이터 어댑터 (GENESIS Phase 323)
==========================================
SDACS 시나리오 ↔ 공개 ATM/UTM 시뮬레이터(BlueSky·U-TRAFMAN) **호환 import/export**.

배경 — Phase 405 와의 분담
--------------------------
``benchmark_comparison`` (ODYSSEY Phase 405) 은 BlueSky·U-TRAFMAN 과 SDACS 의
**기능 범위**를 동일 축으로 정렬·비교한다(서술 기반). 본 모듈은 그 위에서 한 발
더 나아가 **실 시나리오 데이터를 양방향 변환**한다: SDACS 의 통계형 시나리오
(``config/scenario_params/*.yaml``) 를 BlueSky ``.scn`` 스택 명령 / U-TRAFMAN
비행계획 JSON 으로 내보내고, 그 역으로 다시 읽어들인다.

중립 교환 모델(IR)
------------------
포맷마다 직접 N×M 변환기를 두지 않고 단일 중립 표현 ``ScenarioExchange`` 을
경유한다. 각 포맷은 IR ↔ 자기 포맷 변환기 1쌍만 제공하면 된다.

    SDACS yaml ──┐                        ┌── BlueSky .scn
                 ├── ScenarioExchange ──┤
    BlueSky .scn ─┘   (lat/lon·항공기)    └── U-TRAFMAN JSON

좌표 정직성(maturity honesty)
-----------------------------
SDACS 시나리오는 면적(``area_km2``)·도착률 기반 **통계형**이라 항공기별 위경도가
없다. 본 어댑터는 기준 원점(기본 목포항 권역 34.79N/126.39E)을 중심으로 한 정사각
영역에 ``np.random.default_rng(seed)`` 로 **결정적**으로 항공기를 물질화(materialize)
한다. 등거리 직사각 투영(equirectangular)으로 로컬 km → 위경도 변환하며, 실 측량
좌표가 아니다. BlueSky/U-TRAFMAN 포맷 규약은 공개 문서·논문 기술 기반이다.

새 의존성 없이 동작한다 — 결정적·오프라인.

CLI::

    python simulation/external_sim_adapter.py --to-bluesky config/scenario_params/high_density.yaml
    python simulation/external_sim_adapter.py --to-utrafman config/scenario_params/high_density.yaml
    python simulation/external_sim_adapter.py --from-bluesky out.scn
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# 기준 원점 — 목포항 권역 중심 근사 (mokpo_harbor.py 권역 박스 중심)
DEFAULT_REF_LAT = 34.79
DEFAULT_REF_LON = 126.39

# 등거리 투영 상수 — 위도 1도 ≈ 111.32 km
_KM_PER_DEG_LAT = 111.32

# 기본 운항 파라미터 (SDACS 통계형 시나리오엔 항공기별 값이 없어 결정적 기본값 적용)
_DEFAULT_ALT_M = 100.0
_DEFAULT_SPD_MS = 15.0
_DEFAULT_TYPE = "MULTIROTOR"

# 단위 변환 (BlueSky 는 피트·노트 사용)
_M_TO_FT = 3.280839895
_MS_TO_KT = 1.943844492

# BlueSky 시나리오 시각 프리픽스 (즉시 생성)
_SCN_T0 = "00:00:00.00>"


# ──────────────────────────────────────────────────────────────────────────
# 중립 교환 모델 (IR)
# ──────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ExchangeAircraft:
    """단일 항공기 — 출발 상태 + 목적지."""

    acid: str
    type_code: str
    lat: float
    lon: float
    hdg_deg: float
    alt_m: float
    spd_ms: float
    dest_lat: float
    dest_lon: float


@dataclass(frozen=True)
class ScenarioExchange:
    """포맷 중립 시나리오 교환 표현."""

    name: str
    description: str
    duration_s: float
    ref_lat: float
    ref_lon: float
    area_km2: float
    aircraft: tuple[ExchangeAircraft, ...] = field(default_factory=tuple)


# ──────────────────────────────────────────────────────────────────────────
# 로컬 km ↔ 위경도 (등거리 직사각 투영)
# ──────────────────────────────────────────────────────────────────────────
def local_km_to_latlon(x_km: float, y_km: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    """원점 기준 동쪽 x_km·북쪽 y_km 오프셋 → (lat, lon)."""
    dlat = y_km / _KM_PER_DEG_LAT
    dlon = x_km / (_KM_PER_DEG_LAT * math.cos(math.radians(ref_lat)))
    return ref_lat + dlat, ref_lon + dlon


def latlon_to_local_km(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    """(lat, lon) → 원점 기준 (x_km 동, y_km 북)."""
    y_km = (lat - ref_lat) * _KM_PER_DEG_LAT
    x_km = (lon - ref_lon) * _KM_PER_DEG_LAT * math.cos(math.radians(ref_lat))
    return x_km, y_km


def _bearing_deg(x0: float, y0: float, x1: float, y1: float) -> float:
    """(x0,y0)→(x1,y1) 방위각(도, 북=0, 시계방향). 동일점이면 0."""
    dx, dy = x1 - x0, y1 - y0
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return math.degrees(math.atan2(dx, dy)) % 360.0


# ──────────────────────────────────────────────────────────────────────────
# SDACS 시나리오 → IR (결정적 물질화)
# ──────────────────────────────────────────────────────────────────────────
def _read_drone_count(scenario: dict[str, Any]) -> int:
    """러너 관용 키에서 드론 수 추출 (scenario_migration 규약과 정렬)."""
    for key in ("drone_count", "base_drone_count", "total_drone_count"):
        if key in scenario and scenario[key]:
            val = int(scenario[key])
            if val > 0:
                return val
    base = scenario.get("base_traffic")
    if isinstance(base, dict) and base.get("drone_count"):
        return int(base["drone_count"])
    return 0


def _read_duration_s(scenario: dict[str, Any]) -> float:
    """시뮬 시간(초) 추출 — 초 우선, 없으면 분→초."""
    if scenario.get("simulation_duration_s"):
        return float(scenario["simulation_duration_s"])
    if scenario.get("simulation_duration_min"):
        return float(scenario["simulation_duration_min"]) * 60.0
    return 0.0


def sdacs_to_exchange(
    scenario: dict[str, Any],
    *,
    ref_lat: float = DEFAULT_REF_LAT,
    ref_lon: float = DEFAULT_REF_LON,
    seed: int = 0,
) -> ScenarioExchange:
    """SDACS 통계형 시나리오 → 결정적 항공기 집합 IR.

    면적 정사각 영역(``area_km2``)에 ``seed`` 결정적으로 출발/목적지를 배치한다.
    같은 (scenario, seed) 는 항상 동일 결과(재현성).
    """
    count = _read_drone_count(scenario)
    area_km2 = float(scenario.get("area_km2", 0.0) or 0.0)
    half = math.sqrt(area_km2) / 2.0 if area_km2 > 0 else 5.0
    rng = np.random.default_rng(seed)

    # 프로파일 분포 → 결정적 타입 라벨 시퀀스
    dist = scenario.get("drone_profile_distribution") or {}
    type_codes = _materialize_types(dist, count, rng)

    aircraft: list[ExchangeAircraft] = []
    for i in range(count):
        ox, oy = rng.uniform(-half, half), rng.uniform(-half, half)
        dx, dy = rng.uniform(-half, half), rng.uniform(-half, half)
        olat, olon = local_km_to_latlon(ox, oy, ref_lat, ref_lon)
        dlat, dlon = local_km_to_latlon(dx, dy, ref_lat, ref_lon)
        aircraft.append(
            ExchangeAircraft(
                acid=f"SD{i:04d}",
                type_code=type_codes[i],
                lat=olat,
                lon=olon,
                hdg_deg=_bearing_deg(ox, oy, dx, dy),
                alt_m=_DEFAULT_ALT_M,
                spd_ms=_DEFAULT_SPD_MS,
                dest_lat=dlat,
                dest_lon=dlon,
            )
        )

    return ScenarioExchange(
        name=str(scenario.get("scenario", "sdacs_scenario")),
        description=str(scenario.get("description", "")),
        duration_s=_read_duration_s(scenario),
        ref_lat=ref_lat,
        ref_lon=ref_lon,
        area_km2=area_km2,
        aircraft=tuple(aircraft),
    )


def _materialize_types(dist: dict[str, float], count: int, rng: np.random.Generator) -> list[str]:
    """프로파일 분포를 count 개 결정적 타입 라벨로 전개."""
    if not dist or count == 0:
        return [_DEFAULT_TYPE] * count
    labels = sorted(dist)  # 결정적 순서
    weights = np.array([float(dist[k]) for k in labels], dtype=float)
    total = weights.sum()
    if total <= 0:
        return [_DEFAULT_TYPE] * count
    idx = rng.choice(len(labels), size=count, p=weights / total)
    return [labels[int(j)] for j in idx]


# ──────────────────────────────────────────────────────────────────────────
# IR → SDACS 시나리오 (스키마 호환 dict)
# ──────────────────────────────────────────────────────────────────────────
def exchange_to_sdacs(ex: ScenarioExchange) -> dict[str, Any]:
    """IR → SDACS 시나리오 dict (``scenario_schema.validate_scenario`` 계약 만족).

    스키마는 양수 ``drone_count`` 를 요구한다. 항공기 0대 IR 은 유효 시나리오를
    만들 수 없으므로 잘못된 출력을 내보내는 대신 명시적으로 거부한다.
    """
    if not ex.aircraft:
        raise ValueError("cannot build a valid SDACS scenario from an empty exchange (0 aircraft)")
    scenario: dict[str, Any] = {
        "scenario": ex.name,
        "description": ex.description or f"imported from external simulator ({len(ex.aircraft)} aircraft)",
        "schema_version": "2.0",
        "drone_count": len(ex.aircraft),
        "simulation_duration_s": ex.duration_s if ex.duration_s > 0 else 600.0,
        "area_km2": ex.area_km2 if ex.area_km2 > 0 else 100.0,
        "route_generation": {"type": "explicit_od"},
        "success_criteria": {"collision_count": 0},
    }
    return scenario


# ──────────────────────────────────────────────────────────────────────────
# IR ↔ BlueSky .scn
# ──────────────────────────────────────────────────────────────────────────
def exchange_to_bluesky(ex: ScenarioExchange) -> str:
    """IR → BlueSky ``.scn`` 스택 명령 텍스트.

    BlueSky 규약(Hoekstra & Ellerbroek, ICRAT 2016): 시각 프리픽스
    ``HH:MM:SS.ss>`` + ``CRE acid,type,lat,lon,hdg,alt_ft,spd_kt`` + ``DEST``.
    고도는 피트, 속도는 노트로 변환한다.
    """
    lines: list[str] = [
        f"# SDACS export → BlueSky scenario: {ex.name}",
        f"# {ex.description}",
        f"# ref_origin={ex.ref_lat:.5f},{ex.ref_lon:.5f} area_km2={ex.area_km2:g} aircraft={len(ex.aircraft)}",
    ]
    # 정밀도 안내: 고도 .1f(ft)·속도 .2f(kt) 직렬화는 왕복 시 미세 드리프트를
    # 남긴다(100 m→100.005 m, 15 m/s→15.001 m/s). 포맷 호환 우선의 의도된 손실.
    for ac in ex.aircraft:
        alt_ft = ac.alt_m * _M_TO_FT
        spd_kt = ac.spd_ms * _MS_TO_KT
        lines.append(
            f"{_SCN_T0}CRE {ac.acid},{ac.type_code},"
            f"{ac.lat:.6f},{ac.lon:.6f},{ac.hdg_deg:.2f},{alt_ft:.1f},{spd_kt:.2f}"
        )
        lines.append(f"{_SCN_T0}DEST {ac.acid},{ac.dest_lat:.6f},{ac.dest_lon:.6f}")
    return "\n".join(lines) + "\n"


def bluesky_to_exchange(
    scn_text: str,
    *,
    name: str = "bluesky_import",
    description: str = "",
    ref_lat: float = DEFAULT_REF_LAT,
    ref_lon: float = DEFAULT_REF_LON,
    duration_s: float = 600.0,
    area_km2: float = 0.0,
) -> ScenarioExchange:
    """BlueSky ``.scn`` 텍스트 → IR. ``CRE``/``DEST`` 명령만 해석한다."""
    cres: dict[str, dict[str, Any]] = {}
    dests: dict[str, tuple[float, float]] = {}
    for raw in scn_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        body = line.split(">", 1)[1].strip() if ">" in line else line
        parts = body.split(None, 1)
        if len(parts) < 2:
            continue
        cmd, args = parts[0].upper(), parts[1]
        fields = [f.strip() for f in args.split(",")]
        # 외부/손상 파일 방어 — 숫자 파싱 실패 라인은 조용히 건너뛴다(경계 검증).
        try:
            if cmd == "CRE" and len(fields) >= 7:
                entry = {
                    "type_code": fields[1],
                    "lat": float(fields[2]),
                    "lon": float(fields[3]),
                    "hdg_deg": float(fields[4]),
                    "alt_m": float(fields[5]) / _M_TO_FT,
                    "spd_ms": float(fields[6]) / _MS_TO_KT,
                }
            elif cmd == "DEST" and len(fields) >= 3:
                dests[fields[0]] = (float(fields[1]), float(fields[2]))
                continue
            else:
                continue
        except ValueError:
            continue
        # 파싱 성공한 CRE 만 도달 — 중복 ACID 는 조용한 항공기 유실 방지를 위해 명시적 오류.
        if fields[0] in cres:
            raise ValueError(f"duplicate ACID '{fields[0]}' in .scn file")
        cres[fields[0]] = entry

    aircraft: list[ExchangeAircraft] = []
    for acid in cres:  # CRE 등장 순서 보존
        c = cres[acid]
        dlat, dlon = dests.get(acid, (c["lat"], c["lon"]))
        aircraft.append(
            ExchangeAircraft(
                acid=acid,
                type_code=c["type_code"],
                lat=c["lat"],
                lon=c["lon"],
                hdg_deg=c["hdg_deg"],
                alt_m=c["alt_m"],
                spd_ms=c["spd_ms"],
                dest_lat=dlat,
                dest_lon=dlon,
            )
        )
    return ScenarioExchange(
        name=name,
        description=description,
        duration_s=duration_s,
        ref_lat=ref_lat,
        ref_lon=ref_lon,
        area_km2=area_km2,
        aircraft=tuple(aircraft),
    )


# ──────────────────────────────────────────────────────────────────────────
# IR ↔ U-TRAFMAN 비행계획 JSON
# ──────────────────────────────────────────────────────────────────────────
def exchange_to_utrafman(ex: ScenarioExchange) -> dict[str, Any]:
    """IR → U-TRAFMAN 호환 비행계획 JSON(dict).

    U-TRAFMAN 은 UAS 비행계획(flight plan) 중심 UTM 시뮬레이터다. 출발/목적지·
    순항 고도·속도를 비행계획 레코드로 표현한다(공개 문서 기반 호환 포맷).
    """
    flight_plans = [
        {
            "flight_id": ac.acid,
            "aircraft_type": ac.type_code,
            "origin": [round(ac.lat, 6), round(ac.lon, 6)],
            "destination": [round(ac.dest_lat, 6), round(ac.dest_lon, 6)],
            "cruise_alt_m": ac.alt_m,
            "cruise_speed_ms": ac.spd_ms,
            "departure_s": 0.0,
        }
        for ac in ex.aircraft
    ]
    return {
        "format": "u-trafman/flight-plan",
        "version": "1.0",
        "scenario": ex.name,
        "description": ex.description,
        "reference_origin": [ex.ref_lat, ex.ref_lon],
        "area_km2": ex.area_km2,
        "duration_s": ex.duration_s,
        "flight_plans": flight_plans,
    }


def _require_coord(value: Any, label: str) -> tuple[float, float]:
    """외부 좌표 경계 검증 — 2원소 [lat, lon] 리스트만 허용(IndexError 차단)."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise ValueError(f"{label} must be a 2-element [lat, lon] list, got: {value!r}")
    return float(value[0]), float(value[1])


def utrafman_to_exchange(doc: dict[str, Any]) -> ScenarioExchange:
    """U-TRAFMAN 비행계획 JSON(dict) → IR."""
    ref = doc.get("reference_origin", [DEFAULT_REF_LAT, DEFAULT_REF_LON])
    ref_lat, ref_lon = _require_coord(ref, "reference_origin")
    aircraft: list[ExchangeAircraft] = []
    for fp in doc.get("flight_plans", []):
        # 외부 비행계획 경계 검증 — 출발/목적지 누락은 명시적 오류로 표면화.
        if "origin" not in fp or "destination" not in fp:
            raise ValueError(
                f"flight plan {fp.get('flight_id', '?')} missing origin/destination"
            )
        fid = fp.get("flight_id", "?")
        o = _require_coord(fp["origin"], f"flight plan {fid} origin")
        d = _require_coord(fp["destination"], f"flight plan {fid} destination")
        ox, oy = latlon_to_local_km(float(o[0]), float(o[1]), ref_lat, ref_lon)
        dx, dy = latlon_to_local_km(float(d[0]), float(d[1]), ref_lat, ref_lon)
        aircraft.append(
            ExchangeAircraft(
                acid=str(fp["flight_id"]),
                type_code=str(fp.get("aircraft_type", _DEFAULT_TYPE)),
                lat=float(o[0]),
                lon=float(o[1]),
                hdg_deg=_bearing_deg(ox, oy, dx, dy),
                alt_m=float(fp.get("cruise_alt_m", _DEFAULT_ALT_M)),
                spd_ms=float(fp.get("cruise_speed_ms", _DEFAULT_SPD_MS)),
                dest_lat=float(d[0]),
                dest_lon=float(d[1]),
            )
        )
    return ScenarioExchange(
        name=str(doc.get("scenario", "utrafman_import")),
        description=str(doc.get("description", "")),
        duration_s=float(doc.get("duration_s", 600.0) or 600.0),
        ref_lat=ref_lat,
        ref_lon=ref_lon,
        area_km2=float(doc.get("area_km2", 0.0) or 0.0),
        aircraft=tuple(aircraft),
    )


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────
def _load_scenario_yaml(path: str) -> dict[str, Any]:
    import yaml

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or args[0] not in {"--to-bluesky", "--to-utrafman", "--from-bluesky"}:
        print(__doc__)
        return 1
    mode, target = args[0], args[1]
    if mode == "--from-bluesky":
        ex = bluesky_to_exchange(Path(target).read_text(encoding="utf-8"))
        print(json.dumps(exchange_to_sdacs(ex), ensure_ascii=False, indent=2))
        return 0
    ex = sdacs_to_exchange(_load_scenario_yaml(target))
    if mode == "--to-bluesky":
        print(exchange_to_bluesky(ex), end="")
    else:
        print(json.dumps(exchange_to_utrafman(ex), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
