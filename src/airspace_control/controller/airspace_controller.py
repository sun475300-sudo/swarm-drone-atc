"""
공역 컨트롤러 — SimPy 기반 1 Hz 제어 루프

책임:
  - ClearanceRequest 처리 (우선순위 큐 → A* 경로 → ClearanceResponse)
  - 충돌 예측 스캔 (O(N²) CPA → AdvisoryGenerator → ResolutionAdvisory)
  - 침입 드론 탐지 (is_registered=False → IntrusionAlert)
  - Voronoi 공역 분할 10 s 주기 갱신
  - 어드바이저리 만료 관리
"""
from __future__ import annotations
import uuid
import numpy as np
from typing import TYPE_CHECKING

import simpy

from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
from src.airspace_control.comms.message_types import (
    TelemetryMessage, ClearanceRequest, ClearanceResponse,
    ResolutionAdvisory, IntrusionAlert,
)
from src.airspace_control.controller.priority_queue import FlightPriorityQueue
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.utils.geo_math import closest_approach, distance_3d
from simulation.voronoi_airspace.voronoi_partition import compute_voronoi_partition
from simulation.spatial_hash import SpatialHash
from simulation.cbs_planner.cbs import (
    cbs_plan, position_to_grid, GridNode, GRID_RESOLUTION,
)

if TYPE_CHECKING:
    from simulation.analytics import SimulationAnalytics


class AirspaceController:
    """
    공역 통제 컨트롤러.

    Parameters
    ----------
    env:            SimPy Environment
    comm_bus:       CommunicationBus 인스턴스
    planner:        FlightPathPlanner 인스턴스
    advisory_gen:   AdvisoryGenerator 인스턴스
    priority_queue: FlightPriorityQueue 인스턴스
    config:         default_simulation.yaml 설정 dict
    analytics:      SimulationAnalytics (선택)
    """

    CONTROL_HZ = 1.0           # 제어 루프 주파수
    VORONOI_INTERVAL_S = 10.0  # Voronoi 갱신 주기

    def __init__(
        self,
        env: simpy.Environment,
        comm_bus: CommunicationBus,
        planner: FlightPathPlanner,
        advisory_gen: AdvisoryGenerator,
        priority_queue: FlightPriorityQueue,
        config: dict,
        analytics: "SimulationAnalytics | None" = None,
    ) -> None:
        self.env           = env
        self.comm_bus      = comm_bus
        self.planner       = planner
        self.advisory_gen  = advisory_gen
        self.pq            = priority_queue
        self.config        = config
        self.analytics     = analytics

        self._active_drones: dict[str, DroneState] = {}
        self._active_routes: dict[str, object]     = {}   # drone_id → Route
        self._pending:       list[ClearanceRequest] = []
        self._advisories:    dict[str, ResolutionAdvisory] = {}  # adv_id → adv
        self._intruders:     set[str]               = set()
        self._voronoi_cells: dict                   = {}
        self._spatial_hash = SpatialHash(cell_size=50.0)

        self._lat_min   = float(config.get("separation_standards", {})
                                .get("lateral_min_m", 50.0))
        self._vert_min  = float(config.get("separation_standards", {})
                                .get("vertical_min_m", 15.0))
        self._near_lat  = float(config.get("separation_standards", {})
                                .get("near_miss_lateral_m", 10.0))
        self._lookahead = float(config.get("separation_standards", {})
                                .get("conflict_lookahead_s", 90.0))
        self._max_clear = int(config.get("controller", {})
                              .get("max_concurrent_clearances", 500))

        # 텔레메트리/허가 요청 수신 구독
        comm_bus.subscribe("CONTROLLER", self._on_message)

    # ── SimPy 프로세스 ────────────────────────────────────────

    def run(self):
        """1 Hz 제어 루프 SimPy 프로세스"""
        dt = 1.0 / self.CONTROL_HZ
        while True:
            yield self.env.timeout(dt)
            t = float(self.env.now)
            self._process_clearances(t)
            self._scan_conflicts(t)
            self._detect_intruders(t)
            self._expire_advisories(t)
            if int(t) % int(self.VORONOI_INTERVAL_S) == 0:
                self._refresh_voronoi()

    # ── 메시지 수신 ──────────────────────────────────────────

    def _on_message(self, msg: CommMessage) -> None:
        payload = msg.payload
        if isinstance(payload, TelemetryMessage):
            self._update_drone_state(payload)
        elif isinstance(payload, ClearanceRequest):
            self._pending.append(payload)

    def _update_drone_state(self, tm: TelemetryMessage) -> None:
        drone = self._active_drones.get(tm.drone_id)
        if drone is None:
            drone = DroneState(
                drone_id=tm.drone_id,
                position=np.array(tm.position, dtype=float),
                velocity=np.array(tm.velocity, dtype=float),
            )
            self._active_drones[tm.drone_id] = drone
        else:
            drone.position = np.array(tm.position, dtype=float)
            drone.velocity = np.array(tm.velocity, dtype=float)
            drone.battery_pct = float(tm.battery_pct)
        drone.last_update_s = float(tm.timestamp_s)
        from src.airspace_control.agents.drone_state import FlightPhase
        try:
            drone.flight_phase = FlightPhase[tm.flight_phase]
        except KeyError:
            pass

    # ── 허가 처리 ────────────────────────────────────────────

    def _process_clearances(self, t: float) -> None:
        # 대기 중 요청을 우선순위 큐에 삽입
        for req in self._pending:
            self.pq.push(req, req.timestamp_s)
        self._pending.clear()

        # 배치 수집: 최대 max_clear 건 꺼내기
        batch: list[ClearanceRequest] = []
        while len(batch) < self._max_clear:
            item = self.pq.pop()
            if item is None:
                break
            batch.append(item)

        if not batch:
            return

        # CBS 멀티에이전트 경로 계획 (3건 이상 동시 요청 시)
        cbs_waypoints: dict[str, list] = {}
        if len(batch) >= 3:
            cbs_waypoints = self._cbs_plan_batch(batch)

        for req in batch:
            route = self.planner.plan_route(
                drone_id=req.drone_id,
                origin=req.origin,
                destination=req.destination,
                priority=req.priority,
            )
            approved = True
            reason   = ""

            # Voronoi 셀 충돌 경고
            voronoi_conflict = self._check_voronoi_conflict(req.drone_id, req.destination)
            if voronoi_conflict:
                approved = False
                reason = f"voronoi_conflict:{voronoi_conflict}"

            # CBS 경로가 있으면 우선 사용
            if req.drone_id in cbs_waypoints:
                waypoints = cbs_waypoints[req.drone_id]
            else:
                waypoints = [wp.position for wp in route.waypoints]

            resp = ClearanceResponse(
                drone_id=req.drone_id,
                approved=approved,
                assigned_waypoints=waypoints,
                altitude_band=(30.0, 120.0),
                timestamp_s=t,
                reason=reason,
            )
            self.comm_bus.send(CommMessage(
                sender_id="CONTROLLER",
                receiver_id=req.drone_id,
                payload=resp,
                sent_time=t,
                channel="clearance",
            ))
            if approved:
                self._active_routes[req.drone_id] = route
            if self.analytics:
                event = "CLEARANCE_APPROVED" if approved else "CLEARANCE_DENIED"
                self.analytics.record_event(event, t, drone_id=req.drone_id,
                                            voronoi_conflict=voronoi_conflict)

    def _cbs_plan_batch(self, batch: list) -> dict[str, list]:
        """CBS로 동시 요청 배치의 충돌 없는 경로 세트 계산"""
        bounds_m = max(
            abs(self.config.get("airspace", {})
                .get("bounds_km", {}).get("x", [-5, 5])[1]) * 1000,
            5000.0,
        )
        grid_bounds = {
            "x": [int(-bounds_m / GRID_RESOLUTION), int(bounds_m / GRID_RESOLUTION)],
            "y": [int(-bounds_m / GRID_RESOLUTION), int(bounds_m / GRID_RESOLUTION)],
            "z": [0, int(120.0 / GRID_RESOLUTION)],
        }
        starts = {}
        goals = {}
        for req in batch:
            starts[req.drone_id] = position_to_grid(req.origin)
            goals[req.drone_id] = position_to_grid(req.destination)

        try:
            paths = cbs_plan(starts, goals, grid_bounds, max_ct_nodes=500)
        except Exception:
            return {}

        result: dict[str, list] = {}
        for did, grid_path in paths.items():
            # GridNode → 연속 좌표 변환 (웨이포인트 간소화: 10스텝마다)
            wp_list = []
            for i, node in enumerate(grid_path):
                if i % 10 == 0 or i == len(grid_path) - 1:
                    wp_list.append(node.to_position().tolist())
            result[did] = wp_list

        return result

    def _check_voronoi_conflict(self, drone_id: str, destination: np.ndarray) -> str:
        """
        Voronoi 셀을 활용하여 목적지가 다른 드론의 할당 셀에 진입하는지 확인.
        충돌하는 드론 ID를 반환, 없으면 빈 문자열.
        """
        if not self._voronoi_cells:
            return ""
        dest_2d = destination[:2]
        for owner_id, cell in self._voronoi_cells.items():
            if owner_id == drone_id:
                continue
            vertices = getattr(cell, "vertices", None)
            if vertices is None or len(vertices) < 3:
                continue
            # 점이 볼록 다각형 내부에 있는지 판정 (winding number)
            if _point_in_polygon(dest_2d, vertices):
                return owner_id
        return ""

    # ── 충돌 스캔 ────────────────────────────────────────────

    def _scan_conflicts(self, t: float) -> None:
        active = {did: d for did, d in self._active_drones.items()
                  if d.is_active}
        if len(active) < 2:
            return

        # 이미 어드바이저리가 발령된 쌍 추적
        covered: set[frozenset[str]] = set()
        for adv in self._advisories.values():
            if adv.conflict_pair:
                covered.add(frozenset([adv.target_drone_id, adv.conflict_pair]))

        # Spatial Hash로 근접 쌍만 추출 — O(N·k) (분리기준의 2배 범위)
        scan_radius = self._lat_min * 2.0
        self._spatial_hash.clear()
        for did, d in active.items():
            self._spatial_hash.insert(did, d.position)

        for id_a, id_b, cur_dist in self._spatial_hash.query_pairs_with_dist(scan_radius):
            pair = frozenset([id_a, id_b])
            if pair in covered:
                continue

            da = active[id_a]
            db = active[id_b]

            cpa_dist, cpa_t = closest_approach(
                da.position, da.velocity,
                db.position, db.velocity,
                lookahead_s=self._lookahead,
            )

            # 근접 경고 로그
            if cur_dist < self._near_lat:
                if self.analytics:
                    self.analytics.record_event("NEAR_MISS", t,
                                                drone_a=id_a, drone_b=id_b,
                                                dist_m=cur_dist)

            # 충돌 예측 → 어드바이저리 발령
            if cpa_dist < self._lat_min and cpa_t < self._lookahead:
                if self.analytics:
                    self.analytics.record_event("CONFLICT", t,
                                                drone_a=id_a, drone_b=id_b,
                                                cpa_dist_m=cpa_dist,
                                                cpa_t_s=cpa_t)
                # 낮은 우선순위 드론에 어드바이저리 발령
                target = self._pick_target(da, db)
                threat = db if target.drone_id == id_a else da
                adv = self.advisory_gen.generate(target, threat, cpa_dist, cpa_t, t)
                self._advisories[adv.advisory_id] = adv
                self.comm_bus.send(CommMessage(
                    sender_id="CONTROLLER",
                    receiver_id=target.drone_id,
                    payload=adv,
                    sent_time=t,
                    channel="advisory",
                ))
                covered.add(pair)
                if self.analytics:
                    self.analytics.record_event("ADVISORY_ISSUED", t,
                                                advisory_id=adv.advisory_id,
                                                target=target.drone_id,
                                                type=adv.advisory_type)

                # Dynamic rerouting: 위협 위치를 피해 경로 재계획
                if target.goal is not None:
                    blocked = position_to_grid(threat.position)
                    try:
                        reroute = self.planner.replan_avoiding(
                            drone_id=target.drone_id,
                            current_pos=target.position,
                            destination=target.goal,
                            blocked_node=blocked,
                        )
                        reroute_wps = [wp.position for wp in reroute.waypoints]
                        self.comm_bus.send(CommMessage(
                            sender_id="CONTROLLER",
                            receiver_id=target.drone_id,
                            payload=ClearanceResponse(
                                drone_id=target.drone_id,
                                approved=True,
                                assigned_waypoints=reroute_wps,
                                altitude_band=(30.0, 120.0),
                                timestamp_s=t,
                                reason="reroute_conflict_avoidance",
                            ),
                            sent_time=t,
                            channel="clearance",
                        ))
                    except Exception:
                        pass

    def _pick_target(self, da: DroneState, db: DroneState) -> DroneState:
        """어드바이저리를 받을 드론 선택 (낮은 우선순위)"""
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        pri_a = DRONE_PROFILES.get(da.profile_name,
                                    DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority
        pri_b = DRONE_PROFILES.get(db.profile_name,
                                    DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority
        return da if pri_a >= pri_b else db

    # ── 침입 탐지 ────────────────────────────────────────────

    def _detect_intruders(self, t: float) -> None:
        for did, drone in self._active_drones.items():
            if did in self._intruders:
                continue
            if getattr(drone, 'profile_name', '') == 'ROGUE':
                threat = self._threat_level(drone)
                alert = IntrusionAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
                    intruder_id=did,
                    detection_position=drone.position.copy(),
                    detection_time_s=t,
                    threat_level=threat,
                )
                self.comm_bus.send(CommMessage(
                    sender_id="CONTROLLER",
                    receiver_id="BROADCAST",
                    payload=alert,
                    sent_time=t,
                    channel="alert",
                ))
                self._intruders.add(did)
                if self.analytics:
                    self.analytics.record_event("INTRUSION_DETECTED", t,
                                                intruder_id=did,
                                                threat_level=threat)

    def _threat_level(self, intruder: DroneState) -> str:
        min_dist = min(
            (distance_3d(intruder.position, d.position)
             for d in self._active_drones.values()
             if d.drone_id != intruder.drone_id and d.is_active),
            default=9999.0,
        )
        if min_dist < 100.0:   return "CRITICAL"
        if min_dist < 300.0:   return "HIGH"
        if min_dist < 1000.0:  return "MEDIUM"
        return "LOW"

    # ── 어드바이저리 만료 ─────────────────────────────────────

    def _expire_advisories(self, t: float) -> None:
        expired = [aid for aid, adv in self._advisories.items()
                   if t > adv.timestamp_s + adv.duration_s]
        for aid in expired:
            del self._advisories[aid]

    # ── Voronoi 갱신 ─────────────────────────────────────────

    # ── 유틸리티 ─────────────────────────────────────────────

    def _refresh_voronoi(self) -> None:
        if not self._active_drones:
            return
        positions = {
            did: d.position.copy()
            for did, d in self._active_drones.items()
            if d.is_active
        }
        if len(positions) >= 3:
            bounds_m = max(
                abs(self.config.get("airspace", {})
                    .get("bounds_km", {}).get("x", [-5, 5])[1]) * 1000,
                5000.0,
            )
            bounds_dict = {
                "x": [-bounds_m, bounds_m],
                "y": [-bounds_m, bounds_m],
            }
            try:
                self._voronoi_cells = compute_voronoi_partition(
                    positions, bounds_dict
                )
            except Exception:
                pass


# ── 모듈 수준 유틸리티 ─────────────────────────────────────────

def _point_in_polygon(point: np.ndarray, vertices) -> bool:
    """
    2D Ray-casting 알고리즘으로 점이 다각형 내부에 있는지 판정.

    Parameters
    ----------
    point:    [x, y] ndarray
    vertices: iterable of [x, y] (polygon vertices in order)
    """
    px, py = float(point[0]), float(point[1])
    verts = [(float(v[0]), float(v[1])) for v in vertices]
    n = len(verts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = verts[i]
        xj, yj = verts[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside
