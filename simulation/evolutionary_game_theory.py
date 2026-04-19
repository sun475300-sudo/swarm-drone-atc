# Phase 549: Evolutionary Game Theory — Replicator Dynamics & ESS
"""
진화적 게임이론: 레플리케이터 다이내믹스, ESS(진화적 안정 전략),
Hawk-Dove/Prisoner's Dilemma로 군집 행동 전략 분석.
Phase 337 swarm_game_theory.py와 별도 — 진화적 다이내믹스 특화.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class EvoStrategy(Enum):
    COOPERATE = "cooperate"
    DEFECT = "defect"
    HAWK = "hawk"
    DOVE = "dove"
    TIT_FOR_TAT = "tit_for_tat"


@dataclass
class EvoPlayer:
    player_id: str
    strategy: EvoStrategy
    fitness: float = 0.0
    games_played: int = 0


@dataclass
class EvoGameResult:
    player_a: str
    player_b: str
    payoff_a: float
    payoff_b: float


class EvoPayoffMatrix:
    def __init__(self):
        self.hawk_dove = {
            (EvoStrategy.HAWK, EvoStrategy.HAWK): (-2, -2),
            (EvoStrategy.HAWK, EvoStrategy.DOVE): (3, 0),
            (EvoStrategy.DOVE, EvoStrategy.HAWK): (0, 3),
            (EvoStrategy.DOVE, EvoStrategy.DOVE): (1, 1),
        }
        self.pd = {
            (EvoStrategy.COOPERATE, EvoStrategy.COOPERATE): (3, 3),
            (EvoStrategy.COOPERATE, EvoStrategy.DEFECT): (0, 5),
            (EvoStrategy.DEFECT, EvoStrategy.COOPERATE): (5, 0),
            (EvoStrategy.DEFECT, EvoStrategy.DEFECT): (1, 1),
        }

    def get_payoff(self, s1: EvoStrategy, s2: EvoStrategy, game="pd") -> tuple[float, float]:
        matrix = self.pd if game == "pd" else self.hawk_dove
        s1m = EvoStrategy.COOPERATE if s1 == EvoStrategy.TIT_FOR_TAT else s1
        s2m = EvoStrategy.COOPERATE if s2 == EvoStrategy.TIT_FOR_TAT else s2
        return matrix.get((s1m, s2m), (0, 0))


class EvoReplicatorDynamics:
    def __init__(self, strategies: list[EvoStrategy], seed=42):
        self.strategies = strategies
        n = len(strategies)
        self.proportions = np.ones(n) / n
        self.rng = np.random.default_rng(seed)
        self.matrix = EvoPayoffMatrix()
        self.history: list[np.ndarray] = [self.proportions.copy()]

    def step(self, game="pd"):
        n = len(self.strategies)
        fitness = np.zeros(n)
        for i in range(n):
            for j in range(n):
                pa, _ = self.matrix.get_payoff(self.strategies[i], self.strategies[j], game)
                fitness[i] += self.proportions[j] * pa
        avg_fitness = np.dot(self.proportions, fitness)
        new_props = self.proportions * fitness / (avg_fitness + 1e-10)
        new_props = np.clip(new_props, 0, None)
        new_props /= new_props.sum() + 1e-10
        self.proportions = new_props
        self.history.append(self.proportions.copy())

    def is_ess(self) -> list[tuple[EvoStrategy, float]]:
        ess = []
        for i, s in enumerate(self.strategies):
            if self.proportions[i] > 0.5:
                ess.append((s, float(self.proportions[i])))
        return ess


class EvolutionaryGameTheory:
    def __init__(self, n_players=30, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_players = n_players
        self.matrix = EvoPayoffMatrix()
        strategies = [EvoStrategy.COOPERATE, EvoStrategy.DEFECT, EvoStrategy.HAWK, EvoStrategy.DOVE]
        self.players = [
            EvoPlayer(f"P_{i}", strategies[int(self.rng.integers(0, 4))])
            for i in range(n_players)
        ]
        self.replicator = EvoReplicatorDynamics(
            [EvoStrategy.COOPERATE, EvoStrategy.DEFECT], seed
        )
        self.game_results: list[EvoGameResult] = []

    def play_round(self, game="pd"):
        indices = self.rng.permutation(self.n_players)
        for k in range(0, self.n_players - 1, 2):
            i, j = indices[k], indices[k + 1]
            pa, pb = self.matrix.get_payoff(self.players[i].strategy, self.players[j].strategy, game)
            self.players[i].fitness += pa
            self.players[j].fitness += pb
            self.players[i].games_played += 1
            self.players[j].games_played += 1
            self.game_results.append(EvoGameResult(
                self.players[i].player_id, self.players[j].player_id, pa, pb
            ))

    def evolve(self, n_rounds=20, game="pd"):
        for _ in range(n_rounds):
            self.play_round(game)
            self.replicator.step(game)

    def summary(self):
        coop_count = sum(1 for p in self.players if p.strategy in (EvoStrategy.COOPERATE, EvoStrategy.DOVE))
        avg_fitness = float(np.mean([p.fitness for p in self.players]))
        ess = self.replicator.is_ess()
        return {
            "players": self.n_players,
            "cooperators": coop_count,
            "avg_fitness": round(avg_fitness, 2),
            "total_games": len(self.game_results),
            "ess": [(s.value, round(p, 3)) for s, p in ess],
            "rounds": len(self.replicator.history) - 1,
        }


if __name__ == "__main__":
    egt = EvolutionaryGameTheory(30, 42)
    egt.evolve(20)
    for k, v in egt.summary().items():
        print(f"  {k}: {v}")
