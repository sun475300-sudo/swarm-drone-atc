# P692 — Jetson Orin Nano MAVLink 브릿지

## 목표
Jetson Orin Nano(컴패니언 컴퓨터)에서 SDACS 제어 스택을 실행하며, Pixhawk와 MAVLink로 양방향 통신.

## 하드웨어 연결
```
[Pixhawk TELEM2] ─── UART ─── [Jetson Orin J17]
   (TX/RX/GND)               (UART2 /dev/ttyTHS0)
```
- 3.3V 레벨 매칭 (Pixhawk TELEM2는 5V→3.3V 분압)
- 케이블 길이 < 30cm (노이즈 최소)

## 단계

### 1. Jetson 셋업
```bash
# JetPack 6.1 (Ubuntu 22.04)
sudo apt update && sudo apt install -y python3-pip git
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc
pip install -r requirements.txt pymavlink

# UART 권한
sudo usermod -aG dialout $USER && sudo reboot
```

### 2. `simulation/onboard_bridge.py` 실행
```bash
python simulation/onboard_bridge.py \
    --port /dev/ttyTHS0 --baud 921600 \
    --controller-host airspace-controller.local --controller-port 5556
```

### 3. 양방향 통신 검증
```bash
# 로그 확인
tail -f /tmp/onboard_bridge.log

# 예상
[INFO] PX4 heartbeat 수신 OK (SYSID=1)
[INFO] AirspaceController 연결 OK
[INFO] CPA advisory 수신 → MAV_CMD_DO_REPOSITION 전송
```

### 4. 지연시간 측정
```bash
python scripts/measure_mavlink_latency.py --duration 60
# 목표: 평균 <20ms, p99 <50ms
```

## 안전 가드
- Jetson 5V 4A 별도 BEC (기체 BEC와 분리, 노이즈 격리)
- HEAT-SINK + FAN 필수 (Orin Nano 8GB 모드 = 7-15W)
- microSD 부팅 → NVMe 부팅 전환 권장 (10배 빠름)

## SITL → HITL 다리 (테스트)
```bash
# 호스트에서 SITL 가동
make px4_sitl gz_x500

# Jetson에서 onboard_bridge가 SITL 또는 실기에 연결
python simulation/onboard_bridge.py --sitl-host host.docker.internal
```

## 다음 단계
P692 검증 완료 → [P693 Remote ID 방송](remote_id_broadcast.md)
