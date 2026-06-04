# P693 — Remote ID 방송 (ASTM F3411 v2.0)

## 목표
ASTM F3411 v2.0 Broadcast(Bluetooth/Wi-Fi NaN) + Network(LAANC) 양 모드 송출.

## 규격
- **Broadcast**: Bluetooth 4 LE Long Range / Wi-Fi NaN, 1 Hz
- **Network**: HTTPS POST → DET (Discovery & Synchronization)
- **필수 필드**: serial, lat/lon/alt, speed, heading, operator_id, timestamp

## 하드웨어
- 인증 RID 송신기 (Drone Tag DT100 또는 BlueMark DB200) — Pixhawk CAN 또는 USB 연결
- 또는 Jetson Wi-Fi 모듈로 직접 송출 (SDK 필요)

## 단계

### 1. RID 송신기 연동
```bash
python simulation/remote_id_broadcast.py \
    --device /dev/cu.usbserial-rid \
    --serial-no SDACS-001 --operator-id KR.MTU.CAPSTONE
```

### 2. Network RID (LAANC)
```python
from src.airspace.remote_id import LaancClient
client = LaancClient(api_key=os.environ['LAANC_API_KEY'])
client.post_telemetry(drone_state)  # 1 Hz
```

### 3. 수신 검증
```bash
# 별도 RID 수신기(Drone Scanner 앱)로 확인
# 또는 직접 Bluetooth 스니퍼
sudo bluetoothctl scan le
```

## 검증 체크리스트
- [ ] Broadcast: Drone Scanner 앱에서 SDACS-001 ID 수신
- [ ] 좌표 정확도 ±5m 이내 (RTK GPS 사용 시 ±0.5m)
- [ ] 1초 안에 위치 업데이트 반영
- [ ] Network: LAANC 대시보드에 텔레메트리 표시
- [ ] **법규**: 한국은 2024.1.1부터 25kg 이상 의무, 7kg+ 권장

## 트러블슈팅
| 증상 | 해결 |
|---|---|
| 수신기에서 안 보임 | Bluetooth LE Long Range 미지원 → 4.2+ 송신기 |
| LAANC 401 | API 키 만료 / IP whitelist 갱신 |
| 좌표 오류 | EPSG:4326 (WGS84) 확인 |

## 다음 단계
P693 검증 완료 → [P694 RTK-GPS](rtk_gps.md)
