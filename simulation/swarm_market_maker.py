# Phase 628: Swarm Market Maker — Order Book Model
"""
군집 자원 시장 조성자:
주문서 모델, 매수/매도 스프레드, 자원 가격 발견.
"""

import numpy as np
from dataclasses import dataclass, field
from collections import deque


@dataclass
class Order:
    order_id: int
    drone_id: int
    side: str  # "bid" or "ask"
    price: float
    quantity: float
    timestamp: int


class OrderBook:
    def __init__(self):
        self.bids: list[Order] = []
        self.asks: list[Order] = []
        self.trades: list[dict] = []
        self.next_id = 0

    def submit(self, drone_id: int, side: str, price: float, quantity: float, timestamp: int) -> Order:
        self.next_id += 1
        order = Order(self.next_id, drone_id, side, price, quantity, timestamp)
        if side == "bid":
            self.bids.append(order)
            self.bids.sort(key=lambda o: -o.price)
        else:
            self.asks.append(order)
            self.asks.sort(key=lambda o: o.price)
        self._match(timestamp)
        return order

    def _match(self, timestamp: int):
        while self.bids and self.asks and self.bids[0].price >= self.asks[0].price:
            bid, ask = self.bids[0], self.asks[0]
            trade_price = (bid.price + ask.price) / 2
            trade_qty = min(bid.quantity, ask.quantity)
            self.trades.append({
                "price": trade_price,
                "quantity": trade_qty,
                "buyer": bid.drone_id,
                "seller": ask.drone_id,
                "timestamp": timestamp,
            })
            bid.quantity -= trade_qty
            ask.quantity -= trade_qty
            if bid.quantity <= 0:
                self.bids.pop(0)
            if ask.quantity <= 0:
                self.asks.pop(0)

    def spread(self) -> float:
        if not self.bids or not self.asks:
            return float('inf')
        return self.asks[0].price - self.bids[0].price

    def mid_price(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0].price + self.asks[0].price) / 2


class SwarmMarketMaker:
    def __init__(self, n_drones=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.book = OrderBook()
        self.n_drones = n_drones
        self.steps = 0
        self.price_history: list[float] = []

    def run(self, steps=200):
        for t in range(steps):
            for d in range(self.n_drones):
                side = "bid" if self.rng.random() < 0.5 else "ask"
                base_price = 50.0
                price = base_price + float(self.rng.normal(0, 5))
                qty = float(self.rng.uniform(1, 10))
                self.book.submit(d, side, price, qty, t)
            mid = self.book.mid_price()
            if mid > 0:
                self.price_history.append(mid)
            self.steps += 1

    def summary(self):
        return {
            "drones": self.n_drones,
            "steps": self.steps,
            "total_trades": len(self.book.trades),
            "current_spread": round(self.book.spread(), 4) if self.book.spread() < 1e6 else "N/A",
            "avg_price": round(float(np.mean(self.price_history)), 2) if self.price_history else 0,
            "price_volatility": round(float(np.std(self.price_history)), 4) if self.price_history else 0,
        }


if __name__ == "__main__":
    mm = SwarmMarketMaker(20, 42)
    mm.run(200)
    for k, v in mm.summary().items():
        print(f"  {k}: {v}")
