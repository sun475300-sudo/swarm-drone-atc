# Phase 602: Drone Auction Market — Vickrey Auction
"""
드론 경매 시장: 비크리 경매(2차 가격),
자원 할당, 수익 분석.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Bid:
    bidder_id: str
    amount: float


@dataclass
class AuctionResult:
    winner: str
    price: float  # second-highest bid
    highest_bid: float


class VickreyAuction:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.history: list[AuctionResult] = []

    def run_auction(self, bids: list[tuple[str, float]]) -> AuctionResult | None:
        if len(bids) < 1:
            return None
        sorted_bids = sorted(bids, key=lambda b: b[1], reverse=True)
        winner = sorted_bids[0][0]
        price = sorted_bids[1][1] if len(sorted_bids) > 1 else sorted_bids[0][1]
        result = AuctionResult(winner, price, sorted_bids[0][1])
        self.history.append(result)
        return result


class DroneAuctionMarket:
    def __init__(self, n_drones=10, n_tasks=5, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.n_tasks = n_tasks
        self.auction = VickreyAuction(seed)
        self.rounds = 0
        self.total_revenue = 0.0
        self.allocations: list[dict] = []

    def run(self, rounds=20):
        for r in range(rounds):
            task_value = float(self.rng.uniform(10, 100))
            bids = []
            for d in range(self.n_drones):
                valuation = task_value * self.rng.uniform(0.5, 1.5)
                bids.append((f"drone_{d}", float(valuation)))
            result = self.auction.run_auction(bids)
            if result:
                self.total_revenue += result.price
                self.allocations.append({
                    "round": r,
                    "winner": result.winner,
                    "price": result.price,
                })
            self.rounds += 1

    def summary(self):
        return {
            "drones": self.n_drones,
            "tasks": self.n_tasks,
            "rounds": self.rounds,
            "total_revenue": round(self.total_revenue, 2),
            "avg_price": round(self.total_revenue / max(1, self.rounds), 2),
            "unique_winners": len(set(a["winner"] for a in self.allocations)),
        }


if __name__ == "__main__":
    dam = DroneAuctionMarket(10, 5, 42)
    dam.run(20)
    for k, v in dam.summary().items():
        print(f"  {k}: {v}")
