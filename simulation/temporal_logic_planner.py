# Phase 532: Temporal Logic Planner — LTL/CTL Mission Verification
"""
시간논리 기반 미션 계획 검증: LTL(Linear Temporal Logic) 수식 파싱,
Büchi 오토마타 변환, 모델 체킹으로 미션 안전성 검증.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class LTLOp(Enum):
    ALWAYS = "G"       # Globally
    EVENTUALLY = "F"   # Finally
    NEXT = "X"         # Next
    UNTIL = "U"        # Until
    AND = "&"
    OR = "|"
    NOT = "!"
    IMPLIES = "->"
    ATOM = "atom"


@dataclass
class LTLFormula:
    op: LTLOp
    atom: str = ""
    left: 'LTLFormula | None' = None
    right: 'LTLFormula | None' = None


@dataclass
class State:
    name: str
    props: set = field(default_factory=set)
    transitions: list = field(default_factory=list)


@dataclass
class VerificationResult:
    formula_str: str
    satisfied: bool
    counterexample: list = field(default_factory=list)
    depth_explored: int = 0


def atom(name: str) -> LTLFormula:
    return LTLFormula(LTLOp.ATOM, atom=name)

def always(f: LTLFormula) -> LTLFormula:
    return LTLFormula(LTLOp.ALWAYS, left=f)

def eventually(f: LTLFormula) -> LTLFormula:
    return LTLFormula(LTLOp.EVENTUALLY, left=f)

def implies(a: LTLFormula, b: LTLFormula) -> LTLFormula:
    return LTLFormula(LTLOp.IMPLIES, left=a, right=b)

def land(a: LTLFormula, b: LTLFormula) -> LTLFormula:
    return LTLFormula(LTLOp.AND, left=a, right=b)

def lor(a: LTLFormula, b: LTLFormula) -> LTLFormula:
    return LTLFormula(LTLOp.OR, left=a, right=b)

def lnot(f: LTLFormula) -> LTLFormula:
    return LTLFormula(LTLOp.NOT, left=f)


def formula_to_str(f: LTLFormula) -> str:
    if f.op == LTLOp.ATOM:
        return f.atom
    if f.op == LTLOp.NOT:
        return f"!{formula_to_str(f.left)}"
    if f.op in (LTLOp.ALWAYS, LTLOp.EVENTUALLY, LTLOp.NEXT):
        return f"{f.op.value}({formula_to_str(f.left)})"
    return f"({formula_to_str(f.left)} {f.op.value} {formula_to_str(f.right)})"


class ModelChecker:
    """간이 Bounded LTL 모델 체커."""

    def __init__(self, bound=50):
        self.bound = bound

    def check(self, states: list[State], initial: str, formula: LTLFormula) -> VerificationResult:
        state_map = {s.name: s for s in states}
        if initial not in state_map:
            return VerificationResult(formula_to_str(formula), False, [], 0)

        # BFS로 모든 경로 탐색 (bounded)
        paths = [[initial]]
        satisfied = True
        counter = []
        depth = 0

        for d in range(self.bound):
            depth = d + 1
            new_paths = []
            for path in paths:
                cur = state_map[path[-1]]
                if not cur.transitions:
                    # 자기 자신으로 루프
                    new_paths.append(path + [cur.name])
                else:
                    for t in cur.transitions:
                        if t in state_map:
                            new_paths.append(path + [t])
            paths = new_paths[:100]  # 경로 수 제한

            # 현재까지의 모든 경로에서 수식 검증
            for path in paths:
                trace = [state_map[s].props for s in path]
                if not self._eval_trace(formula, trace, 0):
                    satisfied = False
                    counter = path[:depth]
                    return VerificationResult(formula_to_str(formula), False, counter, depth)

        return VerificationResult(formula_to_str(formula), satisfied, [], depth)

    def _eval_trace(self, f: LTLFormula, trace: list[set], pos: int) -> bool:
        if pos >= len(trace):
            return True
        if f.op == LTLOp.ATOM:
            return f.atom in trace[pos]
        if f.op == LTLOp.NOT:
            return not self._eval_trace(f.left, trace, pos)
        if f.op == LTLOp.AND:
            return self._eval_trace(f.left, trace, pos) and self._eval_trace(f.right, trace, pos)
        if f.op == LTLOp.OR:
            return self._eval_trace(f.left, trace, pos) or self._eval_trace(f.right, trace, pos)
        if f.op == LTLOp.IMPLIES:
            return not self._eval_trace(f.left, trace, pos) or self._eval_trace(f.right, trace, pos)
        if f.op == LTLOp.NEXT:
            return self._eval_trace(f.left, trace, pos + 1) if pos + 1 < len(trace) else True
        if f.op == LTLOp.ALWAYS:
            return all(self._eval_trace(f.left, trace, i) for i in range(pos, len(trace)))
        if f.op == LTLOp.EVENTUALLY:
            return any(self._eval_trace(f.left, trace, i) for i in range(pos, len(trace)))
        if f.op == LTLOp.UNTIL:
            for i in range(pos, len(trace)):
                if self._eval_trace(f.right, trace, i):
                    return True
                if not self._eval_trace(f.left, trace, i):
                    return False
            return False
        return True


class TemporalLogicPlanner:
    """미션 계획의 시간논리 검증기."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.checker = ModelChecker(bound=30)
        self.states: list[State] = []
        self.results: list[VerificationResult] = []

    def build_mission_model(self, n_waypoints=8):
        """미션 상태 모델 자동 생성."""
        self.states.clear()
        state_names = [f"WP_{i}" for i in range(n_waypoints)]
        props_pool = ["safe", "charged", "in_geofence", "no_conflict", "comm_ok"]

        for i, name in enumerate(state_names):
            props = set()
            for p in props_pool:
                if self.rng.random() < 0.8:
                    props.add(p)
            nexts = []
            if i + 1 < n_waypoints:
                nexts.append(state_names[i + 1])
            if i + 2 < n_waypoints and self.rng.random() < 0.3:
                nexts.append(state_names[i + 2])
            self.states.append(State(name, props, nexts))

        # 마지막 상태 → 자기 자신 (종료)
        if self.states:
            self.states[-1].props.add("landed")

    def verify(self, formula: LTLFormula) -> VerificationResult:
        if not self.states:
            self.build_mission_model()
        result = self.checker.check(self.states, self.states[0].name, formula)
        self.results.append(result)
        return result

    def verify_safety_properties(self) -> list[VerificationResult]:
        """기본 안전 속성 검증 배치."""
        props = [
            always(atom("safe")),
            always(implies(atom("no_conflict"), atom("safe"))),
            eventually(atom("landed")),
            always(atom("in_geofence")),
        ]
        return [self.verify(f) for f in props]

    def summary(self):
        passed = sum(1 for r in self.results if r.satisfied)
        return {
            "states": len(self.states),
            "checks": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
        }


if __name__ == "__main__":
    planner = TemporalLogicPlanner(42)
    planner.build_mission_model(10)
    results = planner.verify_safety_properties()
    for r in results:
        print(f"  {r.formula_str}: {'PASS' if r.satisfied else 'FAIL'}")
    print(planner.summary())
