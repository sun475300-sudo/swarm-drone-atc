"""
시뮬레이션 분석 / 결과 수집 모듈

SimulationAnalytics — 드론 상태 스냅샷, 이벤트 로그, 지표 계산
SimulationResult    — 최종 결과 데이터클래스 (Monte Carlo 집계용)
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from src.airspace_control.agents.drone_state import DroneState


@dataclass
class SimulationResult:
    """시뮬레이션 1회 결과 — Monte Carlo 수집 단위"""
    # 안전
    collision_count:  int   = 0
    near_miss_count:  int   = 0

    # 분리 보장
    conflicts_total:        int   = 0
    advisories_issued:      int   = 0
    conflict_resolution_rate_pct: float = 100.0  # 충돌 → 어드바이저리 발령률

    # 효율
    route_efficiency_mean: float = 1.0   # actual/planned 거리 비율
    route_efficiency_max:  float = 1.0
    total_flight_time_s:   float = 0.0
    total_distance_km:     float = 0.0

    # 컨트롤러 처리량
    clearances_approved: int   = 0
    clearances_denied:   int   = 0

    # 지연 (s)
    advisory_latency_p50: float = 0.0
    advisory_latency_p99: float = 0.0

    # 설정 메타
    seed:          int   = 0
    scenario:      str   = "default"
    duration_s:    float = 0.0
    n_drones:      int   = 0
    config_params: dict  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {}
        for f_name in self.__dataclass_fields__:
            v = getattr(self, f_name)
            if isinstance(v, dict):
                continue   # Monte Carlo 집계 시 생략
            d[f_name] = v
        return d

    def summary_table(self) -> str:
        rows = [
            ("충돌 수",            str(self.collision_count)),
            ("근접 경고",          str(self.near_miss_count)),
            ("충돌 감지 총계",     str(self.conflicts_total)),
            ("어드바이저리 발령",  str(self.advisories_issued)),
            ("충돌 해결률",        f"{self.conflict_resolution_rate_pct:.1f} %"),
            ("경로 효율 (평균)",   f"{self.route_efficiency_mean:.3f}"),
            ("경로 효율 (최대)",   f"{self.route_efficiency_max:.3f}"),
            ("허가 승인",          str(self.clearances_approved)),
            ("총 비행 거리",       f"{self.total_distance_km:.1f} km"),
            ("어드바이저리 P50",   f"{self.advisory_latency_p50:.2f} s"),
            ("어드바이저리 P99",   f"{self.advisory_latency_p99:.2f} s"),
        ]
        lines = [
            "┌──────────────────────────────┬──────────────────┐",
            "│ KPI                          │ 값               │",
            "├──────────────────────────────┼──────────────────┤",
        ]
        for k, v in rows:
            lines.append(f"│ {k:<28} │ {v:>16} │")
        lines.append("└──────────────────────────────┴──────────────────┘")
        return "\n".join(lines)

    def check_acceptance(self, thresholds: dict) -> dict[str, bool]:
        """monte_carlo.yaml acceptance_thresholds 대비 합격 여부"""
        checks: dict[str, bool] = {}
        checks["no_collision"]      = self.collision_count == 0
        checks["conflict_res_rate"] = (
            self.conflict_resolution_rate_pct
            >= float(thresholds.get("conflict_resolution_rate_pct", 99.5))
        )
        checks["route_efficiency"]  = (
            self.route_efficiency_mean
            <= float(thresholds.get("route_efficiency_max", 1.15))
        )
        return checks


class SimulationAnalytics:
    """
    실시간 이벤트 수신 + 1 Hz 스냅샷 수집.
    run() 종료 후 finalize()로 SimulationResult를 반환한다.
    """

    MAX_EVENTS = 50_000

    def __init__(self, cfg: dict) -> None:
        self._cfg = cfg
        self._save_traj = bool(cfg.get("logging", {}).get("save_trajectory", True))

        self._events:      list[dict] = []
        self._snapshots:   list[dict] = []
        self._adv_latencies: list[float] = []
        self._conflict_times: list[float] = []

        self._collision_count  = 0
        self._near_miss_count  = 0
        self._conflicts_total  = 0
        self._advisories_total = 0
        self._clearances_ok    = 0
        self._clearances_no    = 0

        self._dist_actual:  dict[str, float] = {}  # drone_id → actual km
        self._dist_planned: dict[str, float] = {}
        self._flight_time:  dict[str, float] = {}

        self._start_wall = time.monotonic()

    # ── 이벤트 기록 ──────────────────────────────────────────

    def record_event(self, event_type: str, t: float, **kwargs) -> None:
        if len(self._events) >= self.MAX_EVENTS:
            return
        ev = {"type": event_type, "t": t, **kwargs}
        self._events.append(ev)

        # 즉시 집계
        if event_type == "COLLISION":
            self._collision_count += 1
        elif event_type == "NEAR_MISS":
            self._near_miss_count += 1
        elif event_type == "CONFLICT":
            self._conflicts_total += 1
            self._conflict_times.append(t)
        elif event_type == "ADVISORY_ISSUED":
            self._advisories_total += 1
        elif event_type == "CLEARANCE_APPROVED":
            self._clearances_ok += 1
        elif event_type == "CLEARANCE_DENIED":
            self._clearances_no += 1

    def record_advisory_latency(self, latency_s: float) -> None:
        self._adv_latencies.append(latency_s)

    # ── 스냅샷 ──────────────────────────────────────────────

    def record_snapshot(
        self,
        drones: dict[str, "DroneState"],
        t: float,
    ) -> None:
        if not self._save_traj:
            return
        for did, d in drones.items():
            self._snapshots.append({
                "t":       t,
                "id":      did,
                "x":       float(d.position[0]),
                "y":       float(d.position[1]),
                "z":       float(d.position[2]),
                "spd":     float(d.speed),
                "bat":     float(d.battery_pct),
                "phase":   d.flight_phase.name,
            })
            # 거리 누적
            self._dist_actual[did] = float(d.distance_flown_m)
            self._flight_time[did] = float(d.flight_time_s)

    def record_planned_distance(self, drone_id: str, dist_m: float) -> None:
        self._dist_planned[drone_id] = dist_m

    # ── 최종 결과 ────────────────────────────────────────────

    def finalize(
        self,
        seed: int = 0,
        scenario: str = "default",
        duration_s: float = 0.0,
        n_drones: int = 0,
    ) -> SimulationResult:
        # 경로 효율 (actual / planned)
        efficiencies = []
        for did in self._dist_actual:
            planned = self._dist_planned.get(did, 0.0)
            actual  = self._dist_actual[did]
            if planned > 10.0:
                efficiencies.append(actual / planned)

        eff_mean = float(np.mean(efficiencies))  if efficiencies else 1.0
        eff_max  = float(np.max(efficiencies))   if efficiencies else 1.0

        # 충돌 해결률 (음수 방지: 충돌 > 충돌예측 시 0% 클램프)
        if self._conflicts_total > 0:
            res_rate = max(0.0, 100.0 * (1.0 - self._collision_count / self._conflicts_total))
        else:
            res_rate = 100.0

        # 어드바이저리 지연
        lats = self._adv_latencies
        p50  = float(np.percentile(lats, 50)) if lats else 0.0
        p99  = float(np.percentile(lats, 99)) if lats else 0.0

        total_flight_s  = sum(self._flight_time.values())
        total_dist_km   = sum(self._dist_actual.values()) / 1000.0

        return SimulationResult(
            collision_count=self._collision_count,
            near_miss_count=self._near_miss_count,
            conflicts_total=self._conflicts_total,
            advisories_issued=self._advisories_total,
            conflict_resolution_rate_pct=res_rate,
            route_efficiency_mean=eff_mean,
            route_efficiency_max=eff_max,
            total_flight_time_s=total_flight_s,
            total_distance_km=total_dist_km,
            clearances_approved=self._clearances_ok,
            clearances_denied=self._clearances_no,
            advisory_latency_p50=p50,
            advisory_latency_p99=p99,
            seed=seed,
            scenario=scenario,
            duration_s=duration_s,
            n_drones=n_drones,
        )

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    @property
    def snapshots(self) -> list[dict]:
        return list(self._snapshots)
