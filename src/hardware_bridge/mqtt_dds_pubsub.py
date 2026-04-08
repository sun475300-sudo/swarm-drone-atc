"""
MQTT / DDS Realtime Pub-Sub (Phase 673)

이 모듈은 무선 지연 및 패킷 손실이 발생하는 환경에서,
외부 엣지 디바이스(예: Jetson Nano가 탑재된 드론)와 SDACS 관제 서버 간에
MQTT 프로토콜을 사용한 저지연 제어 데이터를 교환합니다.
"""

import json
import logging
import threading

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("paho-mqtt 패키지가 없습니다. MQTT 모듈이 Mock 모드로 동작합니다.")

class MqttPubSubBridge:
    def __init__(self, broker_ip="127.0.0.1", port=1883, client_id="sdacs_controller"):
        self.broker_ip = broker_ip
        self.port = port
        self.client_id = client_id
        
        self.client = None
        self._connected = False
        self.incoming_messages = []
        
        if MQTT_AVAILABLE:
            self.client = mqtt.Client(self.client_id)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info(f"[MQTT] Connected to {self.broker_ip}:{self.port}")
            # SDACS 전용 토픽 구독
            self.client.subscribe("sdacs/telemetry/#")
        else:
            logger.error(f"[MQTT] Failed to connect, return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning("[MQTT] Disconnected from broker.")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            self.incoming_messages.append({"topic": msg.topic, "data": data})
        except Exception as e:
            pass

    def start(self):
        if not MQTT_AVAILABLE or self.client is None:
            return
            
        try:
            self.client.connect(self.broker_ip, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"[MQTT] Connection exception: {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def publish_advisory(self, drone_id: str, command: dict):
        """특정 드론에게 MQTT로 어드바이저리 액션 퍼블리시"""
        if self.client and self._connected:
            topic = f"sdacs/control/{drone_id}"
            payload = json.dumps(command)
            self.client.publish(topic, payload, qos=1)

    def fetch_incoming(self) -> list:
        msgs = self.incoming_messages.copy()
        self.incoming_messages.clear()
        return msgs
