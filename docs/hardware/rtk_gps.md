# P694 — RTK-GPS 센티미터 정밀도 측위

## 목표
u-blox ZED-F9P 듀얼 안테나로 RTK Fix 상태 유지 + AirspaceController에 cm급 위치 피드백.

## 구성
```
[Rover (드론)]                [Base (지상국)]
  ZED-F9P RTK rover     ←──── ZED-F9P RTK base
  + Tallysman 안테나          + 측량용 안테나
  + Pixhawk GPS1              + RTKLIB / VRS-RTK
                              + NTRIP caster
```

## 단계

### 1. Base station 셋업 (NTRIP)
```bash
# RTKLIB strsvr로 base RTCM3 송출
str2str -in serial://ttyACM0:115200#ubx \
        -out ntrips://:password@0.0.0.0:2101/RTK
```

### 2. Rover 설정 (u-center)
1. UART1 → Pixhawk GPS1 (115200 baud)
2. 메시지: NAV-PVT + NAV-RELPOSNED + RTCM3
3. 좌표계: WGS84 (EPSG:4326)
4. RTK 모드: Fixed (Float은 fallback)

### 3. SDACS 피드백 통합
```python
from simulation.rtk_gps_handler import RTKHandler
rtk = RTKHandler(uart='/dev/ttyACM1', base_ntrip='ntrip://your-vrs.kr:2101')

while True:
    pos = rtk.read()  # {lat, lon, alt, fix_type, h_acc_m, v_acc_m}
    if pos.fix_type == 'FIX' and pos.h_acc_m < 0.02:
        controller.update_position(drone_id='SDACS-001', pos=pos)
    else:
        # Fallback: 단독 GPS
        controller.update_position(... , source='dGPS')
```

### 4. 검증
```bash
# 정지 상태에서 1시간 측정 → 표준편차 < 2cm
python scripts/rtk_static_test.py --duration 3600
```

## 트러블슈팅
| 증상 | 원인 | 해결 |
|---|---|---|
| Float만 유지 | Base 좌표 부정확 | survey-in 24h 이상 |
| 가끔 Fix loss | Multipath | Tallysman 안테나 고도 +50cm |
| h_acc > 5cm | RTCM 지연 | NTRIP 캐스터 변경 (한국: VRS-RTK) |

## 한국 RTK 인프라
- **국토지리정보원 VRS-RTK**: 무료, 가입 필요 (`vrs.ngii.go.kr`)
- **민간 NTRIP**: NSS RTK (1만원/월)

## 다음 단계
P694 → [P695 Failsafe 로직](failsafe_logic.md)
