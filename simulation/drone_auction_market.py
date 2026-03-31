# Phase 602: Drone Auction Market — Vickrey Auction
"""
경매 기반 태스크 할당: Vickrey(2nd-price) 경매,
다중 태스크 할당, 사회적 후생 최적화.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Task:
    task_id: int
    value: float
    location: np.ndarray
    deadline: float


@dataclass
class Bid:
    bidder_id: int
    task_id: int
    amount: float
    capability: float


@dataclass
class AuctionResult:
    task_id: int
    winner_id: int
    payment: float  # 2nd price
    surplus: float


class VickreyAuction:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.results: list[AuctionResult] = []

    def run_auction(self, task: Task, bids: list[Bid]) -> AuctionResult:
        if not bids:
            return AuctionResult(task.task_id, -1, 0, 0)
        sorted_bids = sorted(bids, key=lambda b: b.amount, reverse=True)
        winner = sorted_bids[0]
        payment = sorted_bids[1].amount if len(sorted_bids) > 1 else 0
        result = AuctionResult(task.task_id, winner.bidder_id, payment, winner.amount - payment)
        self.results.append(result)
        return result


class DroneAuctionMarket:
    def __init__(self, n_drones=10, n_tasks=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.auction = VickreyAuction(seed)
        self.n_drones = n_drones
        self.n_tasks = n_tasks
        self.drone_capabilities = self.rng.uniform(0.5, 1.5, n_drones)
        self.tasks: list[Task] = []
        self.allocations: dict[int, int] = {}

    def generate_tasks(self):
        for i in range(self.n_tasks):
            self.tasks.append(Task(i, float(self.rng.uniform(10, 100)),
                                    self.rng.uniform(0, 100, 2), float(self.rng.uniform(60, 300))))

    def run(self):
        self.generate_tasks()
        for task in self.tasks:
            bids = []
            for d in range(self.n_drones):
                val = float(task.value * self.drone_capabilities[d] + self.rng.normal(0, 5))
                bids.append(Bid(d, task.task_id, max(0, val), float(self.drone_capabilities[d])))
            result = self.auction.run_auction(task, bids)
            if result.winner_id >= 0:
                self.allocations[task.task_id] = result.winner_id

    def summary(self):
        payments = [r.payment for r in self.auction.results]
        surpluses = [r.surplus for r in self.auction.results]
        return {
            "drones": self.n_drones,
            "tasks": self.n_tasks,
            "allocated": len(self.allocations),
            "avg_payment": round(float(np.mean(payments)), 2) if payments else 0,
            "total_surplus": round(float(np.sum(surpluses)), 2),
        }


if __name__ == "__main__":
    dam = DroneAuctionMarket(10, 15, 42)
    dam.run()
    for k, v in dam.summary().items():
        print(f"  {k}: {v}")
