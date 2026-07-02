"""GENESIS Phase 368 -- 에너지 인식 임무 계획.

드론 에너지 프로파일, 바람 조건, 웨이포인트 시퀀스를 기반으로
임무 비행의 에너지 소비를 분석적으로 추정하고 실현가능성을 판단한다.

Note: 해석적 에너지 모델이며, 특정 기체에 대한 캘리브레이션 없음.

CLI:
    python simulation/energy_aware_planner.py --plan
    python simulation/energy_aware_planner.py --profile medium_quad
    python simulation/energy_aware_planner.py --wind 5,180
    python simulation/energy_aware_planner.py --feasibility
    python simulation/energy_aware_planner.py --json
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── Constants ───────────────────────────────────────────────────

DEFAULT_CLIMB_RATE_MS: float = 2.0
DEFAULT_DESCENT_RATE_MS: float = 1.5
MIN_GROUND_SPEED_MS: float = 0.5


# ── Dataclasses ─────────────────────────────────────────────────

@dataclass(frozen=True)
class DroneEnergyProfile:
    """드론 에너지 프로파일 — 질량, 배터리, 소비전력 파라미터."""

    mass_kg: float
    battery_wh: float
    hover_power_w: float
    cruise_power_w: float
    max_speed_ms: float
    climb_power_w: float
    descent_power_w: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "mass_kg": self.mass_kg,
            "battery_wh": self.battery_wh,
            "hover_power_w": self.hover_power_w,
            "cruise_power_w": self.cruise_power_w,
            "max_speed_ms": self.max_speed_ms,
            "climb_power_w": self.climb_power_w,
            "descent_power_w": self.descent_power_w,
        }


@dataclass(frozen=True)
class WindCondition:
    """바람 조건 — 속도, 방향(도), 돌풍."""

    speed_ms: float
    direction_deg: float
    gust_ms: float = 0.0


@dataclass(frozen=True)
class Waypoint:
    """3D 웨이포인트 — 좌표와 체공 시간."""

    x: float
    y: float
    z: float
    required_loiter_s: float = 0.0


@dataclass(frozen=True)
class LegEnergy:
    """구간별 에너지 소비 분석 결과."""

    from_wp: int
    to_wp: int
    distance_m: float
    energy_wh: float
    time_s: float
    headwind_component_ms: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_wp": self.from_wp,
            "to_wp": self.to_wp,
            "distance_m": round(self.distance_m, 2),
            "energy_wh": round(self.energy_wh, 4),
            "time_s": round(self.time_s, 2),
            "headwind_component_ms": round(self.headwind_component_ms, 3),
        }


@dataclass(frozen=True)
class MissionPlan:
    """임무 계획 결과 — 전체 에너지, 시간, 실현가능성."""

    waypoints: tuple[Waypoint, ...]
    legs: tuple[LegEnergy, ...]
    total_energy_wh: float
    total_time_s: float
    reserve_pct: float
    is_feasible: bool
    return_energy_wh: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_waypoints": len(self.waypoints),
            "n_legs": len(self.legs),
            "total_energy_wh": round(self.total_energy_wh, 4),
            "total_time_s": round(self.total_time_s, 2),
            "reserve_pct": self.reserve_pct,
            "is_feasible": self.is_feasible,
            "return_energy_wh": round(self.return_energy_wh, 4),
            "legs": [leg.as_dict() for leg in self.legs],
        }


# ── Default Profiles ────────────────────────────────────────────

SMALL_QUAD = DroneEnergyProfile(
    mass_kg=0.249,
    battery_wh=19.6,
    hover_power_w=30.0,
    cruise_power_w=25.0,
    max_speed_ms=16.0,
    climb_power_w=45.0,
    descent_power_w=15.0,
)

MEDIUM_QUAD = DroneEnergyProfile(
    mass_kg=6.3,
    battery_wh=274.0,
    hover_power_w=320.0,
    cruise_power_w=280.0,
    max_speed_ms=23.0,
    climb_power_w=500.0,
    descent_power_w=150.0,
)

HEAVY_LIFT = DroneEnergyProfile(
    mass_kg=25.0,
    battery_wh=900.0,
    hover_power_w=1200.0,
    cruise_power_w=1000.0,
    max_speed_ms=18.0,
    climb_power_w=1800.0,
    descent_power_w=500.0,
)

PROFILES: dict[str, DroneEnergyProfile] = {
    "small_quad": SMALL_QUAD,
    "medium_quad": MEDIUM_QUAD,
    "heavy_lift": HEAVY_LIFT,
}


# ── Core Functions ──────────────────────────────────────────────

def _headwind_component(
    leg_dx: float,
    leg_dy: float,
    leg_dist: float,
    wind: WindCondition,
) -> float:
    """구간 방향 대비 정풍/배풍 성분을 계산한다.

    양수 = 정풍(headwind), 음수 = 배풍(tailwind).
    기상학적 관례: direction_deg는 바람이 불어오는 방향 (0=북, 180=남).
    """
    if leg_dist < 1e-9:
        return 0.0
    wind_rad = math.radians(wind.direction_deg)
    # 바람이 불어오는 방향에서 불어가는 방향으로 변환
    wind_vx = -wind.speed_ms * math.sin(wind_rad)
    wind_vy = -wind.speed_ms * math.cos(wind_rad)
    unit_x = leg_dx / leg_dist
    unit_y = leg_dy / leg_dist
    # 구간 진행 방향과 반대인 바람 성분 = headwind
    return -(wind_vx * unit_x + wind_vy * unit_y)


def _horizontal_distance(wp1: Waypoint, wp2: Waypoint) -> float:
    """두 웨이포인트 간 수평 거리를 계산한다."""
    dx = wp2.x - wp1.x
    dy = wp2.y - wp1.y
    return math.sqrt(dx * dx + dy * dy)


def _3d_distance(wp1: Waypoint, wp2: Waypoint) -> float:
    """두 웨이포인트 간 3D 거리를 계산한다."""
    dx = wp2.x - wp1.x
    dy = wp2.y - wp1.y
    dz = wp2.z - wp1.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def compute_leg_energy(
    profile: DroneEnergyProfile,
    wp1: Waypoint,
    wp2: Waypoint,
    wind: WindCondition,
    *,
    from_wp: int = 0,
    to_wp: int = 0,
) -> LegEnergy:
    """두 웨이포인트 간 에너지 소비를 분석적으로 계산한다."""
    dx = wp2.x - wp1.x
    dy = wp2.y - wp1.y
    dz = wp2.z - wp1.z
    horiz_dist = math.sqrt(dx * dx + dy * dy)
    dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)

    headwind = _headwind_component(dx, dy, horiz_dist, wind)
    ground_speed = max(profile.max_speed_ms - headwind, MIN_GROUND_SPEED_MS)

    energy_wh = 0.0
    time_s = 0.0

    # Cruise energy (수평 이동)
    if horiz_dist > 1e-6:
        cruise_time_s = horiz_dist / ground_speed
        cruise_energy = profile.cruise_power_w * cruise_time_s / 3600.0
        energy_wh += cruise_energy
        time_s += cruise_time_s

    # Climb / descent energy (수직 이동)
    if dz > 0.01:
        climb_time = dz / DEFAULT_CLIMB_RATE_MS
        energy_wh += profile.climb_power_w * climb_time / 3600.0
        time_s += climb_time
    elif dz < -0.01:
        descent_time = abs(dz) / DEFAULT_DESCENT_RATE_MS
        energy_wh += profile.descent_power_w * descent_time / 3600.0
        time_s += descent_time

    # Loiter energy (체공)
    if wp2.required_loiter_s > 0:
        energy_wh += profile.hover_power_w * wp2.required_loiter_s / 3600.0
        time_s += wp2.required_loiter_s

    return LegEnergy(
        from_wp=from_wp,
        to_wp=to_wp,
        distance_m=dist_3d,
        energy_wh=energy_wh,
        time_s=time_s,
        headwind_component_ms=headwind,
    )


def plan_mission(
    profile: DroneEnergyProfile,
    waypoints: tuple[Waypoint, ...],
    wind: WindCondition,
    reserve_pct: float = 20.0,
) -> MissionPlan:
    """웨이포인트 시퀀스에 대한 임무 에너지 계획을 생성한다."""
    if len(waypoints) < 2:
        return MissionPlan(
            waypoints=waypoints,
            legs=(),
            total_energy_wh=0.0,
            total_time_s=0.0,
            reserve_pct=reserve_pct,
            is_feasible=True,
            return_energy_wh=0.0,
        )

    legs: list[LegEnergy] = []
    for i in range(len(waypoints) - 1):
        legs.append(compute_leg_energy(
            profile, waypoints[i], waypoints[i + 1], wind,
            from_wp=i, to_wp=i + 1,
        ))

    total_energy = sum(leg.energy_wh for leg in legs)
    total_time = sum(leg.time_s for leg in legs)

    # 귀환 에너지 (마지막 WP → 첫 WP)
    return_leg = compute_leg_energy(profile, waypoints[-1], waypoints[0], wind)
    return_energy = return_leg.energy_wh

    required = total_energy + return_energy
    reserve_factor = 1.0 + reserve_pct / 100.0
    feasible = required * reserve_factor <= profile.battery_wh

    return MissionPlan(
        waypoints=waypoints,
        legs=tuple(legs),
        total_energy_wh=total_energy,
        total_time_s=total_time,
        reserve_pct=reserve_pct,
        is_feasible=feasible,
        return_energy_wh=return_energy,
    )


def is_feasible(plan: MissionPlan) -> bool:
    """임무 계획의 실현가능성을 반환한다."""
    return plan.is_feasible


def suggest_reduction(
    plan: MissionPlan,
    profile: DroneEnergyProfile,
) -> tuple[str, ...]:
    """비실현 임무에 대한 에너지 절감 제안을 반환한다."""
    if plan.is_feasible:
        return ()

    suggestions: list[str] = []

    # 체공 시간 절감 제안
    loiter_wps = [
        (i, wp) for i, wp in enumerate(plan.waypoints)
        if wp.required_loiter_s > 0
    ]
    if loiter_wps:
        total_loiter_s = sum(wp.required_loiter_s for _, wp in loiter_wps)
        suggestions.append(
            f"체공 시간 단축: {len(loiter_wps)}개 WP에서 "
            f"총 {total_loiter_s:.0f}s 체공 중"
        )

    # 웨이포인트 삭제 제안 (에너지 소비 큰 순)
    if len(plan.legs) >= 2:
        sorted_legs = sorted(
            plan.legs, key=lambda l: l.energy_wh, reverse=True,
        )
        top = sorted_legs[0]
        suggestions.append(
            f"고비용 구간 제거: WP{top.from_wp}→WP{top.to_wp} "
            f"({top.energy_wh:.2f} Wh)"
        )

    # 고도 낮추기 제안
    max_alt = max(wp.z for wp in plan.waypoints)
    if max_alt > 50.0:
        suggestions.append(
            f"최대 고도 감소: 현재 {max_alt:.0f}m → 50m 이하 권장"
        )

    # 배터리 용량 대비 부족량
    reserve_factor = 1.0 + plan.reserve_pct / 100.0
    required = (plan.total_energy_wh + plan.return_energy_wh) * reserve_factor
    deficit = required - profile.battery_wh
    suggestions.append(
        f"에너지 부족량: {deficit:.2f} Wh (예비 {plan.reserve_pct}% 포함)",
    )

    return tuple(suggestions)


def get_profile(name: str) -> DroneEnergyProfile:
    """이름으로 기본 프로파일을 가져온다."""
    if name not in PROFILES:
        valid = ", ".join(PROFILES)
        raise ValueError(f"Unknown profile '{name}'. Valid: {valid}")
    return PROFILES[name]


# ── CLI ─────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="에너지 인식 임무 계획 (GENESIS Phase 368)",
    )
    p.add_argument("--plan", action="store_true", help="예시 임무 계획 실행")
    p.add_argument(
        "--profile",
        choices=list(PROFILES),
        default="medium_quad",
        help="드론 프로파일 (default: medium_quad)",
    )
    p.add_argument(
        "--wind",
        default="0,0",
        help="바람 조건: speed_ms,direction_deg (default: 0,0)",
    )
    p.add_argument(
        "--feasibility", action="store_true", help="실현가능성 분석",
    )
    p.add_argument(
        "--json", action="store_true", dest="as_json", help="JSON 출력",
    )
    return p


def _parse_wind(wind_str: str) -> WindCondition:
    parts = wind_str.split(",")
    if not parts or not parts[0].strip():
        raise ValueError(f"Invalid wind format: {wind_str!r} (expected: speed[,direction[,gust]])")
    try:
        speed = float(parts[0])
        direction = float(parts[1]) if len(parts) > 1 else 0.0
        gust = float(parts[2]) if len(parts) > 2 else 0.0
    except ValueError as exc:
        raise ValueError(
            f"Invalid wind format: {wind_str!r} (expected numeric values)",
        ) from exc
    if speed < 0:
        raise ValueError(f"Wind speed must be >= 0, got {speed}")
    return WindCondition(speed_ms=speed, direction_deg=direction, gust_ms=gust)


_EXAMPLE_WAYPOINTS: tuple[Waypoint, ...] = (
    Waypoint(0.0, 0.0, 50.0),
    Waypoint(500.0, 0.0, 60.0, required_loiter_s=30.0),
    Waypoint(500.0, 500.0, 55.0, required_loiter_s=15.0),
    Waypoint(1000.0, 500.0, 70.0),
    Waypoint(1000.0, 0.0, 50.0, required_loiter_s=20.0),
)


def _run_cli(args: argparse.Namespace) -> dict[str, Any]:
    profile = get_profile(args.profile)
    wind = _parse_wind(args.wind)
    waypoints = _EXAMPLE_WAYPOINTS

    result: dict[str, Any] = {"profile": args.profile}

    if args.plan or args.feasibility:
        mission = plan_mission(profile, waypoints, wind)
        result["mission"] = mission.as_dict()

        if args.feasibility:
            result["feasible"] = mission.is_feasible
            if not mission.is_feasible:
                result["suggestions"] = list(
                    suggest_reduction(mission, profile),
                )

    return result


def main() -> None:
    """CLI 진입점."""
    parser = _build_parser()
    args = parser.parse_args()

    if not (args.plan or args.feasibility):
        parser.print_help()
        return

    result = _run_cli(args)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_result(result)


def _print_result(result: dict[str, Any]) -> None:
    """결과를 사람이 읽기 쉬운 형태로 출력한다."""
    print(f"\n프로파일: {result['profile']}")
    mission = result.get("mission")
    if mission:
        print(f"웨이포인트: {mission['n_waypoints']}개, 구간: {mission['n_legs']}개")
        print(f"총 에너지: {mission['total_energy_wh']:.2f} Wh")
        print(f"총 시간: {mission['total_time_s']:.1f}초")
        print(f"귀환 에너지: {mission['return_energy_wh']:.2f} Wh")
        print(f"예비: {mission['reserve_pct']}%")
        tag = "가능" if mission["is_feasible"] else "불가"
        print(f"실현가능성: {tag}")

    suggestions = result.get("suggestions")
    if suggestions:
        print("\n개선 제안:")
        for s in suggestions:
            print(f"  - {s}")
    print()


if __name__ == "__main__":
    main()
