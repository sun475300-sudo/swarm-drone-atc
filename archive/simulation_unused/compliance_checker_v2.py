"""
Compliance Checker
Phase 397 - FAA, EASA, ICAO Regulation Validation
"""

from typing import Dict, List


class Regulation:
    FAA = "faa"
    EASA = "easa"
    ICAO = "icao"


class ComplianceChecker:
    def __init__(self, region: str = Regulation.FAA):
        self.region = region
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        return {
            Regulation.FAA: {
                "max_altitude_ft": 400,
                "visual_line_of_sight": True,
                "max_speed_mph": 100,
                "min_distance_from_airport_nm": 5,
            },
            Regulation.EASA: {
                "max_altitude_m": 120,
                "min_distance_from_airport_km": 8,
                "remote_id_required": True,
            },
        }

    def validate_flight(
        self, altitude: float, speed: float, near_airport: bool, airport_dist: float
    ) -> Dict:
        rules = self.rules.get(self.region, {})
        violations = []

        if self.region == Regulation.FAA:
            if altitude > rules["max_altitude_ft"]:
                violations.append(
                    f"Altitude {altitude}ft exceeds {rules['max_altitude_ft']}ft limit"
                )
            if speed > rules["max_speed_mph"]:
                violations.append(f"Speed {speed}mph exceeds limit")
            if near_airport and airport_dist < rules["min_distance_from_airport_nm"]:
                violations.append(
                    f"Near airport: {airport_dist}nm < {rules['min_distance_from_airport_nm']}nm"
                )

        return {"compliant": len(violations) == 0, "violations": violations}


if __name__ == "__main__":
    print("=== Compliance ===")
    checker = ComplianceChecker(Regulation.FAA)
    result = checker.validate_flight(500, 80, True, 3)
    print(result)
