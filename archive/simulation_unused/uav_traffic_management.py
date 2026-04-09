"""
UAV Traffic Management
Phase 396 - UTM Integration, Airspace Coordination
"""

from typing import Dict, List


class UTMClient:
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.flights: Dict[str, Dict] = {}

    def submit_flight_plan(self, plan_id: str, route: list, start: float, end: float):
        self.flights[plan_id] = {
            "route": route,
            "start": start,
            "end": end,
            "status": "pending",
        }

    def get_authorization(self, plan_id: str) -> str:
        if plan_id in self.flights:
            self.flights[plan_id]["status"] = "authorized"
            return "authorized"
        return "not_found"

    def report_position(self, flight_id: str, pos: tuple, alt: float):
        pass


class AirspaceManager:
    def __init__(self):
        self.restrictions: List[Dict] = []

    def add_restriction(self, zone: str, polygon: list, min_alt: float, max_alt: float):
        self.restrictions.append(
            {"zone": zone, "polygon": polygon, "min_alt": min_alt, "max_alt": max_alt}
        )

    def check_airspace(self, pos: tuple, alt: float) -> Dict:
        for r in self.restrictions:
            if r["min_alt"] <= alt <= r["max_alt"]:
                return {"restricted": True, "zone": r["zone"]}
        return {"restricted": False}


if __name__ == "__main__":
    print("=== UTM ===")
    utm = UTMClient("sdacs")
    utm.submit_flight_plan("plan_001", [(0, 0, 50), (100, 100, 50)], 0, 3600)
    print(utm.get_authorization("plan_001"))
