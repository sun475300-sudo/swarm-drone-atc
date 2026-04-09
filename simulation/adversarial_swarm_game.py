# Phase 587: Adversarial Swarm Game — Minimax Strategy
"""
적대적 군집 게임: Minimax 트리 탐색,
알파-베타 가지치기, 군집 전술 최적화.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class GameState:
    blue_positions: np.ndarray   # (N, 2) 아군
    red_positions: np.ndarray    # (M, 2) 적군
    blue_health: np.ndarray
    red_health: np.ndarray
    turn: str = "blue"           # blue or red

    def is_terminal(self) -> bool:
        return np.all(self.blue_health <= 0) or np.all(self.red_health <= 0)

    def score(self) -> float:
        return float(np.sum(self.blue_health) - np.sum(self.red_health))


@dataclass
class Move:
    unit_idx: int
    dx: float
    dy: float
    action: str = "move"  # move, attack


class MinimaxEngine:
    """Minimax + Alpha-Beta 엔진."""

    def __init__(self, max_depth=3, seed=42):
        self.rng = np.random.default_rng(seed)
        self.max_depth = max_depth
        self.nodes_evaluated = 0

    def generate_moves(self, state: GameState) -> list[Move]:
        moves = []
        positions = state.blue_positions if state.turn == "blue" else state.red_positions
        for i in range(len(positions)):
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]:
                moves.append(Move(i, dx * 5, dy * 5, "move"))
            moves.append(Move(i, 0, 0, "attack"))
        return moves[:10]  # 제한

    def apply_move(self, state: GameState, move: Move) -> GameState:
        bp = state.blue_positions.copy()
        rp = state.red_positions.copy()
        bh = state.blue_health.copy()
        rh = state.red_health.copy()

        if state.turn == "blue":
            if move.action == "move":
                bp[move.unit_idx] += [move.dx, move.dy]
            else:
                # 가장 가까운 적 공격
                dists = np.linalg.norm(rp - bp[move.unit_idx], axis=1)
                target = int(np.argmin(dists))
                if dists[target] < 30:
                    rh[target] -= 10
            next_turn = "red"
        else:
            if move.action == "move":
                rp[move.unit_idx] += [move.dx, move.dy]
            else:
                dists = np.linalg.norm(bp - rp[move.unit_idx], axis=1)
                target = int(np.argmin(dists))
                if dists[target] < 30:
                    bh[target] -= 10
            next_turn = "blue"

        return GameState(bp, rp, bh, rh, next_turn)

    def minimax(self, state: GameState, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
        self.nodes_evaluated += 1
        if depth == 0 or state.is_terminal():
            return state.score()

        moves = self.generate_moves(state)
        if maximizing:
            value = -np.inf
            for m in moves:
                child = self.apply_move(state, m)
                value = max(value, self.minimax(child, depth - 1, alpha, beta, False))
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return value
        else:
            value = np.inf
            for m in moves:
                child = self.apply_move(state, m)
                value = min(value, self.minimax(child, depth - 1, alpha, beta, True))
                beta = min(beta, value)
                if beta <= alpha:
                    break
            return value

    def best_move(self, state: GameState) -> Move:
        moves = self.generate_moves(state)
        best = moves[0]
        best_val = -np.inf
        for m in moves:
            child = self.apply_move(state, m)
            val = self.minimax(child, self.max_depth - 1, -np.inf, np.inf, state.turn != "blue")
            if state.turn == "blue" and val > best_val:
                best_val = val
                best = m
            elif state.turn == "red" and val < best_val:
                best_val = val
                best = m
        return best


class AdversarialSwarmGame:
    """적대적 군집 게임 시뮬레이션."""

    def __init__(self, n_blue=3, n_red=3, seed=42):
        self.rng = np.random.default_rng(seed)
        self.engine = MinimaxEngine(2, seed)
        self.state = GameState(
            blue_positions=self.rng.uniform(0, 50, (n_blue, 2)),
            red_positions=self.rng.uniform(50, 100, (n_red, 2)),
            blue_health=np.full(n_blue, 100.0),
            red_health=np.full(n_red, 100.0),
        )
        self.turns_played = 0

    def play_turn(self):
        if self.state.is_terminal():
            return
        move = self.engine.best_move(self.state)
        self.state = self.engine.apply_move(self.state, move)
        self.turns_played += 1

    def run(self, max_turns=20):
        for _ in range(max_turns):
            if self.state.is_terminal():
                break
            self.play_turn()

    def summary(self):
        return {
            "turns": self.turns_played,
            "blue_alive": int(np.sum(self.state.blue_health > 0)),
            "red_alive": int(np.sum(self.state.red_health > 0)),
            "blue_total_hp": round(float(np.sum(np.maximum(self.state.blue_health, 0))), 1),
            "red_total_hp": round(float(np.sum(np.maximum(self.state.red_health, 0))), 1),
            "nodes_evaluated": self.engine.nodes_evaluated,
        }


if __name__ == "__main__":
    game = AdversarialSwarmGame(3, 3, 42)
    game.run(20)
    for k, v in game.summary().items():
        print(f"  {k}: {v}")
