"""
시뮬레이션 상태 도메인 객체.

SimState: Dash 시각화와 백그라운드 시뮬레이션 스레드가 공유하는 스레드-안전 상태.
"""

from __future__ import annotations

import threading

import numpy as np

from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from visualization.metrics_stream import MetricsCollector
from simulation.threat_assessment import ThreatAssessmentEngine
from simulation.multi_controller import MultiControllerManager
from simulation.sla_monitor import SLAMonitor
from simulation.event_timeline import EventTimeline
from visualization._scene_traces import BOUNDS_M, CRUISE_ALT, _PAD_LIST


class SimState:
    """스레드 공유 시뮬레이션 상태"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.drones: dict[str, DroneState] = {}
        self.trails: dict[str, list[tuple]] = {}
        self.trail_len = 40

        self.t = 0.0
        self.dt = 0.1
        self.running = False

        self.wind = np.zeros(3)
        self.n_drones = 30
        self.speed_multiplier = 1.0  # 시뮬레이션 속도 배율 (0.25x ~ 5x)
        self.rng = np.random.default_rng(42)  # 재현성 보장 RNG
        self.show_apf_field = False  # APF 벡터 필드 표시 여부

        # 통계
        self.conflicts = 0
        self.near_misses = 0
        self.advisories = 0
        self.collisions = 0

        # 메트릭 수집기
        self.metrics = MetricsCollector(max_history=600)

        # 동적 NFZ 목록 (런타임 추가/제거)
        self.dynamic_nfzs: dict[str, dict] = {}  # id -> {x_range, y_range, z_range}

        # 위협 평가 엔진
        self.threat_engine = ThreatAssessmentEngine()
        self.threat_matrix: dict = {}

        # 다중 관제 구역
        self.sector_mgr = MultiControllerManager(bounds=BOUNDS_M, n_sectors=4)

        # SLA 모니터
        self.sla_monitor = SLAMonitor()
        self.sla_violations: list[dict] = []

        # 이벤트 타임라인
        self.timeline = EventTimeline()

        # 성능 모니터
        self.tick_times_ms: list[float] = []
        self.max_tick_history = 300

    def reset(self, n_drones: int | None = None) -> None:
        if n_drones is not None:
            self.n_drones = n_drones

        self.rng = np.random.default_rng(42)
        rng = self.rng
        profiles = ["COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY", "RECREATIONAL"]
        weights   = [0.55, 0.25, 0.10, 0.10]

        drones: dict[str, DroneState] = {}
        trails: dict[str, list] = {}

        for i in range(self.n_drones):
            pad = _PAD_LIST[i % len(_PAD_LIST)].copy()
            jitter = rng.uniform(-300, 300, 3) * np.array([1, 1, 0])
            start = (pad + jitter).copy()
            start[2] = 0.0
            start[0] = float(np.clip(start[0], -BOUNDS_M + 200, BOUNDS_M - 200))
            start[1] = float(np.clip(start[1], -BOUNDS_M + 200, BOUNDS_M - 200))

            # 반대편으로 목적지 배정
            goal_pad = _PAD_LIST[(i + len(_PAD_LIST) // 2) % len(_PAD_LIST)].copy()
            goal = goal_pad.copy()
            goal[2] = CRUISE_ALT
            # NFZ 통과 회피: 목적지를 NFZ 밖으로 조정
            if abs(goal[0]) < 700 and abs(goal[1]) < 700:
                goal[0] += float(rng.choice([-900.0, 900.0]))

            profile = str(rng.choice(profiles, p=weights))
            drone_id = f"DR{i:03d}"

            d = DroneState(
                drone_id=drone_id,
                position=start.copy(),
                velocity=np.zeros(3),
                profile_name=profile,
                flight_phase=FlightPhase.GROUNDED,
                battery_pct=float(rng.uniform(70, 100)),
            )
            d.goal = goal
            drones[drone_id] = d
            trails[drone_id] = []

        with self.lock:
            self.drones = drones
            self.trails = trails
            self.t = 0.0
            self.conflicts = 0
            self.near_misses = 0
            self.advisories = 0
            self.collisions = 0
            self.dynamic_nfzs = {}
            self.metrics.reset()
            self.threat_engine.clear()
            self.threat_matrix = {}
            self.sector_mgr = MultiControllerManager(bounds=BOUNDS_M, n_sectors=4)
            self.sla_monitor = SLAMonitor()
            self.sla_violations = []
            self.timeline = EventTimeline()
            self.tick_times_ms = []
