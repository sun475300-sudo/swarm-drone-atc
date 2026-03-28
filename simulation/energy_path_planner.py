"""
에너지 최적 경로 계획
=====================
풍향/고도/속도를 고려한 에너지 최소 비용 A* 경로 탐색.
충전소 경유 자동 계획 포함.

사용법:
    planner = EnergyPathPlanner(wind_vector=np.array([5, 0, 0]))
    path, cost = planner.plan(start, goal)
    path_with_charge = planner.plan_with_charging(start, goal, battery_wh=50)
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(order=True)
class _Node:
    """A* 노드"""
    f_cost: float
    g_cost: float = field(compare=False)
    position: tuple[float, float, float] = field(compare=False)
    parent: Optional["_Node"] = field(default=None, compare=False)


class EnergyPathPlanner:
    """
    에너지 최적 경로 계획기.

    그리드 기반 A*에 에너지 비용 함수를 적용.
    풍향, 고도, 속도에 따른 전력 소모를 비용으로 사용.
    """

    def __init__(
        self,
        grid_resolution: float = 200.0,
        bounds: float = 5000.0,
        alt_min: float = 30.0,
        alt_max: float = 120.0,
        alt_step: float = 30.0,
        wind_vector: np.ndarray | None = None,
        cruise_speed: float = 10.0,
        no_fly_zones: list[dict] | None = None,
        charging_stations: list[np.ndarray] | None = None,
    ) -> None:
        self.grid_res = grid_resolution
        self.bounds = bounds
        self.alt_min = alt_min
        self.alt_max = alt_max
        self.alt_step = alt_step
        self.wind = wind_vector if wind_vector is not None else np.zeros(3)
        self.cruise_speed = cruise_speed
        self.nfzs = no_fly_zones or []
        self.charging_stations = charging_stations or []

    def _snap(self, pos: np.ndarray) -> tuple[float, float, float]:
        """위치를 그리드에 스냅"""
        r = self.grid_res
        x = round(pos[0] / r) * r
        y = round(pos[1] / r) * r
        z = round(pos[2] / self.alt_step) * self.alt_step
        z = max(self.alt_min, min(z, self.alt_max))
        return (x, y, z)

    def _in_nfz(self, pos: tuple[float, float, float]) -> bool:
        """NFZ 내부 판정"""
        for nfz in self.nfzs:
            xr = nfz.get("x_range", (-500, 500))
            yr = nfz.get("y_range", (-500, 500))
            if xr[0] <= pos[0] <= xr[1] and yr[0] <= pos[1] <= yr[1]:
                return True
        return False

    def _energy_cost(
        self,
        from_pos: tuple[float, float, float],
        to_pos: tuple[float, float, float],
    ) -> float:
        """
        두 지점 간 에너지 비용 (Wh).

        고도 변화, 풍향, 거리를 반영.
        """
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        dz = to_pos[2] - from_pos[2]
        dist_h = math.sqrt(dx * dx + dy * dy)
        dist_3d = math.sqrt(dist_h * dist_h + dz * dz)

        if dist_3d < 0.01:
            return 0.0

        # 기본 호버 전력
        p_hover = 50.0  # W
        # 이동 전력 (드래그)
        p_drag = 0.5 * self.cruise_speed ** 2

        # 풍향 효과: 역풍이면 비용 증가, 순풍이면 감소
        if dist_h > 0.01:
            direction = np.array([dx, dy, 0.0]) / dist_h
            headwind = -float(np.dot(self.wind[:2], direction[:2]))
            wind_factor = 1.0 + headwind * 0.05  # 역풍 1m/s당 5% 증가
        else:
            wind_factor = 1.0

        # 고도 변화 비용
        if dz > 0:
            p_climb = dz * 25.0  # 상승: 25 W/m
        else:
            p_climb = dz * 5.0   # 하강: 회수 5 W/m

        # 고도 보정
        alt_factor = 1.0 + from_pos[2] * 0.00012

        # 총 에너지 (Wh)
        travel_time_s = dist_3d / max(self.cruise_speed, 1.0)
        power_w = max(0.0, (p_hover + p_drag) * wind_factor * alt_factor)
        energy_wh = power_w * travel_time_s / 3600.0 + abs(p_climb) / 3600.0

        return energy_wh

    def _heuristic(
        self,
        pos: tuple[float, float, float],
        goal: tuple[float, float, float],
    ) -> float:
        """A* 휴리스틱: 직선 에너지 비용 하한"""
        dist = math.sqrt(
            (pos[0] - goal[0]) ** 2
            + (pos[1] - goal[1]) ** 2
            + (pos[2] - goal[2]) ** 2
        )
        # 최소 전력으로 이동 시 에너지
        min_power = 50.0  # hover only
        travel_time = dist / max(self.cruise_speed, 1.0)
        return min_power * travel_time / 3600.0

    def _neighbors(self, pos: tuple[float, float, float]) -> list[tuple[float, float, float]]:
        """인접 그리드 셀 반환 (6방향 + 수직 2방향)"""
        r = self.grid_res
        candidates = []
        for dx, dy in [
            (r, 0), (-r, 0), (0, r), (0, -r),
            (r, r), (-r, -r), (r, -r), (-r, r),
        ]:
            candidates.append((pos[0] + dx, pos[1] + dy, pos[2]))

        # 수직 이동
        for dz in [self.alt_step, -self.alt_step]:
            nz = pos[2] + dz
            if self.alt_min <= nz <= self.alt_max:
                candidates.append((pos[0], pos[1], nz))

        # 범위 + NFZ 필터
        valid = []
        b = self.bounds
        for c in candidates:
            if -b <= c[0] <= b and -b <= c[1] <= b and not self._in_nfz(c):
                valid.append(c)

        return valid

    def plan(
        self,
        start: np.ndarray,
        goal: np.ndarray,
        max_iterations: int = 10000,
    ) -> tuple[list[np.ndarray], float]:
        """
        에너지 최적 A* 경로 탐색.

        Returns
        -------
        (path, total_energy_wh) : 경로 리스트 + 총 에너지 비용
        """
        s = self._snap(start)
        g = self._snap(goal)

        if s == g:
            return [start.copy()], 0.0

        open_set: list[_Node] = []
        start_node = _Node(
            f_cost=self._heuristic(s, g),
            g_cost=0.0,
            position=s,
        )
        heapq.heappush(open_set, start_node)

        visited: dict[tuple, float] = {}
        best_node: dict[tuple, _Node] = {s: start_node}

        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)

            if current.position == g:
                # 경로 역추적
                path = []
                node = current
                while node is not None:
                    path.append(np.array(node.position))
                    node = node.parent
                path.reverse()
                return path, current.g_cost

            if current.position in visited:
                continue
            visited[current.position] = current.g_cost

            for neighbor_pos in self._neighbors(current.position):
                if neighbor_pos in visited:
                    continue

                edge_cost = self._energy_cost(current.position, neighbor_pos)
                new_g = current.g_cost + edge_cost

                if neighbor_pos in best_node and new_g >= best_node[neighbor_pos].g_cost:
                    continue

                h = self._heuristic(neighbor_pos, g)
                new_node = _Node(
                    f_cost=new_g + h,
                    g_cost=new_g,
                    position=neighbor_pos,
                    parent=current,
                )
                best_node[neighbor_pos] = new_node
                heapq.heappush(open_set, new_node)

        # 경로 없음 → 직선 폴백
        return [start.copy(), goal.copy()], self._energy_cost(s, g)

    def plan_with_charging(
        self,
        start: np.ndarray,
        goal: np.ndarray,
        battery_wh: float = 80.0,
        charge_time_s: float = 60.0,
    ) -> tuple[list[np.ndarray], float, list[int]]:
        """
        배터리 부족 시 충전소 경유 경로 계획.

        Returns
        -------
        (path, total_energy, charge_stop_indices)
        """
        if not self.charging_stations:
            path, cost = self.plan(start, goal)
            return path, cost, []

        # 직접 경로 가능한지 확인
        path, cost = self.plan(start, goal)
        if cost <= battery_wh * 0.9:
            return path, cost, []

        # 충전소 경유 필요
        best_path = path
        best_cost = cost
        best_stops: list[int] = []

        for station in self.charging_stations:
            p1, c1 = self.plan(start, station)
            p2, c2 = self.plan(station, goal)

            if c1 <= battery_wh * 0.9 and c2 <= battery_wh * 0.9:
                total = c1 + c2
                if total < best_cost:
                    combined = p1 + p2[1:]
                    best_path = combined
                    best_cost = total
                    best_stops = [len(p1) - 1]

        return best_path, best_cost, best_stops

    def estimate_range_km(self, battery_wh: float, altitude: float = 60.0) -> float:
        """주어진 배터리로 비행 가능 거리 추정 (km)"""
        p_hover = 50.0
        p_drag = 0.5 * self.cruise_speed ** 2
        alt_factor = 1.0 + altitude * 0.00012
        total_power = (p_hover + p_drag) * alt_factor

        flight_time_h = battery_wh / total_power
        range_km = self.cruise_speed * flight_time_h * 3.6  # m/s → km/h → km
        return range_km
