"""
Phase 479: Payload Delivery System
"""


import numpy as np


class PayloadDeliverySystem:
    """``PayloadDeliverySystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.payloads: dict[str, dict] = {}

    def load_payload(self, drone_id: str, weight_kg: float, target: np.ndarray):
        """`payload` 정보를 조회한다."""
        self.payloads[drone_id] = {
            "weight": weight_kg,
            "target": target,
            "delivered": False,
        }

    def release_payload(self, drone_id: str):
        """``release_payload`` 동작을 수행한다."""
        if drone_id in self.payloads:
            self.payloads[drone_id]["delivered"] = True

    def is_delivered(self, drone_id: str) -> bool:
        """`delivered` 여부를 반환한다."""
        return self.payloads.get(drone_id, {}).get("delivered", False)
