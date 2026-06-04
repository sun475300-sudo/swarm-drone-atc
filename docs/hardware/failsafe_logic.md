# P695 — 페일세이프 로직 (RC loss / Geofence / RTL)

## 목표
전파 간섭·통신 단절·배터리 위기 시 안전한 자동 대응. 5계층 안전망의 **Layer 1 (드론 자율)** 담당.

## 시나리오 매트릭스

| 트리거 | 시간 | 대응 | 비고 |
|---|---|---|---|
| RC signal loss | 2초 | LOITER 5초 → RTL | RC 재연결 시 즉시 복귀 |
| Telemetry loss (Jetson) | 5초 | LOITER 10초 → RTL | RC만 활성 시 정상 비행 |
| GPS loss (3D fix 끊김) | 3초 | LAND in place | RTL 불가 |
| Battery < 25% | 즉시 | RTL | 회랑 우선순위 ↑ |
| Battery < 15% | 즉시 | LAND in place | 안전 영역 외 |
| Geofence breach | 즉시 | HOLD → RTL | NFZ·고도·반경 |
| Compass calibration drift | 즉시 | RTL | EKF 분산 ↑ |

## 구현

### PX4 PARAM 설정 (QGC 또는 mavparam)
```
COM_RC_LOSS_T = 2.0         # RC 손실 2초 후 트리거
COM_RCL_EXCEPT = 0           # RC 손실 시 예외 없음
NAV_RCL_ACT = 3              # RTL
COM_LOW_BAT_ACT = 2          # RTL
GF_ACTION = 3                # Geofence 위반 시 RTL
GF_MAX_HOR_DIST = 500.0      # 500m 반경
GF_MAX_VER_DIST = 120.0      # 120m 고도 한도
```

### `simulation/failsafe_manager.py` 통합
```python
from simulation.failsafe_manager import FailsafeManager
fs = FailsafeManager(controller=airspace_ctrl, drone_id='SDACS-001')

# 자동 트리거 검사 (10 Hz)
fs.check_battery(drone_state.battery_pct)
fs.check_gps(drone_state.gps_fix_type)
fs.check_geofence(drone_state.position)

# 트리거 시 콜백
fs.on_trigger = lambda reason: logger.warn(f'Failsafe: {reason} → RTL')
```

## 시험 절차

### 1. SITL에서 강제 트리거 (안전)
```bash
# RC 손실 시뮬레이션
mavproxy --master=udp:0.0.0.0:14550
> param set NAV_RCL_ACT 3
> radio override rc 1 1500  # 통신 두절 시뮬
> wait_event MISSION RTL    # RTL 진입 확인
```

### 2. HITL에서 실 RC 끄기
- 호버 1분 → RC 트랜스미터 OFF → 5초 내 LOITER 진입 → 10초 후 RTL → 홈 위치 ±2m 착륙

### 3. 배터리 위기 (실외)
- 25% 시점 RTL 자동 트리거 확인
- 사람이 수동으로 takeover 가능

## 안전 체크리스트
- [ ] 모든 페일세이프 SITL 통과
- [ ] HITL에서 RC loss → RTL 정상 (3회)
- [ ] Geofence 침범 → HOLD (3회)
- [ ] **모터 정지 우선**: 어떤 페일세이프든 인구 밀집지로 향하지 않음
- [ ] LAND in place 시 자동 disarm 확인

## 다음 단계
P695 → [P696 시간 동기화](time_sync.md)
