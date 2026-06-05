# 🔧 Pixhawk SDACS HITL 통합 가이드 (트랙 ③ 스캐폴드)

*Created: 2026-06-05 — Phase 22 (Digital Twin) 격상용*

## 🎯 목표

실 Pixhawk 6X 또는 SITL 시뮬에서 송신되는 MAVLink GLOBAL_POSITION_INT (msgid=33)를 WebSocket을 통해 시뮬레이터 `_sdacs.dtwinApplyGPI(payload, droneIdx)`로 매핑하여 시뮬-실드론 양방향 HITL을 구축한다.

## 📋 하드웨어 요구사항

- Pixhawk 6X / Cube Orange (또는 PX4 SITL `make px4_sitl gz_x500`)
- Jetson Orin Nano (MAVLink 브리지)
- u-blox ZED-F9P RTK (옵션, Phase 22 정밀화)
- USB-C UART 케이블 또는 LAN (TCP/UDP 5760)

## 🔌 데이터 흐름

```
Pixhawk → MAVLink2 UART/TCP → Jetson WebSocket Bridge → 
  WebSocket :8765 → 시뮬 브라우저 → _sdacs.dtwinApplyGPI(buffer, idx)
```

## 📦 1단계 — Jetson MAVLink → WebSocket 브리지

`simulation/ws_bridge.py` 가 이미 2Hz 스트리밍 지원. MAVLink GPI 추가:

```python
# simulation/ws_bridge_mavlink.py (신규)
from pymavlink import mavutil
import asyncio, websockets, struct

mav = mavutil.mavlink_connection('udp:0.0.0.0:14550')
async def stream(ws, path):
    while True:
        msg = mav.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=1)
        if msg:
            # 28바이트 little-endian
            buf = struct.pack('<IiiiihhhH',
                msg.time_boot_ms, msg.lat, msg.lon, msg.alt,
                msg.relative_alt, msg.vx, msg.vy, msg.vz, msg.hdg)
            await ws.send(buf)
        await asyncio.sleep(0.1)

asyncio.run(websockets.serve(stream, '0.0.0.0', 8765))
```

## 📦 2단계 — 시뮬레이터 GPI 수신 hook

브라우저 콘솔:
```javascript
const ws = new WebSocket('ws://localhost:8765/mavlink');
ws.binaryType = 'arraybuffer';
ws.onmessage = (ev) => {
    const payload = window._sdacs.dtwinDecodeGPI(ev.data);
    if (payload) window._sdacs.dtwinApplyGPI(payload, 0);  // 첫 드론에 매핑
};
window._sdacs.enableDtwin(true);
window._sdacs.dtwinSetOrigin(34.808, 126.391);  // 목포대
```

## 📦 3단계 — E2E 검증 (10Hz, p99 < 100ms)

```bash
# Pixhawk SITL 기동
cd ~/PX4-Autopilot
make px4_sitl gz_x500

# 시뮬 + 브리지
python3 simulation/ws_bridge_mavlink.py &
python3 -m http.server 8123
# 브라우저 → http://localhost:8123/swarm_3d_simulator.html
```

## 🧪 검증 매트릭스 (Phase 22 격상 완료 기준)

| 항목 | 기준 | 측정 방법 |
|---|---|---|
| 전송 주기 | 10 Hz | `_sdacs.dtwinStats.packetCount` 시간차 |
| p50 지연 | < 50 ms | timestamp 비교 (Pixhawk → render) |
| p99 지연 | < 100 ms | 1분 누적 분포 |
| 좌표 정확도 | ENU ±0.5 m | GPS → Mercator 변환 검증 |
| 5 드론 동시 | 50 Hz 총 throughput | 5 인스턴스 다중 ws 연결 |

## ⏭ 후속 작업

- IMU 자세 매핑 (ATTITUDE msg, Quaternion)
- 명령 역방향 (시뮬 ATC → MAVLink COMMAND_LONG)
- 5 Pixhawk cluster (Phase 45 HITL Cluster 격상)

## 📚 관련

- [`src/digital_twin/sync_engine.py`](../../src/digital_twin/sync_engine.py) — Python 측 sync engine
- [`docs/hardware/jetson_mavlink.md`](jetson_mavlink.md) — 기존 가이드
- [`docs/hardware/fmea_report.md`](fmea_report.md) — 12 failure mode RPN
- 시뮬 hook: `_sdacs.dtwinDecodeGPI / dtwinApplyGPI / dtwinSetOrigin / dtwinStats`
