# P691 — Pixhawk 6X / Cube Orange 펌웨어 + PX4 v1.15+

## 목표
SDACS AirspaceController가 송신하는 MAVLink 명령을 수신·실행할 수 있도록 FC 펌웨어 + 설정 검증.

## 준비물
- Pixhawk 6X 또는 Cube Orange
- microSD 16GB (Class 10)
- USB-C 케이블
- QGroundControl 4.3+

## 단계

### 1. PX4 v1.15+ 빌드 (선택, 권장 stable 4.5)
```bash
git clone --recursive https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot && git checkout v1.15.4
make px4_fmu-v6x_default
make px4_fmu-v6x_default upload   # USB로 자동 플래시
```

### 2. QGroundControl로 설정
1. 차량 자동 설정 (Airframe = Generic Quadrotor X)
2. RC 캘리브레이션 (트랜스미터 페어링)
3. ESC 캘리브레이션 (모터 동시 활성)
4. 컴파스/가속도/지자기 캘리브레이션 (3-점)
5. **MAVLink 통신**: TELEM2 포트 = 921600 baud, Companion 모드

### 3. SDACS 연동 검증
```bash
# 호스트 PC에서
python simulation/onboard_bridge.py --port /dev/ttyACM0 --baud 921600

# 예상 출력
[INFO] MAVLink heartbeat 수신: SYSID=1, GCS_SYSID=255
[INFO] AirspaceController 명령 수신 대기 중...
```

### 4. SITL → HITL 전환 체크리스트
- [ ] PX4 펌웨어 v1.15+ 플래시 완료
- [ ] QGC `Sensors` 모두 ✓ (적색 X 없음)
- [ ] MAVLink heartbeat 1Hz 안정 수신
- [ ] **모터 비활성 상태**에서 ARMED → DISARMED 토글 100회 무오류
- [ ] 페일세이프 (RC loss, GPS loss, batt low) 모두 ✓

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| Heartbeat 끊김 | Baudrate 불일치 | TELEM2 = 921600 재확인 |
| Compass interference | 모터 전류 노이즈 | GPS 마스트 50mm+ 이격 |
| GPS fix 실패 | 실내 시야 부족 | 옥상/창가 1시간 대기 |
| ESC 캘 실패 | LiPo 전압 부족 | 4S=16.8V 만충 후 재시도 |

## 다음 단계
P691 검증 완료 → [P692 Jetson MAVLink 브릿지](jetson_mavlink.md)
