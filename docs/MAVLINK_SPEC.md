# SDACS MAVLink 메시지 흐름 명세 (MAVLINK_SPEC)

> **문서 번호**: SDACS-HW-001  
> **버전**: 0.9 (초안)  
> **작성일**: 2026-05-18  
> **대상**: HITL/실기 통합 개발자, onboard_bridge.py 구현 참조  

---

## 1. 시스템 구성도

```
[Pixhawk FC]
    │  MAVLink v2 (UART / UDP 14550)
    ▼
[Jetson Nano — onboard_bridge.py]  ←→  [SDACS Ground Controller]
    │  TCP/UDP (ground-uri)               │
    │  텔레메트리 JSON push                │  어드바이저리 명령 수신
    │                                      │
    └──────────────────────────────────────┘
                 양방향 링크
```

구현 파일: [src/hardware/onboard_bridge.py](../src/hardware/onboard_bridge.py)

---

## 2. 수신 메시지 (Pixhawk → onboard_bridge)

### 2.1 HEARTBEAT (#0)

| 필드 | 타입 | 설명 |
|------|------|------|
| type | uint8 | MAV_TYPE (쿼드콥터: 2) |
| autopilot | uint8 | MAV_AUTOPILOT_ARDUPILOTMEGA = 3 |
| base_mode | uint8 | 비행 모드 비트마스크 |
| system_status | uint8 | MAV_STATE |

**처리**: 수신 주기 > 3s 이면 링크 두절로 판정 → Lost-Link 프로토콜 시작

---

### 2.2 GLOBAL_POSITION_INT (#33)

| 필드 | 타입 | 단위 | 설명 |
|------|------|------|------|
| lat | int32 | 1E-7 deg | WGS84 위도 |
| lon | int32 | 1E-7 deg | WGS84 경도 |
| alt | int32 | mm | MSL 고도 |
| relative_alt | int32 | mm | AGL 고도 |
| vx | int16 | cm/s | X 속도 (북) |
| vy | int16 | cm/s | Y 속도 (동) |
| vz | int16 | cm/s | Z 속도 (하강 양수) |
| hdg | uint16 | cdeg | 기수 방위 |

**처리**: 10 Hz 폴링 → `TelemetrySnapshot` 생성 → Ground Controller로 전송

```python
# TelemetrySnapshot (onboard_bridge.py:60)
@dataclass(frozen=True)
class TelemetrySnapshot:
    drone_id: int
    lat_deg: float
    lon_deg: float
    alt_m: float
    vx_ms: float
    vy_ms: float
    vz_ms: float
    heading_deg: float
    battery_pct: float
    timestamp_s: float
```

---

### 2.3 BATTERY_STATUS (#147)

| 필드 | 타입 | 단위 | 설명 |
|------|------|------|------|
| battery_remaining | int8 | % | 잔량 (0~100, -1=unknown) |
| current_battery | int16 | cA | 전류 |
| voltages | uint16[10] | mV | 셀 전압 |

**처리**: `battery_pct` 필드로 매핑. 5% 미만 → `BATTERY_CRITICAL` 어드바이저리 발령

---

### 2.4 ATTITUDE (#30)

| 필드 | 타입 | 단위 | 설명 |
|------|------|------|------|
| roll | float | rad | 롤 |
| pitch | float | rad | 피치 |
| yaw | float | rad | 요(기수방위) |
| rollspeed | float | rad/s | 롤 각속도 |
| pitchspeed | float | rad/s | 피치 각속도 |
| yawspeed | float | rad/s | 요 각속도 |

**처리**: `heading_deg = math.degrees(yaw)` 변환

---

### 2.5 SYS_STATUS (#1)

| 필드 | 타입 | 설명 |
|------|------|------|
| onboard_control_sensors_health | uint32 | 센서 정상 비트마스크 |
| errors_count1 | uint16 | IMU 오류 카운터 |

**처리**: GPS 비트 (`MAV_SYS_STATUS_SENSOR_GPS`) 이상 → `GPS_LOSS` 장애 타입 설정

---

## 3. 송신 메시지 (onboard_bridge → Pixhawk)

### 3.1 SET_POSITION_TARGET_LOCAL_NED (#84)

SDACS 어드바이저리를 속도 명령으로 변환하여 전송.

| 필드 | 타입 | 설명 |
|------|------|------|
| coordinate_frame | uint8 | MAV_FRAME_LOCAL_NED = 1 |
| type_mask | uint16 | 0b0000_1111_1000_0111 (속도만 활성) |
| vx | float | 목표 X 속도 (m/s, 북) |
| vy | float | 목표 Y 속도 (m/s, 동) |
| vz | float | 목표 Z 속도 (m/s, 하강 양수) |

**어드바이저리 변환 규칙**:

| 어드바이저리 타입 | MAVLink 명령 |
|-----------------|-------------|
| `EVADE_APF` | APF force 벡터 → `SET_POSITION_TARGET_LOCAL_NED` |
| `TURN_RIGHT` | 현재 속도 벡터를 우측 90도 회전 |
| `HOLD` | vx=vy=vz=0 (정지 호버) |
| `RTL` | ArduCopter RTL 모드로 전환 (`SET_MODE`) |
| `LAND` | ArduCopter LAND 모드로 전환 (`SET_MODE`) |

---

### 3.2 SET_MODE (#11)

| 필드 | 타입 | 설명 |
|------|------|------|
| base_mode | uint8 | MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 128 |
| custom_mode | uint32 | ArduCopter 모드 번호 |

ArduCopter 모드 번호:

| SDACS Phase | ArduCopter 모드 | custom_mode |
|-------------|----------------|-------------|
| ENROUTE | Guided | 4 |
| HOLDING | Loiter | 5 |
| RTL | RTL | 6 |
| LANDING | Land | 9 |

---

### 3.3 COMMAND_LONG (#76)

비상 명령 전송용 범용 메시지.

| 명령 | MAV_CMD | 설명 |
|------|---------|------|
| 비상 착륙 | MAV_CMD_NAV_LAND (21) | 즉시 착륙 명령 |
| 엔진 정지 | MAV_CMD_COMPONENT_ARM_DISARM (400) | param1=0 |
| 고도 변경 | MAV_CMD_DO_CHANGE_ALTITUDE (186) | HITL 고도 충돌 회피 |

---

## 4. 텔레메트리 JSON 포맷 (Ground ↔ Bridge)

### 4.1 Bridge → Ground (텔레메트리 push)

```json
{
  "type": "telemetry",
  "drone_id": "DR007",
  "ts": 1716000000.123,
  "lat": 34.9751,
  "lon": 126.9692,
  "alt_m": 60.0,
  "vx": 5.0,
  "vy": -1.2,
  "vz": 0.0,
  "heading_deg": 270.5,
  "battery_pct": 82.3,
  "flight_phase": "ENROUTE"
}
```

### 4.2 Ground → Bridge (어드바이저리 명령)

```json
{
  "type": "advisory",
  "drone_id": "DR007",
  "ts": 1716000000.200,
  "advisory_type": "EVADE_APF",
  "vector": [3.2, -1.1, 0.0],
  "duration_s": 10.0,
  "severity": "HIGH"
}
```

---

## 5. 연결 파라미터

| 파라미터 | 기본값 | CLI 플래그 |
|---------|--------|-----------|
| MAVLink URI | `udp:0.0.0.0:14550` | `--mavlink-uri` |
| Ground URI | `tcp://localhost:5555` | `--ground-uri` |
| Drone ID | 0 | `--drone-id` |
| 재연결 대기 | 0.5/1/2/5/10 s | 코드 상수 |
| 최대 재연결 | 10회 | `MAX_RECONNECT_ATTEMPTS` |

---

## 6. Lost-Link 프로토콜

HEARTBEAT 수신 중단 감지 시 3단계 시퀀스:

```
HEARTBEAT 중단 감지 (>3s)
    │
    ▼ Phase 1 (0~30s)
  HOLDING (loiter in-place)
  → MAVLink: SET_MODE(Loiter)
    │
    ▼ Phase 2 (30s 이후)
  RTL (Return To Launch)
  → MAVLink: SET_MODE(RTL), alt=80m
    │
    ▼ Phase 3 (착륙 패드 50m 이내)
  LANDING
  → MAVLink: SET_MODE(Land)
```

해당 DroneState 전이: `ENROUTE → HOLDING → RTL → LANDING → GROUNDED`

---

## 7. 구현 현황 (onboard_bridge.py)

| 기능 | 상태 | 비고 |
|------|------|------|
| HEARTBEAT 감지 | ✅ 구현 | |
| GLOBAL_POSITION_INT 파싱 | ✅ 구현 | |
| BATTERY_STATUS 파싱 | ✅ 구현 | |
| ATTITUDE 파싱 | 🔵 스켈레톤 | `# TODO: parse attitude` |
| SET_POSITION_TARGET 전송 | 🔵 스켈레톤 | `# TODO: translate advisory` |
| SET_MODE 전송 | 🔵 스켈레톤 | `# TODO: mode switch` |
| Ground 링크 JSON 통신 | ✅ 구현 | asyncio TCP |
| 재연결 로직 | ✅ 구현 | exponential backoff |
| Lost-Link 3단계 | 🔵 부분 구현 | Phase 1만 완료 |

다음 구현 우선순위: `SET_POSITION_TARGET` 어드바이저리 변환 → `SET_MODE` RTL/Land → ATTITUDE 파싱

---

## 8. HITL 테스트 연결 설정

ArduCopter SITL + MAVProxy + onboard_bridge 연동:

```bash
# Terminal 1: ArduCopter SITL
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550

# Terminal 2: onboard_bridge
python -m src.hardware.onboard_bridge \
    --mavlink-uri udp:127.0.0.1:14550 \
    --ground-uri tcp://127.0.0.1:5555 \
    --drone-id 0

# Terminal 3: SDACS Ground Controller
python main.py visualize  # 또는 API 서버
```

관련 문서: [HITL_CHECKLIST.md](HITL_CHECKLIST.md)
