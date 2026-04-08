"""
PX4 SITL MAVLink Connector (Phase 671)

이 모듈은 pymavlink를 활용하여, SDACS 시뮬레이션 환경 내의 관제 로직이
오픈소스 비행 제어기(PX4/ArduPilot)의 SITL 환경과 MAVLink로 데이터를 주고받도록 합니다.
"""

import logging
import math
import time

logger = logging.getLogger(__name__)

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    logger.warning("pymavlink 패키지가 없습니다. PX4 커넥터는 비활성화됩니다.")

class Px4SitlConnector:
    def __init__(self, connection_string="udp:127.0.0.1:14550"):
        """
        SITL 데몬과 연결 설정.
        QGroundControl과 같은 포트를 공유하지 않으려면 14550 배정 혹은 다른 라우팅 사용.
        """
        self.connection_string = connection_string
        self.master = None
        self.target_system = 1
        self.target_component = 1

    def connect(self):
        if not MAVLINK_AVAILABLE:
            return False
        
        try:
            self.master = mavutil.mavlink_connection(self.connection_string)
            self.master.wait_heartbeat(timeout=5.0)
            self.target_system = self.master.target_system
            self.target_component = self.master.target_component
            logger.info(f"[MAVLink] Heartbeat received from system {self.target_system} component {self.target_component}")
            return True
        except Exception as e:
            logger.error(f"[MAVLink] Failed to connect to SITL: {e}")
            return False

    def request_data_stream(self, rate=10):
        """MAVLink에게 텔레메트리 전송 빈도를 요청"""
        if not self.master:
            return
            
        self.master.mav.request_data_stream_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            rate,
            1  # Start sending
        )

    def read_telemetry(self):
        """가장 최신의 GLOBAL_POSITION_INT 구조 읽어와 SDACS 포맷으로 변환"""
        if not self.master:
            return None
            
        msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=False)
        if msg:
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt_m = msg.relative_alt / 1000.0  # mm to meters
            vx = msg.vx / 100.0                # cm/s to m/s
            vy = msg.vy / 100.0
            vz = msg.vz / 100.0
            
            return {
                "latitude": lat,
                "longitude": lon,
                "altitude_m": alt_m,
                "velocity": [vx, vy, vz]
            }
        return None

    def send_velocity_command(self, vx: float, vy: float, vz: float):
        """관제 명령(회피, 편대)을 속도 벡터로 변환하여 SITL에 강제 주입"""
        if not self.master:
            return
            
        # SET_POSITION_TARGET_LOCAL_NED 커맨드 사용 (type_mask로 속도만 제어함)
        type_mask = int(0b0000011111000111)  # Enable velocity, disable pos & accel
        
        self.master.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            type_mask,
            0, 0, 0, # Position
            vx, vy, vz, # Velocity
            0, 0, 0, # Accel
            0, 0     # Yaw, Yaw rate
        )

if __name__ == "__main__":
    connector = Px4SitlConnector()
    if connector.connect():
        connector.request_data_stream(rate=5)
        print("Listening for 5 seconds...")
        for _ in range(25):
            t = connector.read_telemetry()
            if t:
                print(t)
            time.sleep(0.2)
