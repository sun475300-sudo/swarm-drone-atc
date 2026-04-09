"""Phase 312: Real-time 3D Physics Engine v2 — 실시간 3D 물리 엔진 v2.

Verlet 적분, 강체 역학, 충돌 응답, 바람/중력 외력 모델링.
다중 드론 동시 물리 시뮬레이션.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class RigidBody:
    body_id: str
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    prev_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    mass: float = 2.0
    radius: float = 1.0
    restitution: float = 0.5  # bounciness
    drag_coeff: float = 0.1
    is_static: bool = False


@dataclass
class ForceField:
    name: str
    direction: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, -9.81]))
    strength: float = 1.0
    position: Optional[np.ndarray] = None  # None = uniform, else point source
    radius: float = float("inf")


@dataclass
class CollisionInfo:
    body_a: str
    body_b: str
    contact_point: np.ndarray
    normal: np.ndarray
    penetration: float
    impulse: float


class RealtimePhysicsV2:
    """실시간 3D 물리 엔진 v2.

    - Verlet 적분 (수치 안정성)
    - 구-구 충돌 감지 및 응답
    - 외력 필드 (중력, 바람, 포인트 소스)
    - 바운딩 박스 경계 조건
    """

    def __init__(self, dt: float = 0.01, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.dt = dt
        self._bodies: Dict[str, RigidBody] = {}
        self._forces: List[ForceField] = []
        self._collisions: List[CollisionInfo] = []
        self._step_count = 0
        self._bounds_min = np.array([-1000, -1000, 0])
        self._bounds_max = np.array([1000, 1000, 500])
        # Default gravity
        self._forces.append(ForceField(name="gravity", direction=np.array([0, 0, -9.81])))

    def add_body(self, body: RigidBody):
        body.prev_position = body.position.copy()
        self._bodies[body.body_id] = body

    def remove_body(self, body_id: str) -> bool:
        return self._bodies.pop(body_id, None) is not None

    def add_force_field(self, force: ForceField):
        self._forces.append(force)

    def set_bounds(self, min_bounds: np.ndarray, max_bounds: np.ndarray):
        self._bounds_min = min_bounds.copy()
        self._bounds_max = max_bounds.copy()

    def apply_force(self, body_id: str, force: np.ndarray):
        body = self._bodies.get(body_id)
        if body and not body.is_static:
            body.acceleration += force / body.mass

    def step(self):
        """Advance physics by one timestep using Verlet integration."""
        self._collisions.clear()
        dt = self.dt
        dt2 = dt * dt

        # Accumulate forces
        for body in self._bodies.values():
            if body.is_static:
                continue
            body.acceleration = np.zeros(3)
            for ff in self._forces:
                if ff.position is None:
                    # Uniform field
                    body.acceleration += ff.direction * ff.strength
                else:
                    # Point source
                    diff = ff.position - body.position
                    dist = np.linalg.norm(diff)
                    if 0 < dist < ff.radius:
                        body.acceleration += (diff / dist) * ff.strength / max(dist, 1.0)
            # Drag
            speed = np.linalg.norm(body.velocity)
            if speed > 0.01:
                drag = -body.drag_coeff * body.velocity * speed
                body.acceleration += drag / body.mass

        # Verlet integration
        for body in self._bodies.values():
            if body.is_static:
                continue
            new_pos = 2 * body.position - body.prev_position + body.acceleration * dt2
            body.velocity = (new_pos - body.position) / dt
            body.prev_position = body.position.copy()
            body.position = new_pos

        # Collision detection & response
        bodies_list = [b for b in self._bodies.values() if not b.is_static]
        for i in range(len(bodies_list)):
            for j in range(i + 1, len(bodies_list)):
                self._check_collision(bodies_list[i], bodies_list[j])

        # Boundary enforcement
        for body in self._bodies.values():
            if body.is_static:
                continue
            for k in range(3):
                if body.position[k] < self._bounds_min[k] + body.radius:
                    body.position[k] = self._bounds_min[k] + body.radius
                    body.velocity[k] = abs(body.velocity[k]) * body.restitution
                    body.prev_position[k] = body.position[k] - body.velocity[k] * dt
                elif body.position[k] > self._bounds_max[k] - body.radius:
                    body.position[k] = self._bounds_max[k] - body.radius
                    body.velocity[k] = -abs(body.velocity[k]) * body.restitution
                    body.prev_position[k] = body.position[k] - body.velocity[k] * dt

        self._step_count += 1

    def _check_collision(self, a: RigidBody, b: RigidBody):
        diff = b.position - a.position
        dist = np.linalg.norm(diff)
        min_dist = a.radius + b.radius

        if dist < min_dist and dist > 1e-6:
            normal = diff / dist
            penetration = min_dist - dist

            # Resolve overlap
            total_mass = a.mass + b.mass
            a.position -= normal * (penetration * b.mass / total_mass)
            b.position += normal * (penetration * a.mass / total_mass)

            # Impulse-based response
            rel_vel = a.velocity - b.velocity
            vel_along_normal = np.dot(rel_vel, normal)
            if vel_along_normal > 0:
                return  # separating

            e = min(a.restitution, b.restitution)
            j = -(1 + e) * vel_along_normal / (1 / a.mass + 1 / b.mass)

            a.velocity += (j / a.mass) * normal
            b.velocity -= (j / b.mass) * normal

            contact = (a.position + b.position) / 2
            self._collisions.append(CollisionInfo(
                body_a=a.body_id, body_b=b.body_id,
                contact_point=contact, normal=normal,
                penetration=penetration, impulse=abs(j),
            ))

    def run_for(self, duration_sec: float):
        steps = int(duration_sec / self.dt)
        for _ in range(steps):
            self.step()

    def get_body(self, body_id: str) -> Optional[RigidBody]:
        return self._bodies.get(body_id)

    def get_kinetic_energy(self) -> float:
        return sum(0.5 * b.mass * np.dot(b.velocity, b.velocity)
                   for b in self._bodies.values() if not b.is_static)

    def get_collisions(self) -> List[CollisionInfo]:
        return self._collisions.copy()

    def summary(self) -> dict:
        return {
            "total_bodies": len(self._bodies),
            "static_bodies": sum(1 for b in self._bodies.values() if b.is_static),
            "force_fields": len(self._forces),
            "step_count": self._step_count,
            "collisions_last_step": len(self._collisions),
            "kinetic_energy": round(self.get_kinetic_energy(), 4),
        }
