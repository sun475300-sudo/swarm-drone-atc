"""
Phase 337: Swarm Game Theory
군집 게임이론 의사결정 엔진.
Nash 균형 탐색, 반복 죄수 딜레마, Pareto 최적.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class Strategy(Enum):
    COOPERATE = "cooperate"
    DEFECT = "defect"
    TIT_FOR_TAT = "tit_for_tat"
    RANDOM = "random"
    ALWAYS_COOPERATE = "always_cooperate"
    ALWAYS_DEFECT = "always_defect"
    PAVLOV = "pavlov"


class GameType(Enum):
    PRISONERS_DILEMMA = "prisoners_dilemma"
    STAG_HUNT = "stag_hunt"
    CHICKEN = "chicken"
    COORDINATION = "coordination"
    CUSTOM = "custom"


@dataclass
class Player:
    player_id: str
    strategy: Strategy
    total_payoff: float = 0.0
    games_played: int = 0
    cooperation_rate: float = 0.0
    _coop_count: int = 0
    history: List[str] = field(default_factory=list)


@dataclass
class GameResult:
    player_a: str
    player_b: str
    action_a: str
    action_b: str
    payoff_a: float
    payoff_b: float
    round_num: int


@dataclass
class NashEquilibrium:
    strategies: Dict[str, str]
    payoffs: Dict[str, float]
    is_pure: bool
    is_pareto_optimal: bool


class PayoffMatrix:
    """2-player payoff matrix."""

    PRISONERS_DILEMMA = {
        ("cooperate", "cooperate"): (3, 3),
        ("cooperate", "defect"): (0, 5),
        ("defect", "cooperate"): (5, 0),
        ("defect", "defect"): (1, 1),
    }

    STAG_HUNT = {
        ("cooperate", "cooperate"): (4, 4),
        ("cooperate", "defect"): (0, 3),
        ("defect", "cooperate"): (3, 0),
        ("defect", "defect"): (2, 2),
    }

    CHICKEN = {
        ("cooperate", "cooperate"): (3, 3),
        ("cooperate", "defect"): (1, 5),
        ("defect", "cooperate"): (5, 1),
        ("defect", "defect"): (0, 0),
    }

    @classmethod
    def get_matrix(cls, game_type: GameType) -> Dict[Tuple[str, str], Tuple[float, float]]:
        return {
            GameType.PRISONERS_DILEMMA: cls.PRISONERS_DILEMMA,
            GameType.STAG_HUNT: cls.STAG_HUNT,
            GameType.CHICKEN: cls.CHICKEN,
            GameType.COORDINATION: cls.PRISONERS_DILEMMA,
        }.get(game_type, cls.PRISONERS_DILEMMA)


class SwarmGameTheory:
    """Game-theoretic decision engine for drone swarms."""

    def __init__(self, game_type: GameType = GameType.PRISONERS_DILEMMA,
                 seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.game_type = game_type
        self.payoff_matrix = PayoffMatrix.get_matrix(game_type)
        self.players: Dict[str, Player] = {}
        self.results: List[GameResult] = []
        self.round_num = 0

    def add_player(self, player_id: str, strategy: Strategy) -> Player:
        player = Player(player_id, strategy)
        self.players[player_id] = player
        return player

    def _choose_action(self, player: Player, opponent_history: List[str]) -> str:
        if player.strategy == Strategy.ALWAYS_COOPERATE:
            return "cooperate"
        elif player.strategy == Strategy.ALWAYS_DEFECT:
            return "defect"
        elif player.strategy == Strategy.COOPERATE:
            return "cooperate"
        elif player.strategy == Strategy.DEFECT:
            return "defect"
        elif player.strategy == Strategy.RANDOM:
            return "cooperate" if self.rng.random() < 0.5 else "defect"
        elif player.strategy == Strategy.TIT_FOR_TAT:
            if not opponent_history:
                return "cooperate"
            return opponent_history[-1]
        elif player.strategy == Strategy.PAVLOV:
            if not player.history:
                return "cooperate"
            if player.history[-1] == "cooperate" and opponent_history and opponent_history[-1] == "cooperate":
                return "cooperate"
            elif player.history[-1] == "defect" and opponent_history and opponent_history[-1] == "defect":
                return "cooperate"
            else:
                return "defect"
        return "cooperate"

    def play_round(self, player_a_id: str, player_b_id: str) -> GameResult:
        a = self.players[player_a_id]
        b = self.players[player_b_id]
        self.round_num += 1

        action_a = self._choose_action(a, b.history)
        action_b = self._choose_action(b, a.history)

        payoff_a, payoff_b = self.payoff_matrix.get(
            (action_a, action_b), (0, 0))

        a.total_payoff += payoff_a
        b.total_payoff += payoff_b
        a.games_played += 1
        b.games_played += 1
        a.history.append(action_a)
        b.history.append(action_b)

        if action_a == "cooperate":
            a._coop_count += 1
        if action_b == "cooperate":
            b._coop_count += 1
        a.cooperation_rate = a._coop_count / a.games_played
        b.cooperation_rate = b._coop_count / b.games_played

        result = GameResult(player_a_id, player_b_id, action_a, action_b,
                            payoff_a, payoff_b, self.round_num)
        self.results.append(result)
        return result

    def play_tournament(self, n_rounds: int = 50) -> Dict[str, float]:
        ids = list(self.players.keys())
        for _ in range(n_rounds):
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    self.play_round(ids[i], ids[j])

        return {pid: p.total_payoff for pid, p in self.players.items()}

    def find_nash_equilibria(self) -> List[NashEquilibrium]:
        equilibria = []
        actions = ["cooperate", "defect"]

        for a1 in actions:
            for a2 in actions:
                pa, pb = self.payoff_matrix.get((a1, a2), (0, 0))
                is_nash = True

                for alt in actions:
                    alt_pa, _ = self.payoff_matrix.get((alt, a2), (0, 0))
                    if alt_pa > pa:
                        is_nash = False
                        break

                if is_nash:
                    for alt in actions:
                        _, alt_pb = self.payoff_matrix.get((a1, alt), (0, 0))
                        if alt_pb > pb:
                            is_nash = False
                            break

                if is_nash:
                    is_pareto = self._is_pareto_optimal(pa, pb)
                    equilibria.append(NashEquilibrium(
                        strategies={"A": a1, "B": a2},
                        payoffs={"A": pa, "B": pb},
                        is_pure=True,
                        is_pareto_optimal=is_pareto
                    ))
        return equilibria

    def _is_pareto_optimal(self, pa: float, pb: float) -> bool:
        for (a1, a2), (qa, qb) in self.payoff_matrix.items():
            if qa >= pa and qb >= pb and (qa > pa or qb > pb):
                return False
        return True

    def find_pareto_frontier(self) -> List[Tuple[str, str, float, float]]:
        outcomes = []
        for (a1, a2), (pa, pb) in self.payoff_matrix.items():
            if self._is_pareto_optimal(pa, pb):
                outcomes.append((a1, a2, pa, pb))
        return outcomes

    def get_social_welfare(self) -> float:
        return sum(p.total_payoff for p in self.players.values())

    def get_cooperation_stats(self) -> Dict[str, float]:
        return {pid: p.cooperation_rate for pid, p in self.players.items()}

    def summary(self) -> Dict:
        scores = {pid: p.total_payoff for pid, p in self.players.items()}
        best = max(scores, key=scores.get) if scores else ""
        return {
            "game_type": self.game_type.value,
            "players": len(self.players),
            "rounds": self.round_num,
            "total_games": len(self.results),
            "social_welfare": self.get_social_welfare(),
            "best_player": best,
            "best_score": scores.get(best, 0),
            "nash_equilibria": len(self.find_nash_equilibria()),
            "cooperation_rates": self.get_cooperation_stats(),
        }


if __name__ == "__main__":
    game = SwarmGameTheory(GameType.PRISONERS_DILEMMA)
    game.add_player("drone_tft", Strategy.TIT_FOR_TAT)
    game.add_player("drone_coop", Strategy.ALWAYS_COOPERATE)
    game.add_player("drone_defect", Strategy.ALWAYS_DEFECT)
    game.add_player("drone_pavlov", Strategy.PAVLOV)
    game.add_player("drone_random", Strategy.RANDOM)

    scores = game.play_tournament(20)
    for pid, score in sorted(scores.items(), key=lambda x: -x[1]):
        print(f"  {pid}: {score:.0f}")

    nash = game.find_nash_equilibria()
    print(f"\nNash equilibria: {len(nash)}")
    for eq in nash:
        print(f"  {eq.strategies} → {eq.payoffs} (Pareto: {eq.is_pareto_optimal})")

    print(f"\nSummary: {game.summary()}")
