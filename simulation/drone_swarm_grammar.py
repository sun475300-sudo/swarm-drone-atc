# Phase 542: Drone Swarm Grammar — L-System Formation Generation
"""
L-시스템 기반 대형 생성: 문법 규칙으로 군집 대형 정의,
프랙탈/재귀 패턴 대형 생성 및 진화.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class GrammarRule:
    """``GrammarRule`` 관련 기능을 제공한다."""
    symbol: str
    replacement: str
    probability: float = 1.0


@dataclass
class Formation:
    """``Formation`` 관련 기능을 제공한다."""
    formation_id: str
    positions: np.ndarray
    pattern_str: str
    fitness: float = 0.0


class LSystem:
    """L-시스템 문법 엔진."""

    def __init__(self, axiom="F", seed=42):
        """인스턴스를 초기화한다."""
        self.axiom = axiom
        self.rules: list[GrammarRule] = []
        self.rng = np.random.default_rng(seed)

    def add_rule(self, symbol: str, replacement: str, prob=1.0):
        """`rule` 항목을 추가한다."""
        self.rules.append(GrammarRule(symbol, replacement, prob))

    def generate(self, iterations=3) -> str:
        """`대상` 결과를 생성한다."""
        current = self.axiom
        for _ in range(iterations):
            new = []
            for ch in current:
                applied = False
                for rule in self.rules:
                    if rule.symbol == ch and self.rng.random() < rule.probability:
                        new.append(rule.replacement)
                        applied = True
                        break
                if not applied:
                    new.append(ch)
            current = "".join(new)
        return current

    def interpret(self, pattern: str, step=10.0, angle_deg=60.0) -> np.ndarray:
        """터틀 그래픽스 방식으로 패턴 → 좌표 변환."""
        positions = []
        x, y, z = 0.0, 0.0, 50.0
        heading = 0.0
        angle_rad = np.radians(angle_deg)
        stack = []

        for ch in pattern[:200]:  # 길이 제한
            if ch == 'F':
                x += step * np.cos(heading)
                y += step * np.sin(heading)
                positions.append([x, y, z])
            elif ch == '+':
                heading += angle_rad
            elif ch == '-':
                heading -= angle_rad
            elif ch == 'U':
                z += step * 0.3
            elif ch == 'D':
                z -= step * 0.3
            elif ch == '[':
                stack.append((x, y, z, heading))
            elif ch == ']' and stack:
                x, y, z, heading = stack.pop()

        return np.array(positions) if positions else np.array([[0, 0, 50]])


class FormationEvolver:
    """문법 진화: 대형 패턴 유전 알고리즘."""

    def __init__(self, seed=42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)

    def evaluate_fitness(self, positions: np.ndarray, target_count=10) -> float:
        """`fitness` 결과를 계산하거나 판정한다."""
        n = len(positions)
        count_score = 1.0 - abs(n - target_count) / max(target_count, 1)
        if n < 2:
            return max(0, count_score)
        dists = []
        for i in range(min(n, 20)):
            for j in range(i + 1, min(n, 20)):
                dists.append(np.linalg.norm(positions[i] - positions[j]))
        uniformity = 1.0 / (1.0 + np.std(dists)) if dists else 0
        spread = min(1.0, np.mean(dists) / 50.0) if dists else 0
        return float(np.clip(0.3 * count_score + 0.4 * uniformity + 0.3 * spread, 0, 1))

    def mutate_rules(self, rules: list[GrammarRule]) -> list[GrammarRule]:
        """``mutate_rules`` 동작을 수행한다."""
        new_rules = []
        symbols = "F+-UD[]"
        for rule in rules:
            rep = list(rule.replacement)
            if self.rng.random() < 0.3 and len(rep) > 0:
                idx = int(self.rng.integers(0, len(rep)))
                rep[idx] = symbols[int(self.rng.integers(0, len(symbols)))]
            if self.rng.random() < 0.2:
                rep.append(symbols[int(self.rng.integers(0, len(symbols)))])
            new_rules.append(GrammarRule(rule.symbol, "".join(rep), rule.probability))
        return new_rules


class DroneSwarmGrammar:
    """L-시스템 기반 군집 대형 시뮬레이션."""

    def __init__(self, n_target=15, seed=42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.n_target = n_target
        self.evolver = FormationEvolver(seed)
        self.formations: list[Formation] = []
        self.best: Formation | None = None

        # 기본 L-시스템 초기화
        self.lsys = LSystem("F", seed)
        self.lsys.add_rule("F", "F+F-F-F+F")

    def generate_formation(self, fid: str, iterations=3) -> Formation:
        """`formation` 결과를 생성한다."""
        pattern = self.lsys.generate(iterations)
        positions = self.lsys.interpret(pattern)
        fitness = self.evolver.evaluate_fitness(positions, self.n_target)
        f = Formation(fid, positions, pattern[:50], fitness)
        self.formations.append(f)
        if not self.best or f.fitness > self.best.fitness:
            self.best = f
        return f

    def evolve(self, generations=10, pop_size=8):
        """``evolve`` 동작을 수행한다."""
        for gen in range(generations):
            pop = []
            for i in range(pop_size):
                lsys = LSystem("F", int(self.rng.integers(0, 10000)))
                rules = self.evolver.mutate_rules(self.lsys.rules) if gen > 0 else self.lsys.rules
                for r in rules:
                    lsys.add_rule(r.symbol, r.replacement, r.probability)
                pattern = lsys.generate(3)
                positions = lsys.interpret(pattern)
                fitness = self.evolver.evaluate_fitness(positions, self.n_target)
                pop.append(Formation(f"gen{gen}_{i}", positions, pattern[:50], fitness))
            pop.sort(key=lambda f: f.fitness, reverse=True)
            self.formations.extend(pop)
            if not self.best or pop[0].fitness >= self.best.fitness:
                self.best = pop[0]

    def summary(self):
        """현재 상태 요약을 반환한다."""
        return {
            "target_drones": self.n_target,
            "formations_generated": len(self.formations),
            "best_fitness": round(self.best.fitness, 4) if self.best else 0,
            "best_drone_count": len(self.best.positions) if self.best else 0,
        }


if __name__ == "__main__":
    dsg = DroneSwarmGrammar(15, 42)
    dsg.evolve(10, 8)
    for k, v in dsg.summary().items():
        print(f"  {k}: {v}")
