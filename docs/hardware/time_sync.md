# P696 — 스웜 시간 동기화 (PTP/NTP <10ms jitter)

## 목표
3-5기 스웜의 시간축을 PTP(IEEE 1588) 또는 NTP로 정렬, jitter < 10ms. CBS 충돌해결의 시간 정확도 보장.

## 옵션 비교

| 프로토콜 | jitter | 인프라 | 비고 |
|---|---|---|---|
| **PTP (IEEE 1588v2)** | <1ms | 전용 스위치 필요 | 정확, 복잡 |
| **chrony NTP** | 5-10ms | 일반 Wi-Fi/이더넷 | 권장 |
| **GPS PPS** | <100ns | GPS 신호 필요 | 옥외 한정 |

권장: **chrony NTP + GPS PPS 보조**

## 단계

### 1. 마스터 노드 (지상국)
```bash
sudo apt install chrony
sudo nano /etc/chrony/chrony.conf
# 추가:
allow 192.168.0.0/16
local stratum 8
sudo systemctl restart chrony
```

### 2. 슬레이브 (각 드론 Jetson)
```bash
sudo nano /etc/chrony/chrony.conf
# 추가:
server 192.168.0.1 iburst prefer minpoll 4 maxpoll 4
sudo systemctl restart chrony

# 확인 (5분 후)
chronyc tracking
# 목표: System time offset to NTP source: < 5ms
```

### 3. GPS PPS 보강 (옥외)
```bash
# Jetson에 PPS 입력 핀 연결 (Pin 27)
sudo apt install gpsd pps-tools
sudo nano /etc/chrony/chrony.conf
# 추가:
refclock SHM 0 refid GPS lock NMEA precision 1e-1
refclock PPS /dev/pps0 lock GPS refid PPS precision 1e-7
```

### 4. SDACS 통합
```python
from simulation.swarm_time_sync import TimeSync
ts = TimeSync(min_drones=3, max_jitter_ms=10)

if not ts.is_synchronized():
    logger.error('스웜 시간 동기화 실패 → 비행 보류')
    sys.exit(1)

# 동기화 OK
controller.start_cbs_planning()
```

## 검증
```bash
# 3대 동시 측정 (5분)
python scripts/measure_swarm_jitter.py --duration 300
# 목표: 평균 < 5ms, p99 < 10ms
```

## 트러블슈팅
| 증상 | 원인 | 해결 |
|---|---|---|
| offset > 50ms | Wi-Fi 지연 | iperf3 로 대역폭 검사 |
| jitter spike | CPU thermal throttle | Orin Nano 7W 모드 시 우회 |
| GPS PPS 불안정 | 옥내 위성 신호 약 | NTP만 사용 |

## 다음 단계
P696 → [P697 MoCap HITL](mocap_hitl.md)
