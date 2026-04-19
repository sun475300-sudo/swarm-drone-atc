"""
Phase 413: Risk Hedge Calculator for Mission Portfolio Optimization
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class RiskCategory(Enum):
    COLLISION = "collision"
    WEATHER = "weather"
    BATTERY = "battery"
    COMMUNICATION = "communication"
    REGULATORY = "regulatory"
    SECURITY = "security"


class HedgeStrategy(Enum):
    DIVERSIFICATION = "diversification"
    INSURANCE = "insurance"
    REDUNDANCY = "redundancy"
    AVOIDANCE = "avoidance"


@dataclass
class RiskFactor:
    category: RiskCategory
    probability: float
    impact: float
    timestamp: float


@dataclass
class HedgeAction:
    action_id: str
    strategy: HedgeStrategy
    cost: float
    risk_reduction: float
    drones_affected: List[str]


@dataclass
class PortfolioMetrics:
    total_risk: float
    expected_value: float
    variance: float
    sharpe_ratio: float
    max_drawdown: float


class RiskHedgeCalculator:
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        target_return: float = 0.15,
        max_risk_tolerance: float = 0.3,
    ):
        self.risk_free_rate = risk_free_rate
        self.target_return = target_return
        self.max_risk_tolerance = max_risk_tolerance

        self.risk_factors: Dict[RiskCategory, List[RiskFactor]] = {
            rc: [] for rc in RiskCategory
        }

        self.hedge_actions: List[HedgeAction] = []

        self.mission_returns: List[float] = []
        self.mission_variance = 0.0

    def add_risk_factor(
        self, category: RiskCategory, probability: float, impact: float
    ):
        factor = RiskFactor(
            category=category,
            probability=probability,
            impact=impact,
            timestamp=time.time(),
        )
        self.risk_factors[category].append(factor)

    def calculate_portfolio_risk(self, mission_weights: np.ndarray) -> PortfolioMetrics:
        if len(mission_weights) == 0:
            return PortfolioMetrics(0, 0, 0, 0, 0)

        expected_return = (
            np.sum(mission_weights * np.array(self.mission_returns))
            if self.mission_returns
            else 0.1
        )

        risk_contributions = []
        for category, factors in self.risk_factors.items():
            if not factors:
                continue
            for factor in factors:
                risk = factor.probability * factor.impact
                risk_contributions.append(risk)

        total_risk = sum(risk_contributions) if risk_contributions else 0.1

        variance = self.mission_variance * np.sum(mission_weights**2)

        sharpe_ratio = (
            (expected_return - self.risk_free_rate) / np.sqrt(variance)
            if variance > 0
            else 0
        )

        max_drawdown = total_risk * 0.5

        return PortfolioMetrics(
            total_risk=total_risk,
            expected_value=expected_return,
            variance=variance,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
        )

    def optimize_hedge(self, available_budget: float) -> List[HedgeAction]:
        optimal_actions = []

        redundancy_action = HedgeAction(
            action_id=f"hedge_{int(time.time())}_redundancy",
            strategy=HedgeStrategy.REDUNDANCY,
            cost=available_budget * 0.4,
            risk_reduction=0.3,
            drones_affected=[],
        )

        diversification_action = HedgeAction(
            action_id=f"hedge_{int(time.time())}_diversification",
            strategy=HedgeStrategy.DIVERSIFICATION,
            cost=available_budget * 0.3,
            risk_reduction=0.2,
            drones_affected=[],
        )

        insurance_action = HedgeAction(
            action_id=f"hedge_{int(time.time())}_insurance",
            strategy=HedgeStrategy.INSURANCE,
            cost=available_budget * 0.2,
            risk_reduction=0.15,
            drones_affected=[],
        )

        avoidance_action = HedgeAction(
            action_id=f"hedge_{int(time.time())}_avoidance",
            strategy=HedgeStrategy.AVOIDANCE,
            cost=available_budget * 0.1,
            risk_reduction=0.1,
            drones_affected=[],
        )

        optimal_actions.extend(
            [
                redundancy_action,
                diversification_action,
                insurance_action,
                avoidance_action,
            ]
        )

        total_cost = sum(a.cost for a in optimal_actions)

        if total_cost > available_budget:
            scale = available_budget / total_cost
            for action in optimal_actions:
                action.cost *= scale

        self.hedge_actions.extend(optimal_actions)

        return optimal_actions

    def calculate_var(self, confidence_level: float = 0.95) -> float:
        if not self.mission_returns:
            return 0.0

        returns_array = np.array(self.mission_returns)

        sorted_returns = np.sort(returns_array)

        index = int((1 - confidence_level) * len(sorted_returns))

        var = abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0

        return var

    def calculate_cvar(self, confidence_level: float = 0.95) -> float:
        var = self.calculate_var(confidence_level)

        if not self.mission_returns:
            return var

        returns_array = np.array(self.mission_returns)

        tail_losses = returns_array[returns_array <= -var]

        if len(tail_losses) == 0:
            return var

        cvar = abs(np.mean(tail_losses))

        return cvar

    def simulate_monte_carlo(self, num_simulations: int = 10000) -> Dict[str, Any]:
        results = []

        base_return = 0.1
        base_volatility = 0.2

        for _ in range(num_simulations):
            shock = np.random.normal(0, 1)

            risk_shock = sum(
                np.mean([f.probability * f.impact for f in factors])
                for factors in self.risk_factors.values()
                if factors
            )

            simulated_return = base_return + shock * base_volatility - risk_shock

            results.append(simulated_return)

        results = np.array(results)

        return {
            "mean_return": np.mean(results),
            "std_return": np.std(results),
            "min_return": np.min(results),
            "max_return": np.max(results),
            "percentile_5": np.percentile(results, 5),
            "percentile_95": np.percentile(results, 95),
            "probability_loss": np.sum(results < 0) / len(results),
        }

    def get_risk_report(self) -> Dict[str, Any]:
        category_risks = {}

        for category, factors in self.risk_factors.items():
            if factors:
                avg_probability = np.mean([f.probability for f in factors])
                avg_impact = np.mean([f.impact for f in factors])
                category_risks[category.value] = {
                    "average_probability": avg_probability,
                    "average_impact": avg_impact,
                    "risk_score": avg_probability * avg_impact,
                }

        return {
            "total_risk_factors": sum(len(f) for f in self.risk_factors.values()),
            "category_risks": category_risks,
            "var_95": self.calculate_var(0.95),
            "cvar_95": self.calculate_cvar(0.95),
            "hedge_actions_count": len(self.hedge_actions),
            "total_hedge_cost": sum(a.cost for a in self.hedge_actions),
        }
