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
    energy_efficiency_wh_per_km: float = 0.0  # 평균 에너지 소모 (Wh/km)
    failures_injected:     int   = 0
    comms_losses_injected: int   = 0

    # 컨트롤러 처리량
    clearances_approved: int   = 0
    clearances_denied:   int   = 0
    clearances_per_sec:  float = 0.0  # 60초 윈도우 평균 처리율

    # 경로 계획
    cbs_attempts:   int = 0
    cbs_successes:  int = 0
    astar_fallbacks: int = 0

    # 통신
    comm_messages_sent:     int = 0
    comm_messages_delivered: int = 0
    comm_messages_dropped:  int = 0
    comm_drop_rate:         float = 0.0

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
            ("에너지 효율",        f"{self.energy_efficiency_wh_per_km:.2f} Wh/km"),
            ("고장 주입",          str(self.failures_injected)),
            ("통신 두절 주입",     str(self.comms_losses_injected)),
            ("CBS 시도/성공",      f"{self.cbs_attempts}/{self.cbs_successes}"),
            ("A* 폴백",            str(self.astar_fallbacks)),
            ("허가 처리율",        f"{self.clearances_per_sec:.1f} /s"),
            ("통신 전송/배달/손실", f"{self.comm_messages_sent}/{self.comm_messages_delivered}/{self.comm_messages_dropped}"),
            ("통신 손실률",        f"{self.comm_drop_rate:.1%}"),
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
    MAX_SNAPSHOTS = 100_000  # 메모리 제한: ~100대 × 600초 / 5초 간격

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

        self._cbs_attempts  = 0
        self._cbs_successes = 0
        self._astar_count   = 0
        self._ctrl_cps      = 0.0
        self._comm_sent      = 0
        self._comm_delivered = 0
        self._comm_dropped   = 0

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
        # 메모리 최적화: 5초 간격 샘플링 (1Hz 전체 → 0.2Hz)
        if hasattr(self, '_last_snapshot_t') and t - self._last_snapshot_t < 5.0:
            # 거리/시간만 갱신 (경로 효율 계산용)
            for did, d in drones.items():
                self._dist_actual[did] = float(d.distance_flown_m)
                self._flight_time[did] = float(d.flight_time_s)
            return
        self._last_snapshot_t = t
        if len(self._snapshots) >= self.MAX_SNAPSHOTS:
            return  # 메모리 제한 도달
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

    def record_controller_stats(
        self,
        cbs_attempts: int = 0,
        cbs_successes: int = 0,
        astar_count: int = 0,
        clearances_per_sec: float = 0.0,
    ) -> None:
        """컨트롤러 통계 기록 (finalize 전 호출)"""
        self._cbs_attempts = cbs_attempts
        self._cbs_successes = cbs_successes
        self._astar_count = astar_count
        self._ctrl_cps = clearances_per_sec

    def record_comm_stats(
        self,
        sent: int = 0,
        delivered: int = 0,
        dropped: int = 0,
    ) -> None:
        """통신 버스 통계 기록 (finalize 전 호출)"""
        self._comm_sent = sent
        self._comm_delivered = delivered
        self._comm_dropped = dropped

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

        # 충돌 해결률: 전체 위험 상황 중 충돌 미발생 비율
        # total_events = 충돌예측 + 실제충돌 (예측 없이 발생한 충돌 포함)
        total_events = self._conflicts_total + self._collision_count
        if total_events > 0:
            res_rate = 100.0 * (1.0 - self._collision_count / total_events)
        else:
            res_rate = 100.0

        # 어드바이저리 지연
        lats = self._adv_latencies
        p50  = float(np.percentile(lats, 50)) if lats else 0.0
        p99  = float(np.percentile(lats, 99)) if lats else 0.0

        total_flight_s  = sum(self._flight_time.values())
        total_dist_km   = sum(self._dist_actual.values()) / 1000.0

        # 에너지 효율 추정: 평균 50Wh 배터리, 사용 배터리% → Wh/km
        battery_used_pct = [100.0 - ev.get("bat", 100.0) for ev in self._snapshots
                           if ev.get("phase") not in ("GROUNDED",)]
        avg_wh = 50.0  # 기본 배터리 용량 가정
        energy_wh = sum(max(0, p) * avg_wh / 100.0 for p in battery_used_pct) if battery_used_pct else 0.0
        energy_eff = energy_wh / max(total_dist_km, 0.01) if total_dist_km > 0 else 0.0

        # 고장/통신두절 주입 카운트
        fail_injected = sum(1 for ev in self._events if ev["type"] == "FAILURE_INJECTED")
        comms_injected = sum(1 for ev in self._events if ev["type"] == "COMMS_LOSS_INJECTED")

        # 통신 드롭률
        comm_total = self._comm_sent or 0
        comm_drop_rate = self._comm_dropped / max(comm_total, 1)

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
            energy_efficiency_wh_per_km=energy_eff,
            failures_injected=fail_injected,
            comms_losses_injected=comms_injected,
            clearances_approved=self._clearances_ok,
            clearances_denied=self._clearances_no,
            clearances_per_sec=self._ctrl_cps,
            cbs_attempts=self._cbs_attempts,
            cbs_successes=self._cbs_successes,
            astar_fallbacks=self._astar_count,
            comm_messages_sent=self._comm_sent,
            comm_messages_delivered=self._comm_delivered,
            comm_messages_dropped=self._comm_dropped,
            comm_drop_rate=comm_drop_rate,
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
