"""
Mission Auction System
Phase 360 - Vickrey Auction, Combinatorial Auction for Drone Swarm Task Allocation
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
from collections import defaultdict
import heapq


class AuctionState(Enum):
    OPEN = "open"
    BIDDING = "bidding"
    CLOSED = "closed"
    ALLOCATED = "allocated"


class MissionType(Enum):
    DELIVERY = "delivery"
    SURVEILLANCE = "surveillance"
    SEARCH_RESCUE = "search_rescue"
    MONITORING = "monitoring"
    TRANSPORT = "transport"


@dataclass
class Mission:
    mission_id: str
    mission_type: MissionType
    start_position: Tuple[float, float, float]
    end_position: Tuple[float, float, float]
    deadline: float
    priority: int
    required_capabilities: Set[str]
    estimated_duration: float
    payload_kg: float = 0.0
    reward: float = 0.0


@dataclass
class Drone:
    drone_id: str
    position: Tuple[float, float, float]
    battery_percent: float
    capabilities: Set[str]
    max_payload_kg: float
    cost_per_km: float
    available_from: float = 0.0


@dataclass
class Bid:
    bidder_id: str
    mission_id: str
    bid_amount: float
    cost_estimate: float
    start_time: float
    completion_time: float
    confidence: float


@dataclass
class AuctionResult:
    mission_id: str
    winning_drone_id: str
    winning_bid_amount: float
    second_highest_bid: float
    payment: float
    allocation_time: float


class VickreyAuction:
    def __init__(self, mission: Mission):
        self.mission = mission
        self.bids: List[Bid] = []
        self.state = AuctionState.OPEN

    def submit_bid(self, bid: Bid):
        if self.state == AuctionState.OPEN:
            self.state = AuctionState.BIDDING
        self.bids.append(bid)

    def close_auction(self) -> Optional[AuctionResult]:
        if not self.bids:
            return None

        self.state = AuctionState.CLOSED

        sorted_bids = sorted(self.bids, key=lambda b: b.bid_amount, reverse=True)

        winner = sorted_bids[0]

        if len(sorted_bids) > 1:
            second_price = sorted_bids[1].bid_amount
        else:
            second_price = 0.0

        payment = second_price

        return AuctionResult(
            mission_id=self.mission.mission_id,
            winning_drone_id=winner.bidder_id,
            winning_bid_amount=winner.bid_amount,
            second_highest_bid=second_price,
            payment=payment,
            allocation_time=bid.completion_time,
        )


class CombinatorialAuction:
    def __init__(self, missions: List[Mission], drones: List[Drone]):
        self.missions = missions
        self.drones = drones
        self.bids: Dict[str, List[Bid]] = {m.mission_id: [] for m in missions}
        self.state = AuctionState.OPEN

        self.allocation: Dict[str, str] = {}

    def submit_bundle_bid(
        self,
        drone_id: str,
        mission_bundle: List[str],
        bundle_price: float,
        start_time: float,
    ):
        if self.state != AuctionState.OPEN:
            return

        bundle_cost = sum(self._estimate_cost(drone_id, m) for m in mission_bundle)

        for mission_id in mission_bundle:
            bid = Bid(
                bidder_id=drone_id,
                mission_id=mission_id,
                bid_amount=bundle_price / len(mission_bundle),
                cost_estimate=bundle_cost / len(mission_bundle),
                start_time=start_time,
                completion_time=start_time
                + sum(self._get_mission_duration(m) for m in mission_bundle),
                confidence=0.9,
            )
            self.bids[mission_id].append(bid)

    def _estimate_cost(self, drone_id: str, mission_id: str) -> float:
        drone = next((d for d in self.drones if d.drone_id == drone_id), None)
        mission = next((m for m in self.missions if m.mission_id == mission_id), None)

        if not drone or not mission:
            return float("inf")

        distance = self._calculate_distance(drone.position, mission.start_position)
        distance += self._calculate_distance(
            mission.start_position, mission.end_position
        )

        return distance * drone.cost_per_km

    def _calculate_distance(self, pos1: Tuple, pos2: Tuple) -> float:
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

    def _get_mission_duration(self, mission_id: str) -> float:
        mission = next((m for m in self.missions if m.mission_id == mission_id), None)
        return mission.estimated_duration if mission else 0.0

    def allocate(self) -> Dict[str, AuctionResult]:
        self.state = AuctionState.ALLOCATED
        results = {}

        for mission_id, bids in self.bids.items():
            if not bids:
                continue

            sorted_bids = sorted(bids, key=lambda b: b.bid_amount, reverse=True)

            if sorted_bids:
                winner = sorted_bids[0]
                second_price = (
                    sorted_bids[1].bid_amount if len(sorted_bids) > 1 else 0.0
                )

                results[mission_id] = AuctionResult(
                    mission_id=mission_id,
                    winning_drone_id=winner.bidder_id,
                    winning_bid_amount=winner.bid_amount,
                    second_highest_bid=second_price,
                    payment=second_price,
                    allocation_time=winner.completion_time,
                )

                self.allocation[mission_id] = winner.bidder_id

        return results


class EnglishAuction:
    def __init__(self, mission: Mission):
        self.mission = mission
        self.current_price = 0.0
        self.highest_bidder: Optional[str] = None
        self.bids: List[Tuple[str, float]] = []
        self.round = 0
        self.min_increment = mission.reward * 0.05
        self.state = AuctionState.OPEN

    def submit_bid(self, bidder_id: str, bid_amount: float) -> bool:
        if self.state != AuctionState.OPEN:
            return False

        if bid_amount > self.current_price + self.min_increment:
            self.current_price = bid_amount
            self.highest_bidder = bidder_id
            self.bids.append((bidder_id, bid_amount))
            self.round += 1
            return True

        return False

    def close(self) -> Optional[AuctionResult]:
        if not self.highest_bidder:
            return None

        self.state = AuctionState.CLOSED

        return AuctionResult(
            mission_id=self.mission.mission_id,
            winning_drone_id=self.highest_bidder,
            winning_bid_amount=self.current_price,
            second_highest_bid=self.current_price,
            payment=self.current_price,
            allocation_time=0.0,
        )


class DutchAuction:
    def __init__(self, mission: Mission):
        self.mission = mission
        self.current_price = mission.reward * 1.5
        self.min_price = mission.reward * 0.5
        self.decrement = mission.reward * 0.1
        self.state = AuctionState.OPEN
        self.accepted_bidder: Optional[str] = None

    def submit_acceptance(self, bidder_id: str) -> Optional[AuctionResult]:
        if self.state != AuctionState.OPEN:
            return None

        self.accepted_bidder = bidder_id
        self.state = AuctionState.CLOSED

        return AuctionResult(
            mission_id=self.mission.mission_id,
            winning_drone_id=bidder_id,
            winning_bid_amount=self.current_price,
            second_highest_bid=self.current_price,
            payment=self.current_price,
            allocation_time=0.0,
        )

    def next_price(self) -> float:
        self.current_price = max(self.min_price, self.current_price - self.decrement)
        return self.current_price


class MissionAuctionManager:
    def __init__(self):
        self.missions: Dict[str, Mission] = {}
        self.drones: Dict[str, Drone] = {}
        self.auctions: Dict[str, VickreyAuction] = {}
        self.combinatorial_auction: Optional[CombinatorialAuction] = None
        self.auction_results: List[AuctionResult] = []

    def register_mission(self, mission: Mission):
        self.missions[mission.mission_id] = mission
        self.auctions[mission.mission_id] = VickreyAuction(mission)

    def register_drone(self, drone: Drone):
        self.drones[drone.drone_id] = drone

    def create_missions(self, num_missions: int = 10):
        mission_types = list(MissionType)

        for i in range(num_missions):
            mission = Mission(
                mission_id=f"MISSION-{i + 1:03d}",
                mission_type=np.random.choice(mission_types),
                start_position=(
                    np.random.uniform(0, 500),
                    np.random.uniform(0, 500),
                    50,
                ),
                end_position=(np.random.uniform(0, 500), np.random.uniform(0, 500), 50),
                deadline=np.random.uniform(10, 60),
                priority=np.random.randint(1, 10),
                required_capabilities={"flight", "navigation"},
                estimated_duration=np.random.uniform(5, 30),
                payload_kg=np.random.uniform(0, 10),
                reward=np.random.uniform(100, 1000),
            )
            self.register_mission(mission)

    def create_drones(self, num_drones: int = 10):
        for i in range(num_drones):
            drone = Drone(
                drone_id=f"DRONE-{i + 1:03d}",
                position=(np.random.uniform(0, 500), np.random.uniform(0, 500), 50),
                battery_percent=np.random.uniform(50, 100),
                capabilities={"flight", "navigation", "delivery"},
                max_payload_kg=np.random.uniform(5, 20),
                cost_per_km=np.random.uniform(0.5, 2.0),
            )
            self.register_drone(drone)

    def submit_bids(self):
        for mission_id, auction in self.auctions.items():
            mission = self.missions[mission_id]

            available_drones = [
                d for d in self.drones.values() if d.battery_percent > 30
            ]

            for drone in available_drones:
                distance = np.sqrt(
                    (drone.position[0] - mission.start_position[0]) ** 2
                    + (drone.position[1] - mission.start_position[1]) ** 2
                    + (drone.position[2] - mission.start_position[2]) ** 2
                )

                cost = distance * drone.cost_per_km
                bid_amount = cost * np.random.uniform(1.2, 1.5)

                bid = Bid(
                    bidder_id=drone.drone_id,
                    mission_id=mission_id,
                    bid_amount=bid_amount,
                    cost_estimate=cost,
                    start_time=0.0,
                    completion_time=mission.estimated_duration,
                    confidence=np.random.uniform(0.7, 1.0),
                )

                auction.submit_bid(bid)

    def run_auction(self) -> List[AuctionResult]:
        results = []

        for mission_id, auction in self.auctions.items():
            result = auction.close_auction()
            if result:
                results.append(result)
                self.auction_results.append(result)

        return results

    def run_combinatorial_auction(self) -> Dict[str, AuctionResult]:
        mission_list = list(self.missions.values())
        drone_list = list(self.drones.values())

        self.combinatorial_auction = CombinatorialAuction(mission_list, drone_list)

        for drone in drone_list:
            mission_bundle = np.random.choice(
                [m.mission_id for m in mission_list],
                size=np.random.randint(1, min(3, len(mission_list))),
                replace=False,
            ).tolist()

            bundle_price = sum(
                self.missions[m].reward * np.random.uniform(0.8, 1.2)
                for m in mission_bundle
            )

            self.combinatorial_auction.submit_bundle_bid(
                drone.drone_id, mission_bundle, bundle_price, 0.0
            )

        results = self.combinatorial_auction.allocate()

        for result in results.values():
            self.auction_results.append(result)

        return results

    def get_auction_summary(self) -> Dict:
        total_revenue = sum(r.winning_bid_amount for r in self.auction_results)
        total_payment = sum(r.payment for r in self.auction_results)

        return {
            "total_missions": len(self.missions),
            "total_drones": len(self.drones),
            "allocated_missions": len(self.auction_results),
            "total_revenue": total_revenue,
            "total_payment": total_payment,
            "efficiency": len(self.auction_results) / max(1, len(self.missions)) * 100,
        }


def simulate_mission_auction():
    manager = MissionAuctionManager()

    print("=== Mission Auction System Simulation ===")

    manager.create_missions(10)
    manager.create_drones(5)

    print(f"\n--- Vickrey Auctions ---")
    manager.submit_bids()
    vickrey_results = manager.run_auction()

    for result in vickrey_results[:5]:
        print(f"{result.mission_id}: {result.winning_drone_id} - ${result.payment:.2f}")

    print(f"\n--- Combinatorial Auction ---")
    combo_results = manager.run_combinatorial_auction()

    for mission_id, result in list(combo_results.items())[:3]:
        print(f"{mission_id}: {result.winning_drone_id} - ${result.payment:.2f}")

    summary = manager.get_auction_summary()
    print(f"\n=== Summary ===")
    print(f"Missions: {summary['total_missions']}")
    print(f"Allocated: {summary['allocated_missions']}")
    print(f"Revenue: ${summary['total_revenue']:.2f}")
    print(f"Efficiency: {summary['efficiency']:.1f}%")

    return summary


if __name__ == "__main__":
    simulate_mission_auction()
