# Phase 537: Multi-Objective Scheduler — NSGA-II Pareto Optimization
"""
다목적 스케줄링: NSGA-II 기반 Pareto 최적화.
에너지 소모, 비행 시간, 충돌 위험을 동시 최소화하는 임무 스케줄링.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Mission:
    mission_id: str
    priority: float
    duration_s: float
    energy_cost: float
    risk: float
    drone_id: str = ""


@dataclass
class Schedule:
    schedule_id: str
    assignments: list  # [(mission_id, drone_id, start_time)]
    objectives: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rank: int = 0
    crowding: float = 0.0


class NSGA2:
    """NSGA-II 다목적 최적화."""

    def __init__(self, pop_size=30, n_objectives=3, seed=42):
        self.pop_size = pop_size
        self.n_obj = n_objectives
        self.rng = np.random.default_rng(seed)

    def dominates(self, a: np.ndarray, b: np.ndarray) -> bool:
        return bool(np.all(a <= b) and np.any(a < b))

    def fast_nondominated_sort(self, pop: list[Schedule]) -> list[list[int]]:
        n = len(pop)
        domination_count = [0] * n
        dominated_set: list[list[int]] = [[] for _ in range(n)]
        fronts: list[list[int]] = [[]]

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if self.dominates(pop[i].objectives, pop[j].objectives):
                    dominated_set[i].append(j)
                elif self.dominates(pop[j].objectives, pop[i].objectives):
                    domination_count[i] += 1
            if domination_count[i] == 0:
                pop[i].rank = 0
                fronts[0].append(i)

        k = 0
        while fronts[k]:
            next_front = []
            for i in fronts[k]:
                for j in dominated_set[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        pop[j].rank = k + 1
                        next_front.append(j)
            k += 1
            fronts.append(next_front)

        return [f for f in fronts if f]

    def crowding_distance(self, pop: list[Schedule], front: list[int]):
        if len(front) <= 2:
            for idx in front:
                pop[idx].crowding = float('inf')
            return
        for idx in front:
            pop[idx].crowding = 0.0

        for m in range(self.n_obj):
            sorted_idx = sorted(front, key=lambda i: pop[i].objectives[m])
            pop[sorted_idx[0]].crowding = float('inf')
            pop[sorted_idx[-1]].crowding = float('inf')
            obj_range = pop[sorted_idx[-1]].objectives[m] - pop[sorted_idx[0]].objectives[m]
            if obj_range < 1e-10:
                continue
            for k in range(1, len(sorted_idx) - 1):
                pop[sorted_idx[k]].crowding += (
                    pop[sorted_idx[k + 1]].objectives[m] - pop[sorted_idx[k - 1]].objectives[m]
                ) / obj_range

    def tournament_select(self, pop: list[Schedule]) -> Schedule:
        i, j = int(self.rng.integers(0, len(pop))), int(self.rng.integers(0, len(pop)))
        if pop[i].rank < pop[j].rank:
            return pop[i]
        if pop[j].rank < pop[i].rank:
            return pop[j]
        return pop[i] if pop[i].crowding > pop[j].crowding else pop[j]


class MultiObjectiveScheduler:
    """다목적 임무 스케줄러."""

    def __init__(self, n_missions=20, n_drones=8, pop_size=30, generations=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_missions = n_missions
        self.n_drones = n_drones
        self.pop_size = pop_size
        self.generations = generations
        self.nsga = NSGA2(pop_size, 3, seed)
        self.missions: list[Mission] = []
        self.population: list[Schedule] = []
        self.pareto_front: list[Schedule] = []

        self._generate_missions()

    def _generate_missions(self):
        for i in range(self.n_missions):
            self.missions.append(Mission(
                f"M-{i:04d}",
                priority=self.rng.uniform(0.1, 1.0),
                duration_s=self.rng.uniform(60, 600),
                energy_cost=self.rng.uniform(5, 50),
                risk=self.rng.uniform(0, 0.5),
            ))

    def _random_schedule(self, sid: str) -> Schedule:
        assignments = []
        time_offset = {}
        for m in self.missions:
            did = f"drone_{int(self.rng.integers(0, self.n_drones))}"
            start = time_offset.get(did, 0.0)
            assignments.append((m.mission_id, did, start))
            time_offset[did] = start + m.duration_s
        return Schedule(sid, assignments)

    def _evaluate(self, sched: Schedule):
        total_energy = 0.0
        total_time = 0.0
        total_risk = 0.0
        mission_map = {m.mission_id: m for m in self.missions}
        drone_end = {}
        for mid, did, start in sched.assignments:
            m = mission_map[mid]
            total_energy += m.energy_cost
            end = start + m.duration_s
            drone_end[did] = max(drone_end.get(did, 0), end)
            total_risk += m.risk
        total_time = max(drone_end.values()) if drone_end else 0
        sched.objectives = np.array([total_energy, total_time, total_risk])

    def _mutate(self, sched: Schedule, sid: str) -> Schedule:
        new_assignments = list(sched.assignments)
        if new_assignments:
            idx = int(self.rng.integers(0, len(new_assignments)))
            mid, _, start = new_assignments[idx]
            new_drone = f"drone_{int(self.rng.integers(0, self.n_drones))}"
            new_assignments[idx] = (mid, new_drone, start + self.rng.normal(0, 30))
        return Schedule(sid, new_assignments)

    def run(self):
        # 초기 집단
        self.population = [self._random_schedule(f"S-{i}") for i in range(self.pop_size)]
        for s in self.population:
            self._evaluate(s)

        for gen in range(self.generations):
            # 자식 생성
            children = []
            for i in range(self.pop_size):
                parent = self.nsga.tournament_select(self.population)
                child = self._mutate(parent, f"S-g{gen}_{i}")
                self._evaluate(child)
                children.append(child)

            combined = self.population + children
            fronts = self.nsga.fast_nondominated_sort(combined)
            for front in fronts:
                self.nsga.crowding_distance(combined, front)

            # 상위 pop_size만 선택
            new_pop = []
            for front in fronts:
                if len(new_pop) + len(front) <= self.pop_size:
                    new_pop.extend(front)
                else:
                    remaining = self.pop_size - len(new_pop)
                    sorted_front = sorted(front, key=lambda i: combined[i].crowding, reverse=True)
                    new_pop.extend(sorted_front[:remaining])
                    break
            self.population = [combined[i] for i in new_pop]

        # Pareto front 추출
        fronts = self.nsga.fast_nondominated_sort(self.population)
        if fronts:
            self.pareto_front = [self.population[i] for i in fronts[0]]

    def summary(self):
        best = min(self.population, key=lambda s: s.objectives.sum()) if self.population else None
        return {
            "missions": self.n_missions,
            "drones": self.n_drones,
            "generations": self.generations,
            "pareto_size": len(self.pareto_front),
            "best_energy": float(best.objectives[0]) if best else 0,
            "best_time": float(best.objectives[1]) if best else 0,
            "best_risk": float(best.objectives[2]) if best else 0,
        }


if __name__ == "__main__":
    mos = MultiObjectiveScheduler(20, 8, 30, 15, 42)
    mos.run()
    s = mos.summary()
    for k, v in s.items():
        print(f"  {k}: {v}")
