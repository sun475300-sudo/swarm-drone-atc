"""
Phase 509: Autonomous Landing System
정밀 착륙, 비상 착륙, 지형 적응형 접근.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class LandingMode(Enum):
    PRECISION = "precision"
    EMERGENCY = "emergency"
    AUTOROTATION = "autorotation"
    VERTICAL = "vertical"
    GLIDE = "glide"


class LandingPhase(Enum):
    APPROACH = "approach"
    FINAL = "final"
    FLARE = "flare"
    TOUCHDOWN = "touchdown"
    ROLLOUT = "rollout"
    COMPLETE = "complete"
    ABORTED = "aborted"


class SurfaceType(Enum):
    PAVED = "paved"
    GRASS = "grass"
    WATER = "water"
    ROOFTOP = "rooftop"
    MOVING_PLATFORM = "moving_platform"
    UNPREPARED = "unprepared"


@dataclass
class LandingZone:
    zone_id: str
    center: np.ndarray
    radius_m: float
    surface: SurfaceType
    elevation_m: float
    wind_knots: float = 0.0
    obstacles: int = 0
    available: bool = True


@dataclass
class LandingAttempt:
    drone_id: str
    zone_id: str
    mode: LandingMode
    phase: LandingPhase
    touchdown_error_m: float = 0.0
    sink_rate_ms: float = 0.0
    success: bool = False
    duration_s: float = 0.0


class GlidepathController:
    """3-degree glidepath tracking with ILS-like guidance."""

    def __init__(self, glide_angle_deg: float = 3.0, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.glide_angle = np.radians(glide_angle_deg)
        self.gain_lateral = 0.5
        self.gain_vertical = 0.8

    def compute_guidance(self, position: np.ndarray, target: np.ndarray,
                         velocity: np.ndarray) -> np.ndarray:
        to_target = target - position
        distance = np.linalg.norm(to_target[:2])
        desired_alt = target[2] + distance * np.tan(self.glide_angle)
        alt_error = desired_alt - position[2]
        lateral_error = np.cross(to_target[:2], velocity[:2]) / (np.linalg.norm(velocity[:2]) + 1e-8)

        cmd = np.zeros(3)
        cmd[:2] = to_target[:2] / (distance + 1e-8) * 5.0
        cmd[1] += -self.gain_lateral * lateral_error
        cmd[2] = self.gain_vertical * alt_error
        noise = self.rng.standard_normal(3) * 0.1
        return cmd + noise

    def is_on_glidepath(self, position: np.ndarray, target: np.ndarray,
                        tolerance_m: float = 5.0) -> bool:
        to_target = target - position
        distance = np.linalg.norm(to_target[:2])
        desired_alt = target[2] + distance * np.tan(self.glide_angle)
        return abs(position[2] - desired_alt) < tolerance_m


class TerrainAnalyzer:
    """Analyze landing zone suitability."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def assess_zone(self, zone: LandingZone) -> Dict:
        slope = self.rng.uniform(0, 15)
        roughness = self.rng.uniform(0, 1)
        surface_score = {
            SurfaceType.PAVED: 1.0, SurfaceType.ROOFTOP: 0.9,
            SurfaceType.GRASS: 0.7, SurfaceType.MOVING_PLATFORM: 0.6,
            SurfaceType.UNPREPARED: 0.4, SurfaceType.WATER: 0.2,
        }.get(zone.surface, 0.5)

        obstacle_penalty = min(0.5, zone.obstacles * 0.1)
        wind_penalty = min(0.3, zone.wind_knots / 50)
        score = surface_score * (1 - obstacle_penalty) * (1 - wind_penalty)
        score *= max(0.5, 1 - slope / 30)
        score *= max(0.5, 1 - roughness * 0.3)

        return {
            "zone_id": zone.zone_id,
            "score": round(score, 3),
            "slope_deg": round(slope, 1),
            "roughness": round(roughness, 3),
            "surface_score": surface_score,
            "suitable": score > 0.5,
        }


class AutonomousLanding:
    """Complete autonomous landing management system."""

    def __init__(self, n_zones: int = 8, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.glidepath = GlidepathController(seed=seed)
        self.terrain = TerrainAnalyzer(seed)
        self.zones: Dict[str, LandingZone] = {}
        self.attempts: List[LandingAttempt] = []

        surfaces = list(SurfaceType)
        for i in range(n_zones):
            center = self.rng.uniform(-500, 500, 3)
            center[2] = self.rng.uniform(0, 50)
            zone = LandingZone(
                f"LZ-{i:03d}", center, self.rng.uniform(5, 30),
                self.rng.choice(surfaces), center[2],
                self.rng.uniform(0, 25), self.rng.integers(0, 5))
            self.zones[zone.zone_id] = zone

    def select_zone(self, drone_pos: np.ndarray,
                    mode: LandingMode = LandingMode.PRECISION) -> Optional[str]:
        best_id = None
        best_score = -1
        for zid, zone in self.zones.items():
            if not zone.available:
                continue
            assessment = self.terrain.assess_zone(zone)
            if not assessment["suitable"] and mode != LandingMode.EMERGENCY:
                continue
            dist = np.linalg.norm(drone_pos - zone.center)
            dist_score = max(0, 1 - dist / 2000)
            total = assessment["score"] * 0.6 + dist_score * 0.4
            if mode == LandingMode.EMERGENCY:
                total = dist_score * 0.8 + assessment["score"] * 0.2
            if total > best_score:
                best_score = total
                best_id = zid
        return best_id

    def execute_landing(self, drone_id: str, zone_id: str,
                        mode: LandingMode = LandingMode.PRECISION) -> LandingAttempt:
        zone = self.zones.get(zone_id)
        if not zone:
            return LandingAttempt(drone_id, zone_id, mode, LandingPhase.ABORTED)

        start_pos = zone.center + self.rng.uniform(-50, 50, 3)
        start_pos[2] = zone.elevation_m + self.rng.uniform(30, 80)
        pos = start_pos.copy()
        vel = np.zeros(3)
        dt = 0.1
        time_elapsed = 0.0
        phase = LandingPhase.APPROACH

        for step in range(1000):
            cmd = self.glidepath.compute_guidance(pos, zone.center, vel)
            vel = vel * 0.95 + cmd * dt
            pos = pos + vel * dt
            time_elapsed += dt

            alt_above = pos[2] - zone.elevation_m
            if phase == LandingPhase.APPROACH and alt_above < 10:
                phase = LandingPhase.FINAL
            elif phase == LandingPhase.FINAL and alt_above < 3:
                phase = LandingPhase.FLARE
                vel[2] *= 0.5
            elif phase == LandingPhase.FLARE and alt_above < 0.5:
                phase = LandingPhase.TOUCHDOWN
                break

        error = np.linalg.norm(pos[:2] - zone.center[:2])
        sink = abs(vel[2])
        success = error < zone.radius_m and sink < 2.0

        if success:
            phase = LandingPhase.COMPLETE

        attempt = LandingAttempt(drone_id, zone_id, mode, phase,
                                round(error, 2), round(sink, 3),
                                success, round(time_elapsed, 1))
        self.attempts.append(attempt)
        return attempt

    def emergency_land(self, drone_id: str, drone_pos: np.ndarray) -> LandingAttempt:
        zone_id = self.select_zone(drone_pos, LandingMode.EMERGENCY)
        if not zone_id:
            return LandingAttempt(drone_id, "NONE", LandingMode.EMERGENCY, LandingPhase.ABORTED)
        return self.execute_landing(drone_id, zone_id, LandingMode.EMERGENCY)

    def summary(self) -> Dict:
        return {
            "zones": len(self.zones),
            "attempts": len(self.attempts),
            "successes": sum(1 for a in self.attempts if a.success),
            "success_rate": round(
                sum(1 for a in self.attempts if a.success) / max(len(self.attempts), 1), 4),
            "avg_error_m": round(
                np.mean([a.touchdown_error_m for a in self.attempts]) if self.attempts else 0, 2),
        }
