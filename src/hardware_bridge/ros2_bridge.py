"""
ROS2 Interoperability Bridge (Phase 672)

이 모듈은 rclpy를 사용하여, SDACS의 1Hz 관제 루프와 
외부 ROS2 메타시스템(예: 로봇 관제 프레임워크) 간의 실시간 브릿지 역할을 합니다.
내부적으로는 MAVROS 토픽이나 사용자 정의 Swarm 토픽을 활용합니다.
"""
import sys
import threading
import json
import logging

logger = logging.getLogger(__name__)

# rclpy가 설치된 환경에서만 동작하도록 분기 처리
try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    RCLPY_AVAILABLE = True
except ImportError:
    RCLPY_AVAILABLE = False
    logger.warning("rclpy 패키지를 찾을 수 없습니다. ROS2 브릿지는 Mock 모드로 동작합니다.")

if RCLPY_AVAILABLE:
    class SDACSRos2Node(Node):
        def __init__(self):
            super().__init__('sdacs_bridge_node')
            
            # Pub: SDACS 관제 시스템에서 발행된 어드바이저리를 외부로 전송
            self.advisory_pub = self.create_publisher(String, '/sdacs/resolution_advisory', 10)
            
            # Sub: 외부 시스템이나 실제 드론에서 오는 텔레메트리 수신
            self.telemetry_sub = self.create_subscription(
                String,
                '/sdacs/drone_telemetry',
                self.telemetry_callback,
                10
            )
            
            # 수신 버퍼
            self.telemetry_queue = []
            
        def telemetry_callback(self, msg):
            """외부 ROS2 노드로부터 수신한 드론의 위치 및 상태 정보를 버퍼링"""
            try:
                data = json.loads(msg.data)
                self.telemetry_queue.append(data)
                logger.debug(f"[ROS2] Received telemetry for drone {data.get('drone_id')}")
            except Exception as e:
                logger.error(f"[ROS2] Failed to parse telemetry: {e}")
                
        def publish_advisory(self, advisory_dict: dict):
            """관제 명령을 JSON 페이로드로 직렬화하여 발행"""
            msg = String()
            msg.data = json.dumps(advisory_dict)
            self.advisory_pub.publish(msg)
            logger.debug(f"[ROS2] Published advisory for drone {advisory_dict.get('target')}")

class Ros2BridgeDaemon:
    def __init__(self):
        self.node = None
        self._thread = None
        
    def start(self):
        """ROS2 스핀 스레드 백그라운드 시작"""
        if not RCLPY_AVAILABLE:
            return
            
        rclpy.init()
        self.node = SDACSRos2Node()
        self._thread = threading.Thread(target=rclpy.spin, args=(self.node,), daemon=True)
        self._thread.start()
        logger.info("ROS2 브릿지 스레드가 시작되었습니다.")
        
    def stop(self):
        if self.node:
            self.node.destroy_node()
            rclpy.shutdown()
            
    def pop_telemetry(self):
        """관제 루프에서 호출 주기마다 수집된 텔레메트리 데이터를 반환"""
        if not self.node:
            return []
        data = self.node.telemetry_queue.copy()
        self.node.telemetry_queue.clear()
        return data
