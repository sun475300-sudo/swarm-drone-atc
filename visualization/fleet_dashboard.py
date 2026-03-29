"""
Fleet Management Dashboard
Phase 260 P2 - Real-time fleet monitoring and management UI
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np


class DroneStatus:
    IDLE = "idle"
    CHARGING = "charging"
    IN_MISSION = "in_mission"
    RETURNING = "returning"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"


@dataclass
class FleetDrone:
    drone_id: str
    status: str = DroneStatus.IDLE
    battery_percent: float = 100.0
    position: tuple = (0.0, 0.0, 0.0)
    target: Optional[tuple] = None
    speed_mps: float = 0.0
    mission_progress: float = 0.0
    total_flights: int = 0
    flight_hours: float = 0.0
    last_maintenance: Optional[datetime] = None
    next_maintenance: Optional[datetime] = None


class FleetMetrics:
    def __init__(self):
        self.total_drones = 0
        self.active_drones = 0
        self.charging_drones = 0
        self.idle_drones = 0
        self.maintenance_drones = 0
        self.emergency_drones = 0
        self.avg_battery: float = 0.0
        self.total_flight_hours: float = 0.0
        self.missions_completed_today: int = 0
        self.utilization_rate: float = 0.0


class FleetManager:
    def __init__(self, fleet_size: int = 100):
        self.drones: Dict[str, FleetDrone] = {}
        self.mission_history: List[Dict] = []
        self.alerts: List[Dict] = []
        self._initialize_fleet(fleet_size)
        self.start_time = datetime.now()

    def _initialize_fleet(self, size: int):
        for i in range(size):
            drone_id = f"FLEET-{i + 1:04d}"
            drone = FleetDrone(
                drone_id=drone_id,
                status=np.random.choice(
                    [DroneStatus.IDLE, DroneStatus.IN_MISSION, DroneStatus.CHARGING],
                    p=[0.3, 0.5, 0.2],
                ),
                battery_percent=np.random.uniform(20, 100),
                position=(
                    np.random.uniform(0, 500),
                    np.random.uniform(0, 500),
                    np.random.uniform(20, 100),
                ),
                speed_mps=np.random.uniform(5, 20),
                total_flights=np.random.randint(0, 500),
                flight_hours=np.random.uniform(0, 1000),
                last_maintenance=datetime.now()
                - timedelta(days=np.random.randint(1, 30)),
                next_maintenance=datetime.now()
                + timedelta(days=np.random.randint(1, 30)),
            )
            self.drones[drone_id] = drone

    def get_metrics(self) -> FleetMetrics:
        metrics = FleetMetrics()
        metrics.total_drones = len(self.drones)

        status_counts = {}
        batteries = []

        for drone in self.drones.values():
            status_counts[drone.status] = status_counts.get(drone.status, 0) + 1
            batteries.append(drone.battery_percent)
            metrics.total_flight_hours += drone.flight_hours

        metrics.active_drones = status_counts.get(DroneStatus.IN_MISSION, 0)
        metrics.charging_drones = status_counts.get(DroneStatus.CHARGING, 0)
        metrics.idle_drones = status_counts.get(DroneStatus.IDLE, 0)
        metrics.maintenance_drones = status_counts.get(DroneStatus.MAINTENANCE, 0)
        metrics.emergency_drones = status_counts.get(DroneStatus.EMERGENCY, 0)
        metrics.avg_battery = np.mean(batteries) if batteries else 0
        metrics.utilization_rate = (
            (metrics.active_drones / metrics.total_drones * 100)
            if metrics.total_drones > 0
            else 0
        )

        return metrics

    def assign_mission(self, drone_id: str, target: tuple) -> bool:
        if drone_id not in self.drones:
            return False

        drone = self.drones[drone_id]
        if drone.status not in [DroneStatus.IDLE, DroneStatus.RETURNING]:
            return False

        drone.status = DroneStatus.IN_MISSION
        drone.target = target
        drone.mission_progress = 0.0

        self.mission_history.append(
            {
                "drone_id": drone_id,
                "target": target,
                "start_time": datetime.now().isoformat(),
                "status": "assigned",
            }
        )

        return True

    def update_drone(self, drone_id: str, delta_time: float = 1.0):
        if drone_id not in self.drones:
            return

        drone = self.drones[drone_id]

        if drone.status == DroneStatus.IN_MISSION:
            dx = drone.target[0] - drone.position[0]
            dy = drone.target[1] - drone.position[1]
            dz = drone.target[2] - drone.position[2]
            dist = np.sqrt(dx**2 + dy**2 + dz**2)

            if dist < 10:
                drone.status = DroneStatus.RETURNING
                drone.mission_progress = 100.0
                drone.total_flights += 1
            else:
                move = delta_time * drone.speed_mps
                drone.position = (
                    drone.position[0] + (dx / dist) * move,
                    drone.position[1] + (dy / dist) * move,
                    drone.position[2] + (dz / dist) * move,
                )
                drone.mission_progress = min(100, (1 - dist / 500) * 100)

            drone.battery_percent = max(0, drone.battery_percent - delta_time * 0.5)

        elif drone.status == DroneStatus.CHARGING:
            drone.battery_percent = min(100, drone.battery_percent + delta_time * 2)
            if drone.battery_percent >= 95:
                drone.status = DroneStatus.IDLE

        elif drone.status == DroneStatus.RETURNING:
            drone.status = DroneStatus.IDLE
            drone.target = None

    def check_alerts(self) -> List[Dict]:
        alerts = []
        for drone in self.drones.values():
            if drone.battery_percent < 20:
                alerts.append(
                    {
                        "type": "low_battery",
                        "severity": "critical",
                        "drone_id": drone.drone_id,
                        "message": f"Low battery: {drone.battery_percent:.1f}%",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            if drone.status == DroneStatus.EMERGENCY:
                alerts.append(
                    {
                        "type": "emergency",
                        "severity": "critical",
                        "drone_id": drone.drone_id,
                        "message": "Emergency status activated",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            if drone.next_maintenance and drone.next_maintenance < datetime.now():
                alerts.append(
                    {
                        "type": "maintenance_due",
                        "severity": "warning",
                        "drone_id": drone.drone_id,
                        "message": "Maintenance overdue",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return alerts

    def get_fleet_status_json(self) -> str:
        metrics = self.get_metrics()
        status = {
            "timestamp": datetime.now().isoformat(),
            "fleet_size": metrics.total_drones,
            "metrics": {
                "active": metrics.active_drones,
                "charging": metrics.charging_drones,
                "idle": metrics.idle_drones,
                "maintenance": metrics.maintenance_drones,
                "emergency": metrics.emergency_drones,
                "avg_battery": round(metrics.avg_battery, 2),
                "utilization_rate": round(metrics.utilization_rate, 2),
                "total_flight_hours": round(metrics.total_flight_hours, 2),
            },
            "drones": [
                {
                    "id": d.drone_id,
                    "status": d.status,
                    "battery": round(d.battery_percent, 1),
                    "position": [round(p, 1) for p in d.position],
                    "mission_progress": round(d.mission_progress, 1),
                }
                for d in list(self.drones.values())[:50]
            ],
            "alerts": self.check_alerts(),
        }
        return json.dumps(status, indent=2)

    def optimize_fleet_allocation(self) -> Dict:
        idle_drones = [d for d in self.drones.values() if d.status == DroneStatus.IDLE]
        low_battery = [d for d in self.drones.values() if d.battery_percent < 30]

        return {
            "idle_drones_available": len(idle_drones),
            "low_battery_drones": len(low_battery),
            "recommended_actions": [
                f"Charge {len(low_battery)} drones with low battery"
                if low_battery
                else "All drones have sufficient battery",
                f"Deploy {len(idle_drones)} idle drones for missions"
                if idle_drones
                else "All drones in use",
            ],
            "fleet_health_score": min(
                100,
                (len(idle_drones) / len(self.drones)) * 100 + (100 - len(low_battery)),
            ),
        }


class FleetDashboard:
    def __init__(self, fleet_manager: FleetManager):
        self.fleet = fleet_manager

    def render_dashboard(self) -> str:
        metrics = self.fleet.get_metrics()
        alerts = self.fleet.check_alerts()

        output = []
        output.append("╔════════════════════════════════════════════════════════════╗")
        output.append("║        🛩️  FLEET MANAGEMENT DASHBOARD  🛩️                    ║")
        output.append("╚════════════════════════════════════════════════════════════╝")
        output.append(f"  Fleet Size: {metrics.total_drones} drones")
        output.append(
            f"  Active: {metrics.active_drones} | Charging: {metrics.charging_drones} | Idle: {metrics.idle_drones}"
        )
        output.append(
            f"  Avg Battery: {metrics.avg_battery:.1f}% | Utilization: {metrics.utilization_rate:.1f}%"
        )
        output.append(f"  Total Flight Hours: {metrics.total_flight_hours:.1f}h")

        if alerts:
            output.append("\n  ⚠️  ALERTS:")
            for alert in alerts[:5]:
                output.append(f"    [{alert['severity'].upper()}] {alert['message']}")

        output.append("\n  Drone Status Distribution:")
        output.append(
            f"    IN_MISSION:    {'█' * (metrics.active_drones // 10)} {metrics.active_drones}"
        )
        output.append(
            f"    CHARGING:      {'█' * (metrics.charging_drones // 10)} {metrics.charging_drones}"
        )
        output.append(
            f"    IDLE:          {'█' * (metrics.idle_drones // 10)} {metrics.idle_drones}"
        )
        output.append(
            f"    MAINTENANCE:   {'█' * (metrics.maintenance_drones // 10)} {metrics.maintenance_drones}"
        )

        return "\n".join(output)


def create_fleet_dashboard(num_drones: int = 100) -> tuple:
    fleet = FleetManager(num_drones)
    dashboard = FleetDashboard(fleet)
    return fleet, dashboard


if __name__ == "__main__":
    fleet, dashboard = create_fleet_dashboard(50)
    print(dashboard.render_dashboard())

    print("\n--- Fleet Status JSON ---")
    print(fleet.get_fleet_status_json()[:500] + "...")

    print("\n--- Optimization ---")
    print(json.dumps(fleet.optimize_fleet_allocation(), indent=2))
