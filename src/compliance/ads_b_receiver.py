"""
ADS-B Receiver Simulator (Phase 682)

이 모듈은 SDACS가 유인 항공기나 비협조적 드론의 신호를 수신하는
가상의 ADS-B(Automatic Dependent Surveillance-Broadcast) 수신기로 동작합니다.
1090MHz 또는 978MHz UAT 신호를 시뮬레이션 환경에 주입합니다.
"""

import numpy as np

class AdsbReceiver:
    def __init__(self, seed: int = 682):
        self.active_aircraft = {}
        self._rng = np.random.default_rng(seed)

    def fetch_surrounding_traffic(self, center_lat: float, center_lon: float, radius_km: float) -> list:
        """
        특정 반경 내의 ADS-B 트래픽을 가상으로 생성하거나 
        실제 RTL-SDR 하드웨어를 통해 수집된 외부 데이터를 주입받아 반환합니다.
        """
        # Phase 682: 가상 트래픽 발생기 (Mock)
        # 1% 확률로 유인 헬기나 경비행기 출현 시뮬레이션
        traffic = []
        if self._rng.random() < 0.01:
            intruder_lat = center_lat + (self._rng.uniform(-1, 1) * radius_km * 0.009)
            intruder_lon = center_lon + (self._rng.uniform(-1, 1) * radius_km * 0.009)

            traffic.append({
                "icao_address": f"A{self._rng.integers(100000, 999999)}",
                "callsign": "MEDIVAC1",
                "lat": intruder_lat,
                "lon": intruder_lon,
                "alt": self._rng.uniform(150, 300),  # 유인기 고도
                "velocity": self._rng.uniform(40, 60),  # m/s
                "heading": self._rng.uniform(0, 360)
            })
            
        return traffic
