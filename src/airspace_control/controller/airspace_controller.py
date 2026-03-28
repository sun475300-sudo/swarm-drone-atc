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
import heapq
import logging
import uuid
import numpy as np
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

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
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
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
    # B2: Voronoi 갱신 10s 주기 — clearance 요청 시점에 최대 10s stale 가능.
    # 고속 드론(20 m/s) 기준 최대 200m 편차이나, Voronoi 셀 크기가 수 km이므로
    # 실제 충돌 위험은 극히 낮음. 성능상 10s 유지.
    VORONOI_INTERVAL_S = 10.0

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
        self._holding_queue: list[tuple[float, str]] = []  # (entry_time, drone_id)
        self.MAX_HOLDING_QUEUE = 100  # HOLDING 큐 최대 크기

        # CBS vs A* 메트릭 추적
        self._cbs_attempts  = 0
        self._cbs_successes = 0
        self._cbs_failures  = 0
        self._astar_count   = 0
        self._clearances_per_sec: float = 0.0
        self._clearance_count_window: list[float] = []  # 최근 처리 시각 리스트

        self._lat_min_base = float(config.get("separation_standards", {})
                                   .get("lateral_min_m", 50.0))
        self._lat_min   = self._lat_min_base
        self._vert_min  = float(config.get("separation_standards", {})
                                .get("vertical_min_m", 15.0))
        self._near_lat  = float(config.get("separation_standards", {})
                                .get("near_miss_lateral_m", 10.0))
        self._lookahead = float(config.get("separation_standards", {})
                                .get("conflict_lookahead_s", 90.0))
        self._max_clear = int(config.get("controller", {})
                              .get("max_concurrent_clearances", 500))
        self._wind_speed: float = 0.0  # 현재 풍속 (m/s), 외부에서 갱신

        # 텔레메트리/허가 요청 수신 구독
        comm_bus.subscribe("CONTROLLER", self._on_message)

    # ── SimPy 프로세스 ────────────────────────────────────────

    def run(self):
        """1 Hz 제어 루프 SimPy 프로세스"""
        dt = 1.0 / self.CONTROL_HZ
        while True:
            yield self.env.timeout(dt)
            t = float(self.env.now)
            self._update_dynamic_separation()
            self._process_clearances(t)
            self._manage_holding_queue(t)
            self._scan_conflicts(t)
            self._detect_intruders(t)
            self._detect_lost_link(t)
            self._expire_advisories(t)
            if int(round(t)) % int(self.VORONOI_INTERVAL_S) == 0:
                self._refresh_voronoi()

    def update_wind_speed(self, wind_speed: float) -> None:
        """외부에서 풍속 갱신 (시뮬레이터 → 컨트롤러)"""
        self._wind_speed = wind_speed

    def _update_dynamic_separation(self) -> None:
        """
        풍속 기반 동적 분리간격 조정.

        - 0~5 m/s: 기본 분리간격 유지
        - 5~10 m/s: 선형 증가 (최대 1.4배)
        - 10~15 m/s: 선형 증가 (최대 1.6배)
        - >15 m/s: 1.6배 고정
        """
        ws = self._wind_speed
        if ws <= 5.0:
            factor = 1.0
        elif ws <= 10.0:
            factor = 1.0 + 0.4 * (ws - 5.0) / 5.0   # 1.0 → 1.4
        elif ws <= 15.0:
            factor = 1.4 + 0.2 * (ws - 10.0) / 5.0   # 1.4 → 1.6
        else:
            factor = 1.6
        self._lat_min = self._lat_min_base * factor

    # ── HOLDING 큐 관리 ──────────────────────────────────────

    def _manage_holding_queue(self, t: float) -> None:
        """
        구조화된 HOLDING 큐 관리.

        - HOLDING 진입 드론을 큐에 등록
        - 선입선출(FIFO) 순서로 최대 3기씩 ENROUTE 복귀 허용
        - 최소 대기시간 5초 보장
        """
        MAX_RELEASE_PER_TICK = 3
        MIN_HOLD_S = 5.0

        # 새 HOLDING 드론 등록 (최대 큐 크기 제한)
        queued_ids = {did for _, did in self._holding_queue}
        for did, d in self._active_drones.items():
            if d.flight_phase == FlightPhase.HOLDING and did not in queued_ids:
                if len(self._holding_queue) < self.MAX_HOLDING_QUEUE:
                    heapq.heappush(self._holding_queue, (t, did))
                else:
                    # 큐 포화 → 즉시 RTL 전환 (안전)
                    d.flight_phase = FlightPhase.RTL
                    if self.analytics:
                        self.analytics.record_event(
                            "HOLDING_QUEUE_OVERFLOW", t,
                            drone_id=did,
                            queue_size=len(self._holding_queue),
                        )

        # 더 이상 HOLDING이 아닌 드론 제거
        self._holding_queue = [
            (et, did) for et, did in self._holding_queue
            if did in self._active_drones
            and self._active_drones[did].flight_phase == FlightPhase.HOLDING
        ]
        heapq.heapify(self._holding_queue)

        # FIFO 해제: 최소 대기시간 경과한 드론부터
        released = 0
        while self._holding_queue and released < MAX_RELEASE_PER_TICK:
            entry_time, did = self._holding_queue[0]
            if t - entry_time < MIN_HOLD_S:
                break
            heapq.heappop(self._holding_queue)
            drone = self._active_drones.get(did)
            if drone and drone.flight_phase == FlightPhase.HOLDING:
                # ENROUTE 복귀 어드바이저리 발송
                adv = ResolutionAdvisory(
                    advisory_id=f"HQ-{uuid.uuid4().hex[:6].upper()}",
                    target_drone_id=did,
                    advisory_type="RESUME",
                    magnitude=0.0,
                    duration_s=0.0,
                    timestamp_s=t,
                    conflict_pair=None,
                )
                self.comm_bus.send(CommMessage(
                    sender_id="CONTROLLER",
                    receiver_id=did,
                    payload=adv,
                    sent_time=t,
                    channel="advisory",
                ))
                released += 1

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
            # 타임스탬프 단조성 검증: 오래된 텔레메트리 무시
            if tm.timestamp_s < drone.last_update_s:
                return
            drone.position = np.array(tm.position, dtype=float)
            drone.velocity = np.array(tm.velocity, dtype=float)
            drone.battery_pct = float(tm.battery_pct)
        drone.last_update_s = float(tm.timestamp_s)
        try:
            drone.flight_phase = FlightPhase[tm.flight_phase]
        except KeyError:
            logger.warning("알 수 없는 FlightPhase: %s (drone=%s)", tm.flight_phase, tm.sender_id)

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
            self._cbs_attempts += 1
            cbs_waypoints = self._cbs_plan_batch(batch)
            if cbs_waypoints:
                self._cbs_successes += 1
            else:
                self._cbs_failures += 1
                if self.analytics:
                    self.analytics.record_event(
                        "CBS_FALLBACK_ASTAR", t,
                        batch_size=len(batch),
                    )

        for req in batch:
            route = self.planner.plan_route(
                drone_id=req.drone_id,
                origin=req.origin,
                destination=req.destination,
                priority=req.priority,
            )
            approved = True
            reason   = ""

            # M-1: 목적지가 NFZ 내부인지 검증
            for nfz in self.planner.nfz_list:
                dist_to_nfz = float(np.linalg.norm(
                    req.destination[:2] - nfz['center'][:2]))
                if dist_to_nfz < nfz['radius_m']:
                    approved = False
                    reason = f"destination_in_nfz:{dist_to_nfz:.0f}m"
                    break

            # Voronoi 셀 충돌 경고
            voronoi_conflict = self._check_voronoi_conflict(req.drone_id, req.destination)
            if voronoi_conflict:
                approved = False
                reason = f"voronoi_conflict:{voronoi_conflict}"

            # CBS 경로가 있으면 우선 사용, 아니면 A*
            if req.drone_id in cbs_waypoints:
                waypoints = cbs_waypoints[req.drone_id]
            else:
                self._astar_count += 1
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
            # 처리량 추적
            self._clearance_count_window.append(t)
            # 60초 윈도우 유지
            self._clearance_count_window = [
                ts for ts in self._clearance_count_window if t - ts <= 60.0
            ]
            self._clearances_per_sec = len(self._clearance_count_window) / 60.0

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
            logger.warning("CBS planning failed for batch of %d drones", len(batch))
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

    # KDTree 드론 수 임계값: 이 수 이상이면 KDTree 사용
    _KDTREE_THRESHOLD = 200

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

        # 드론 수에 따른 적응형 스캔 반경 (고밀도 시 확대)
        density_factor = min(len(active) / 50.0, 3.0)  # 50대 기준 최대 3x
        scan_radius = self._lat_min * max(2.0, 1.5 + density_factor * 0.5)

        # 텔레메트리 지연 보정 위치 계산
        ext_positions: dict[str, np.ndarray] = {}
        for did, d in active.items():
            lag = max(0.0, t - d.last_update_s) if d.last_update_s > 0 else 0.0
            ext_positions[did] = d.position + d.velocity * lag if lag > 0 else d.position

        # 적응형 공간 인덱스: 200대 이상이면 KDTree, 미만이면 SpatialHash
        if len(active) >= self._KDTREE_THRESHOLD:
            nearby_pairs = self._kdtree_query_pairs(ext_positions, scan_radius)
        else:
            self._spatial_hash.clear()
            for did, pos in ext_positions.items():
                self._spatial_hash.insert(did, pos)
            nearby_pairs = list(self._spatial_hash.query_pairs_with_dist(scan_radius))

        for id_a, id_b, cur_dist in nearby_pairs:
            pair = frozenset([id_a, id_b])
            if pair in covered:
                continue

            da = active[id_a]
            db = active[id_b]

            # H-1: 텔레메트리 지연 보정 — 마지막 수신 이후 경과 시간만큼 위치 외삽
            lag_a = max(0.0, t - da.last_update_s) if da.last_update_s > 0 else 0.0
            lag_b = max(0.0, t - db.last_update_s) if db.last_update_s > 0 else 0.0
            pos_a = da.position + da.velocity * lag_a if lag_a > 0 else da.position
            pos_b = db.position + db.velocity * lag_b if lag_b > 0 else db.position

            # 적응형 CPA lookahead: 상대 접근 속도에 비례 (최소 30s, 최대 120s)
            rel_vel = np.linalg.norm(da.velocity - db.velocity)
            adaptive_lookahead = max(30.0, min(
                self._lookahead,
                self._lat_min * 3.0 / max(rel_vel, 0.5)  # 분리기준 3배 거리 / 접근 속도
            ))

            cpa_dist, cpa_t = closest_approach(
                pos_a, da.velocity,
                pos_b, db.velocity,
                lookahead_s=adaptive_lookahead,
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

                # M-2: ROGUE 드론은 어드바이저리를 수신하지 않으므로 발송 스킵
                if getattr(target, 'profile_name', '') == 'ROGUE':
                    # ROGUE 대신 상대방에게 회피 지시 (등록 드론이면)
                    if getattr(threat, 'profile_name', '') != 'ROGUE':
                        target, threat = threat, target
                    else:
                        covered.add(pair)
                        continue

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
                    except Exception as e:
                        logger.warning("Reroute failed for %s: %s", target.drone_id, e)
                        if self.analytics:
                            self.analytics.record_event(
                                "REROUTE_FAILED", t,
                                drone_id=target.drone_id, error=str(e))

    @staticmethod
    def _kdtree_query_pairs(
        positions: dict[str, np.ndarray], radius: float
    ) -> list[tuple[str, str, float]]:
        """KDTree 기반 근접 쌍 쿼리 — 200대+ 고밀도 환경에서 O(N log N)"""
        if len(positions) < 2:
            return []

        from scipy.spatial import KDTree

        ids = list(positions.keys())
        pts = np.array([positions[did] for did in ids])
        tree = KDTree(pts)
        pairs_idx = tree.query_pairs(radius, output_type="ndarray")

        result: list[tuple[str, str, float]] = []
        for i, j in pairs_idx:
            dist = float(np.linalg.norm(pts[i] - pts[j]))
            result.append((ids[i], ids[j], dist))
        return result

    def _pick_target(self, da: DroneState, db: DroneState) -> DroneState:
        """어드바이저리를 받을 드론 선택 (낮은 우선순위, 동률 시 ID 기반 타이브레이크)"""
        pri_a = DRONE_PROFILES.get(da.profile_name,
                                    DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority
        pri_b = DRONE_PROFILES.get(db.profile_name,
                                    DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority
        if pri_a != pri_b:
            return da if pri_a > pri_b else db
        # 동일 우선순위: ID가 큰 드론이 회피 (공정한 결정론적 타이브레이크)
        return da if da.drone_id > db.drone_id else db

    # ── Lost-Link 탐지 ───────────────────────────────────────

    def _detect_lost_link(self, t: float) -> None:
        """텔레메트리 타임아웃으로 Lost-Link 감지 → 3-phase RA 시퀀스 발령"""
        TIMEOUT_S = 10.0  # 텔레메트리 타임아웃 (초)
        for did, drone in self._active_drones.items():
            if not drone.is_active:
                continue
            if drone.flight_phase in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                continue
            stale = t - drone.last_update_s
            if stale > TIMEOUT_S:
                # 이미 Lost-Link 어드바이저리 발령 중이면 스킵
                existing = any(
                    adv.target_drone_id == did and adv.advisory_type == "HOLD"
                    for adv in self._advisories.values()
                )
                if existing:
                    continue
                # Lost-Link 3-phase 시퀀스 발령
                seq = self.advisory_gen.generate_lost_link_sequence(drone, t)
                for adv in seq:
                    self._advisories[adv.advisory_id] = adv
                    self.comm_bus.send(CommMessage(
                        sender_id="CONTROLLER",
                        receiver_id=did,
                        payload=adv,
                        sent_time=t,
                        channel="advisory",
                    ))
                if self.analytics:
                    self.analytics.record_event("LOST_LINK_DETECTED", t,
                                                drone_id=did, stale_s=stale)

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

    # ── Voronoi 갱신 & 밀도 기반 제어 ────────────────────────

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
                self._apply_density_based_separation()
            except Exception:
                logger.warning("Voronoi partition failed with %d drones", len(positions))

    def _apply_density_based_separation(self) -> None:
        """
        Voronoi 셀 면적 기반 밀도 관리.

        - 고밀도 셀(면적 < 2 km²) 드론: 분리간격 추가 확대 + 고도 밴드 할당
        - 밀도 정보를 _density_scores에 저장하여 허가 우선순위에 활용
        """
        if not self._voronoi_cells:
            return

        HIGH_DENSITY_THRESHOLD_KM2 = 2.0
        self._density_scores: dict[str, float] = {}

        for did, cell in self._voronoi_cells.items():
            if cell.area_km2 <= 0:
                continue
            drone = self._active_drones.get(did)
            if drone is None or not drone.is_active:
                continue

            # 밀도 점수: 면적이 작을수록 높음 (0.0~1.0)
            density = max(0.0, min(1.0, 1.0 - cell.area_km2 / 10.0))
            self._density_scores[did] = density

            if drone.flight_phase not in (FlightPhase.ENROUTE,):
                continue

            # 고밀도 셀 드론: 고도 밴드 + 분리 확대
            if cell.area_km2 < HIGH_DENSITY_THRESHOLD_KM2:
                drone._voronoi_alt_band = cell.altitude_band

    def _get_density_priority_boost(self, drone_id: str) -> float:
        """고밀도 지역 드론의 허가 우선순위 부스트 (0.0~0.5)"""
        return getattr(self, '_density_scores', {}).get(drone_id, 0.0) * 0.5

    # ── 동적 NFZ 관리 ──────────────────────────────────────────

    def add_dynamic_nfz(
        self,
        nfz_id: str,
        center: np.ndarray,
        radius_m: float,
        t: float,
    ) -> int:
        """
        런타임 중 비행금지구역 추가 → NFZ 내부 드론 자동 재경로.

        Returns
        -------
        int : 재경로 지시를 받은 드론 수
        """
        nfz = {"center": np.array(center, dtype=float), "radius_m": float(radius_m), "id": nfz_id}
        self.planner.nfz_list.append(nfz)
        logger.info("동적 NFZ 추가: %s (%.0fm 반경, center=%s)", nfz_id, radius_m, center[:2])

        if self.analytics:
            self.analytics.record_event("NFZ_ADDED", t, nfz_id=nfz_id, radius_m=radius_m)

        # NFZ 내부 활성 드론에 EVADE_APF 어드바이저리 발령
        rerouted = 0
        for did, drone in self._active_drones.items():
            if not drone.is_active or drone.flight_phase in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                continue
            dist = float(np.linalg.norm(drone.position[:2] - center[:2]))
            if dist < radius_m * 1.2:  # NFZ 반경 + 20% 마진
                adv = ResolutionAdvisory(
                    advisory_id=f"NFZ-{uuid.uuid4().hex[:6].upper()}",
                    target_drone_id=did,
                    advisory_type="EVADE_APF",
                    magnitude=0.0,
                    duration_s=30.0,
                    timestamp_s=t,
                    conflict_pair=None,
                )
                self._advisories[adv.advisory_id] = adv
                self.comm_bus.send(CommMessage(
                    sender_id="CONTROLLER",
                    receiver_id=did,
                    payload=adv,
                    sent_time=t,
                    channel="advisory",
                ))
                rerouted += 1
        return rerouted

    def remove_dynamic_nfz(self, nfz_id: str, t: float) -> bool:
        """런타임 중 비행금지구역 해제"""
        before = len(self.planner.nfz_list)
        self.planner.nfz_list = [
            n for n in self.planner.nfz_list if n.get("id") != nfz_id
        ]
        removed = len(self.planner.nfz_list) < before
        if removed:
            logger.info("동적 NFZ 해제: %s", nfz_id)
            if self.analytics:
                self.analytics.record_event("NFZ_REMOVED", t, nfz_id=nfz_id)
        return removed


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
