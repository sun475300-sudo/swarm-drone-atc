"""
비행승인 신청서(Drone One-Stop) 자동 생성 스크립트 — GENESIS Phase 303.

항공안전법 시행규칙 §306 / 별지 제122호서식(무인비행장치 비행승인신청서)의
기계 작성 가능 필드를 시뮬레이션 시나리오·기본 설정으로부터 결정적으로 생성한다.
운영자 인적사항(PII)은 placeholder("(운영자 기입)")로 남겨 수기 입력하도록 한다.

근거: 항공안전법 §127·§129, 동법 시행규칙 §306, 국토교통부 Drone One-Stop
(드론 원스톱 민원서비스) 비행승인 신청 항목.

실행:
  python scripts/generate_flight_plan.py --scenario high_density
  python scripts/generate_flight_plan.py --config config/default_simulation.yaml --format json
출력: reports/flight_plan_<name>.md / reports/flight_plan_<name>.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent

# 위경도 환산 상수 (평면근사 — 신청서 구역 좌표 산정용)
KM_PER_DEG_LAT = 111.32
PII_PLACEHOLDER = "(운영자 기입)"


@dataclass(frozen=True)
class GeoBox:
    """비행구역 경계 좌표 (WGS84, 평면근사)."""

    center_lat: float
    center_lon: float
    sw_lat: float
    sw_lon: float
    ne_lat: float
    ne_lon: float
    radius_km: float


@dataclass(frozen=True)
class FlightPlanForm:
    """별지 제122호서식 기계 작성 필드 + 운영자 수기 필드."""

    # 메타
    source: str
    generated_for: str
    legal_basis: str
    # 신청인 (수기)
    applicant_name: str
    applicant_contact: str
    # 비행장치 (시나리오 유도 + 일부 수기)
    aircraft_type: str
    aircraft_count: int
    aircraft_purpose: str
    registration_no: str
    # 비행계획 (시나리오 유도)
    flight_duration_min: float
    flight_mode: str
    max_altitude_m: float
    is_bvlos: bool
    is_night: bool
    # 비행구역 (시나리오 유도)
    area: GeoBox
    # 조종자 (수기)
    pilot_name: str
    pilot_license_no: str
    # 안전대책 (시스템 유도, 불변)
    safety_measures: tuple[str, ...] = field(default_factory=tuple)
    # 보험 (수기)
    insurance_policy_no: str = PII_PLACEHOLDER


def load_config(path: Path) -> dict:
    """YAML 설정 파일을 로드한다."""
    if not path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없음: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"설정 파일 형식 오류(dict 아님): {path}")
    return data


def _resolve_duration_min(config: dict) -> float:
    """설정에서 비행 시간(분)을 결정적으로 추출한다."""
    if "simulation_duration_min" in config:
        return float(config["simulation_duration_min"])
    if "simulation_duration_s" in config:
        return round(float(config["simulation_duration_s"]) / 60.0, 1)
    sim = config.get("simulation", {})
    if "duration_minutes" in sim:
        return float(sim["duration_minutes"])
    return 10.0


def _resolve_drone_count(config: dict) -> int:
    """설정에서 비행장치 대수를 추출한다 (시나리오 키 우선)."""
    for key in ("drone_count", "total_drone_count"):
        if key in config:
            return int(config[key])
    return int(config.get("drones", {}).get("default_count", 1))


def _resolve_max_altitude(config: dict) -> float:
    """최대 비행 고도(AGL, m)를 추출한다."""
    drones = config.get("drones", {})
    if "max_altitude_m" in drones:
        return float(drones["max_altitude_m"])
    z = config.get("airspace", {}).get("bounds_km", {}).get("z")
    if z and len(z) == 2 and float(z[1]) > 0:
        return round(float(z[1]) * 1000.0, 1)  # km → m
    return 120.0  # 설정에 고도 정보가 없을 때 항공안전법 기본 한계


def _area_half_extent_km(config: dict) -> float:
    """home 기준 운영 구역의 최대 반경 방향 거리(km)를 산정한다."""
    bounds = config.get("airspace", {}).get("bounds_km", {})
    x = bounds.get("x", [-0.5, 0.5])
    y = bounds.get("y", [-0.5, 0.5])
    return max(max(abs(v) for v in x), max(abs(v) for v in y))


def build_geobox(config: dict) -> GeoBox:
    """home 좌표 + 공역 경계(km)로 비행구역 좌표를 평면근사 산정한다."""
    airspace = config.get("airspace", {})
    home = airspace.get("home", {"lat": 35.1595, "lon": 126.8526})
    lat0, lon0 = float(home["lat"]), float(home["lon"])
    bounds = airspace.get("bounds_km", {"x": [-5.0, 5.0], "y": [-5.0, 5.0]})
    x_min, x_max = bounds.get("x", [-5.0, 5.0])
    y_min, y_max = bounds.get("y", [-5.0, 5.0])
    km_per_deg_lon = KM_PER_DEG_LAT * abs(_cos_deg(lat0))
    return GeoBox(
        center_lat=round(lat0, 6),
        center_lon=round(lon0, 6),
        sw_lat=round(lat0 + y_min / KM_PER_DEG_LAT, 6),
        sw_lon=round(lon0 + x_min / km_per_deg_lon, 6),
        ne_lat=round(lat0 + y_max / KM_PER_DEG_LAT, 6),
        ne_lon=round(lon0 + x_max / km_per_deg_lon, 6),
        # 운영 구역을 모두 포함하는 외접원 반경(half-diagonal) — 비행구역 과소신고 방지
        radius_km=round(math.hypot(x_max - x_min, y_max - y_min) / 2.0, 3),
    )


def _cos_deg(deg: float) -> float:
    """math.cos(라디안) 결정적 래퍼."""
    return math.cos(math.radians(deg))


def build_flight_plan(config: dict, name: str) -> FlightPlanForm:
    """설정 dict → 비행승인 신청서 양식(결정적)."""
    duration = _resolve_duration_min(config)
    count = _resolve_drone_count(config)
    max_alt = _resolve_max_altitude(config)
    # BVLOS 추론: 운영 구역이 home에서 0.5km(육안 식별 한계 근사)를 넘으면 비가시권으로 간주
    bvlos = bool(config.get("bvlos", _area_half_extent_km(config) > 0.5))
    night = bool(config.get("night", False))
    return FlightPlanForm(
        source=name,
        generated_for=str(config.get("scenario", name)),
        legal_basis="항공안전법 §127·§129, 시행규칙 §306 (Drone One-Stop)",
        applicant_name=PII_PLACEHOLDER,
        applicant_contact=PII_PLACEHOLDER,
        aircraft_type="무인멀티콥터(군집)",
        aircraft_count=count,
        aircraft_purpose=str(config.get("description", "군집 비행 실증")),
        registration_no=PII_PLACEHOLDER,
        flight_duration_min=duration,
        flight_mode="자동(군집 자율) + 관제사 감독",
        max_altitude_m=max_alt,
        is_bvlos=bvlos,
        is_night=night,
        area=build_geobox(config),
        pilot_name=PII_PLACEHOLDER,
        pilot_license_no=PII_PLACEHOLDER,
        safety_measures=(
            "5계층 안전망(APF·CBS·CPA·ATC·UTM) 상시 활성",
            f"수평 분리 {config.get('separation_standards', {}).get('lateral_min_m', 50.0)}m / "
            f"수직 분리 {config.get('separation_standards', {}).get('vertical_min_m', 15.0)}m 유지",
            "Remote ID 송출(ASTM F3411) 및 비행기록 보존",
            "배터리 임계 시 자동 RTB·비상착륙 프로토콜",
        ),
        insurance_policy_no=PII_PLACEHOLDER,
    )


def render_markdown(form: FlightPlanForm) -> str:
    """양식을 Markdown 신청서로 렌더링한다."""
    a = form.area
    bvlos = "예(특별승인 필요)" if form.is_bvlos else "아니오"
    night = "예(특별승인 필요)" if form.is_night else "아니오"
    measures = "\n".join(f"- {m}" for m in form.safety_measures)
    return f"""# 무인비행장치 비행승인 신청서 (자동 생성)

> 별지 제122호서식 기반 · 근거: {form.legal_basis}
> 생성 대상: `{form.source}` (시나리오: {form.generated_for})
> ⚠️ 인적사항·신고번호·자격번호·보험은 운영자가 직접 기입해야 한다. 본 문서는 참고용 초안이다.

## 1. 신청인
| 항목 | 값 |
|---|---|
| 성명/명칭 | {form.applicant_name} |
| 연락처 | {form.applicant_contact} |

## 2. 비행장치
| 항목 | 값 |
|---|---|
| 종류 | {form.aircraft_type} |
| 대수 | {form.aircraft_count} |
| 용도 | {form.aircraft_purpose} |
| 신고번호 | {form.registration_no} |

## 3. 비행계획
| 항목 | 값 |
|---|---|
| 비행 예정 시간 | 약 {form.flight_duration_min} 분 |
| 비행 방식 | {form.flight_mode} |
| 최대 고도(AGL) | {form.max_altitude_m} m |
| 비가시권(BVLOS) | {bvlos} |
| 야간 비행 | {night} |

## 4. 비행구역 (WGS84, 평면근사)
| 항목 | 위도 | 경도 |
|---|---|---|
| 중심 | {a.center_lat} | {a.center_lon} |
| 남서(SW) | {a.sw_lat} | {a.sw_lon} |
| 북동(NE) | {a.ne_lat} | {a.ne_lon} |

반경 약 {a.radius_km} km

## 5. 조종자
| 항목 | 값 |
|---|---|
| 성명 | {form.pilot_name} |
| 자격번호 | {form.pilot_license_no} |

## 6. 안전대책
{measures}

## 7. 보험
| 항목 | 값 |
|---|---|
| 증권번호 | {form.insurance_policy_no} |
"""


def render_json(form: FlightPlanForm) -> str:
    """양식을 JSON 문자열로 직렬화한다."""
    return json.dumps(asdict(form), ensure_ascii=False, indent=2, sort_keys=True)


def _safe_name(name: str) -> str:
    """출력 파일명에 쓸 수 있도록 경로 구분자 등 위험 문자를 제거한다."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)


def _ensure_within_root(path: Path) -> Path:
    """경로가 프로젝트 루트 하위인지 검증한다(경로 이탈 차단)."""
    resolved = path.resolve()
    root = ROOT.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"설정 경로가 프로젝트 루트를 벗어남: {resolved}")
    return resolved


def _resolve_input(args: argparse.Namespace) -> tuple[Path, str]:
    """CLI 인자 → (설정 경로, 출력 이름). 경로 이탈을 차단한다."""
    if args.scenario:
        path = ROOT / "config" / "scenario_params" / f"{_safe_name(args.scenario)}.yaml"
        return _ensure_within_root(path), _safe_name(args.scenario)
    path = _ensure_within_root(ROOT / args.config)
    return path, _safe_name(path.stem)


def main() -> None:
    parser = argparse.ArgumentParser(description="비행승인 신청서(Drone One-Stop) 자동 생성")
    parser.add_argument("--scenario", help="config/scenario_params/<name>.yaml")
    parser.add_argument(
        "--config",
        default="config/default_simulation.yaml",
        help="설정 YAML 경로 (--scenario 미지정 시)",
    )
    parser.add_argument("--format", choices=["md", "json", "both"], default="both")
    args = parser.parse_args()

    path, name = _resolve_input(args)
    config = load_config(path)
    form = build_flight_plan(config, name)

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    if args.format in ("md", "both"):
        md_path = out_dir / f"flight_plan_{name}.md"
        md_path.write_text(render_markdown(form), encoding="utf-8")
        print(f"작성: {md_path}")
    if args.format in ("json", "both"):
        json_path = out_dir / f"flight_plan_{name}.json"
        json_path.write_text(render_json(form), encoding="utf-8")
        print(f"작성: {json_path}")


if __name__ == "__main__":
    main()
