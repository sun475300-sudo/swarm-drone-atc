# Phase 610: Constraint Satisfaction Problem Solver — Backtracking + AC-3
"""
CSP 솔버: 백트래킹 탐색, AC-3 아크 일관성,
드론 스케줄링/할당 제약 만족.
"""

import numpy as np
from dataclasses import dataclass, field
from collections import deque


@dataclass
class Variable:
    name: str
    domain: list


@dataclass
class Constraint:
    var1: str
    var2: str
    relation: str  # "neq", "lt", "gt", "diff_ge"
    param: float = 0.0


class CSPSolver:
    def __init__(self):
        self.variables: dict[str, Variable] = {}
        self.constraints: list[Constraint] = []
        self.solution: dict[str, any] = {}
        self.backtracks = 0

    def add_variable(self, name: str, domain: list):
        self.variables[name] = Variable(name, list(domain))

    def add_constraint(self, var1: str, var2: str, relation: str, param=0.0):
        self.constraints.append(Constraint(var1, var2, relation, param))

    def _satisfies(self, c: Constraint, val1, val2) -> bool:
        if c.relation == "neq":
            return val1 != val2
        elif c.relation == "lt":
            return val1 < val2
        elif c.relation == "gt":
            return val1 > val2
        elif c.relation == "diff_ge":
            return abs(val1 - val2) >= c.param
        return True

    def ac3(self) -> bool:
        queue = deque()
        for c in self.constraints:
            queue.append((c.var1, c.var2, c))
            queue.append((c.var2, c.var1, Constraint(c.var2, c.var1, c.relation, c.param)))
        while queue:
            xi, xj, constraint = queue.popleft()
            if self._revise(xi, xj, constraint):
                if len(self.variables[xi].domain) == 0:
                    return False
                for c in self.constraints:
                    if c.var2 == xi and c.var1 != xj:
                        queue.append((c.var1, xi, c))
        return True

    def _revise(self, xi: str, xj: str, constraint: Constraint) -> bool:
        revised = False
        to_remove = []
        for val_i in self.variables[xi].domain:
            if not any(self._satisfies(constraint, val_i, val_j) for val_j in self.variables[xj].domain):
                to_remove.append(val_i)
                revised = True
        for v in to_remove:
            self.variables[xi].domain.remove(v)
        return revised

    def backtrack(self, assignment: dict) -> dict | None:
        if len(assignment) == len(self.variables):
            return dict(assignment)
        unassigned = [v for v in self.variables if v not in assignment]
        var = min(unassigned, key=lambda v: len(self.variables[v].domain))
        for value in self.variables[var].domain:
            if self._consistent(var, value, assignment):
                assignment[var] = value
                result = self.backtrack(assignment)
                if result is not None:
                    return result
                del assignment[var]
                self.backtracks += 1
        return None

    def _consistent(self, var: str, value, assignment: dict) -> bool:
        for c in self.constraints:
            if c.var1 == var and c.var2 in assignment:
                if not self._satisfies(c, value, assignment[c.var2]):
                    return False
            if c.var2 == var and c.var1 in assignment:
                if not self._satisfies(c, assignment[c.var1], value):
                    return False
        return True

    def solve(self) -> dict | None:
        self.ac3()
        self.solution = self.backtrack({})
        return self.solution


class ConstraintSatisfaction:
    def __init__(self, n_drones=8, n_timeslots=4, seed=42):
        self.rng = np.random.default_rng(seed)
        self.solver = CSPSolver()
        self.n_drones = n_drones
        self.n_timeslots = n_timeslots
        self._build_problem()

    def _build_problem(self):
        slots = list(range(self.n_timeslots))
        for i in range(self.n_drones):
            self.solver.add_variable(f"drone_{i}", list(slots))
        # 인접 드론은 다른 타임슬롯
        for i in range(self.n_drones):
            for j in range(i + 1, min(i + 3, self.n_drones)):
                self.solver.add_constraint(f"drone_{i}", f"drone_{j}", "neq")

    def run(self):
        self.solver.solve()

    def summary(self):
        return {
            "drones": self.n_drones,
            "timeslots": self.n_timeslots,
            "solved": self.solver.solution is not None,
            "backtracks": self.solver.backtracks,
            "assignments": len(self.solver.solution) if self.solver.solution else 0,
        }


if __name__ == "__main__":
    cs = ConstraintSatisfaction(8, 4, 42)
    cs.run()
    for k, v in cs.summary().items():
        print(f"  {k}: {v}")
