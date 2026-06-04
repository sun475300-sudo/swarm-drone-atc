# P697 — 실내 Motion Capture HITL 셋업

## 목표
Vicon Vero / OptiTrack Prime로 mm급 위치 측정 → SDACS에 피드백, 실내 안전 환경에서 SITL의 다음 단계 검증.

## 하드웨어
- 카메라 ≥8대 (방 6m×6m×3m 기준)
- 마커: 16mm reflective (드론당 4-6개)
- 네트워크: 1GbE 전용 스위치
- 작업 PC: Vicon Tracker 4.0+ 또는 Motive 3.0+

## 구성

```
[8× Vicon Vero] → [Switch] → [Vicon PC: VRPN server]
                                ↓
                          [Jetson: VRPN client]
                                ↓
                          [Pixhawk: EXTERNAL_VISION]
```

## 단계

### 1. 마커 부착 + 캘리브레이션
1. 드론에 마커 4-6개 비대칭 배치 (1g 이내)
2. Tracker에서 `Create Rigid Body` → 이름 `SDACS-001`
3. T-pose 캘리브레이션 → 좌표계 정렬 (Z-up, ENU)

### 2. VRPN 서버 가동 (Vicon PC)
```
Tracker > Object > SDACS-001 > Stream
  Protocol: VRPN
  Port: 3883
  Frame rate: 100 Hz
```

### 3. Jetson에서 VRPN 클라이언트
```python
from simulation.mocap_hitl_bridge import MoCapBridge
bridge = MoCapBridge(
    vrpn_url='vrpn://192.168.0.100:3883/SDACS-001',
    mavlink_target='udp://:14550',
    rate_hz=100,
)
bridge.run()  # VRPN 좌표 → MAVLink EXTERNAL_VISION
```

### 4. Pixhawk 설정
```
EKF2_AID_MASK = 24    # VIS_POS + VIS_YAW 활성
EKF2_HGT_MODE = 3     # VIS height
EKF2_EV_DELAY = 5     # ms
```

### 5. HITL 비행 시험
```bash
# 1. 호버 1분 (자동) — 위치 오차 < 5cm
# 2. 1m 정사각형 4점 이동 — 각 점 ±10cm
# 3. APF 회피 시험: 시뮬레이션 침입자 spawn → 회피 동작
# 4. CBS 우회: 2기 동시 시작 → 회랑 양보 확인
python tests/hitl/mocap_apf_avoidance.py
```

## 안전 가드
- 실내 풀 케이지 (4면 그물망) 필수
- 모터 RPM 30% 제한 (호버 한계)
- 킬 스위치 RC + 비상 정지 빨간 버튼
- 사람 진입 시 자동 LAND (Vicon에 사람 marker 추적)

## 트러블슈팅
| 증상 | 해결 |
|---|---|
| Tracker 마커 손실 | 마커 6개로 증설 + 비대칭 |
| EKF position rejected | EXTERNAL_VISION rate < 50Hz 확인 |
| 진동/오실레이션 | EKF2_EV_DELAY ↑ |

## 다음 단계
P697 → [P698 실외 비행](outdoor_test_protocol.md)
