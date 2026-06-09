# SDACS HITL 체크리스트 (HITL_CHECKLIST)

> **문서 번호**: SDACS-HW-002  
> **버전**: 0.9 (초안)  
> **작성일**: 2026-05-18  
> **대상**: onboard_bridge.py HITL 연동 테스터  
> **관련 문서**: [MAVLINK_SPEC.md](MAVLINK_SPEC.md)

---

## 사전 요구사항

| 항목 | 확인 |
|------|------|
| ArduCopter SITL 설치 (`sim_vehicle.py` 실행 가능) | ☐ |
| MAVProxy 설치 (`pip install MAVProxy`) | ☐ |
| pymavlink 설치 (`pip install pymavlink`) | ☐ |
| Python 3.10+ 환경 | ☐ |
| SDACS 패키지 의존성 설치 (`pip install -e .`) | ☐ |
| 포트 14550 (UDP), 5555 (TCP) 방화벽 허용 | ☐ |

---

## Phase 1: 환경 구동 체크리스트

### 1.1 ArduCopter SITL 기동

```bash
# Terminal 1 — SITL 시작
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550 --console
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `APM: EKF3 IMU0 initialised` 출력 | 30s 이내 | ☐ |
| MAVProxy 콘솔 `HEARTBEAT` 수신 | 1Hz 이상 | ☐ |
| `GPS: 3D fix` 획득 | `GPS: 3D fix` 메시지 | ☐ |
| 배터리 상태 정상 | `BATTERY_STATUS` 수신 | ☐ |

### 1.2 SDACS Ground Controller 기동

```bash
# Terminal 2 — SDACS Ground (텔레메트리 수신 서버)
python main.py api  # FastAPI 포트 8000
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `Uvicorn running on http://0.0.0.0:8000` | 출력 확인 | ☐ |
| `GET /health` 응답 | `{"status": "ok"}` | ☐ |
| TCP 5555 리스닝 준비 | 소켓 LISTEN 상태 | ☐ |

### 1.3 onboard_bridge.py 기동

```bash
# Terminal 3 — Bridge
python -m src.hardware.onboard_bridge \
    --mavlink-uri udp:127.0.0.1:14550 \
    --ground-uri tcp://127.0.0.1:5555 \
    --drone-id 0
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `[Bridge] MAVLink connected` 출력 | 연결 성공 메시지 | ☐ |
| `[Bridge] Ground connected` 출력 | TCP 연결 메시지 | ☐ |
| `[Bridge] HEARTBEAT received` 반복 출력 | 1Hz 주기 | ☐ |

---

## Phase 2: 텔레메트리 파싱 검증

### 2.1 GLOBAL_POSITION_INT 파싱

```bash
# MAVProxy에서 위치 확인
module load graph
graph GLOBAL_POSITION_INT.lat GLOBAL_POSITION_INT.lon
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| Bridge 로그에 `lat_deg` 출력 | ±90° 범위 내 | ☐ |
| Bridge 로그에 `lon_deg` 출력 | ±180° 범위 내 | ☐ |
| `alt_m` 단위 변환 (mm → m) | SITL alt와 ±0.1m | ☐ |
| `vx_ms`, `vy_ms` cm/s → m/s 변환 | SITL 속도와 일치 | ☐ |
| Ground에 텔레메트리 JSON push 수신 | `"type": "telemetry"` 포함 | ☐ |

### 2.2 BATTERY_STATUS 파싱

```bash
# MAVProxy에서 배터리 확인
status BATTERY_STATUS
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `battery_pct` 0~100% 범위 | SITL 배터리와 일치 | ☐ |
| 5% 미만 시 `BATTERY_CRITICAL` 어드바이저리 | Ground에서 수신 확인 | ☐ |

### 2.3 HEARTBEAT 수신 모니터링

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `heartbeat_age_s` ≤ 3.0s 유지 | 정상 링크 상태 | ☐ |
| SITL 종료 후 3s 경과 → Lost-Link 감지 | `[Bridge] Link lost` 출력 | ☐ |

---

## Phase 3: 어드바이저리 명령 전송 검증

### 3.1 HOLD 명령 (기본)

```bash
# Ground에서 Advisory JSON 전송
curl -X POST http://localhost:8000/advisory \
  -H "Content-Type: application/json" \
  -d '{"drone_id":"0","advisory_type":"HOLD","vector":[0,0,0],"duration_s":5.0}'
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| MAVProxy에서 `SET_POSITION_TARGET_LOCAL_NED` 수신 | vx=vy=vz=0 | ☐ |
| SITL 드론 호버 유지 | 위치 변화 < 0.5m | ☐ |

### 3.2 EVADE_APF 명령

```bash
curl -X POST http://localhost:8000/advisory \
  -H "Content-Type: application/json" \
  -d '{"drone_id":"0","advisory_type":"EVADE_APF","vector":[3.2,-1.1,0.0],"duration_s":10.0}'
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `SET_POSITION_TARGET_LOCAL_NED` 전송 | vx=3.2, vy=-1.1, vz=0.0 | ☐ |
| SITL 드론 북동 방향 이동 | GPS 위치 변화 확인 | ☐ |
| 10s 후 명령 종료 | HOLD로 복귀 | ☐ |

### 3.3 RTL 명령

```bash
curl -X POST http://localhost:8000/advisory \
  -H "Content-Type: application/json" \
  -d '{"drone_id":"0","advisory_type":"RTL"}'
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `SET_MODE` 전송 (custom_mode=6) | MAVProxy 모드 `RTL` | ☐ |
| SITL 드론 이륙 위치로 복귀 | 높이 80m로 상승 후 귀환 | ☐ |

### 3.4 LAND 명령

```bash
curl -X POST http://localhost:8000/advisory \
  -H "Content-Type: application/json" \
  -d '{"drone_id":"0","advisory_type":"LAND"}'
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `SET_MODE` 전송 (custom_mode=9) | MAVProxy 모드 `LAND` | ☐ |
| SITL 드론 착지 | `DISARMED` 상태 전환 | ☐ |

---

## Phase 4: Lost-Link 프로토콜 검증

```bash
# SITL 강제 종료로 Link Loss 시뮬레이션
kill $(pgrep -f sim_vehicle)
```

| 단계 | 시간 | 확인 항목 | 기대값 | 결과 |
|------|------|-----------|--------|------|
| Phase 1 | 0~30s | `SET_MODE(Loiter)` 전송 | MAVProxy 모드 `Loiter` | ☐ |
| Phase 2 | 30s~ | `SET_MODE(RTL)` 전송 | MAVProxy 모드 `RTL` | ☐ |
| Phase 3 | 착륙 패드 50m 이내 | `SET_MODE(Land)` 전송 | MAVProxy 모드 `Land` | ☐ |
| 완료 | 착지 후 | `GROUNDED` 상태 | Bridge 로그 확인 | ☐ |

---

## Phase 5: 재연결 로직 검증

```bash
# SITL 재기동으로 재연결 테스트
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| Bridge 자동 재연결 시도 | 0.5→1→2→5→10s 백오프 | ☐ |
| 최대 10회 재연결 후 포기 | `MAX_RECONNECT_ATTEMPTS exceeded` | ☐ |
| 재연결 성공 시 텔레메트리 재개 | Ground에서 텔레메트리 재수신 | ☐ |

---

## Phase 6: GPS 장애 시뮬레이션

```bash
# MAVProxy에서 GPS 실패 주입
param set SIM_GPS_DISABLE 1
```

| 확인 항목 | 기대값 | 결과 |
|-----------|--------|------|
| `SYS_STATUS` GPS 비트 이상 감지 | `GPS_LOSS` 장애 타입 설정 | ☐ |
| Ground에 `failure_type: GPS_LOSS` 전송 | JSON 필드 확인 | ☐ |
| GPS 복구 후 정상 복귀 | `failure_type: NONE` | ☐ |

---

## 최종 합격 기준

모든 Phase 체크리스트 항목 100% 통과 시 HITL 검증 완료.

| Phase | 항목 수 | 합격 기준 |
|-------|---------|-----------|
| Phase 1 (환경 구동) | 12 | 전체 통과 |
| Phase 2 (텔레메트리) | 10 | 전체 통과 |
| Phase 3 (어드바이저리) | 10 | 전체 통과 |
| Phase 4 (Lost-Link) | 4 | 전체 통과 |
| Phase 5 (재연결) | 3 | 전체 통과 |
| Phase 6 (GPS 장애) | 3 | 전체 통과 |

---

## 알려진 제약 및 TODO

| 기능 | 상태 | 비고 |
|------|------|------|
| ATTITUDE 파싱 (`heading_deg` 보정) | ✅ 구현 | `GLOBAL_POSITION_INT.hdg` 미지값(65535) 시 `ATTITUDE.yaw` 폴백 — 단위 테스트 7종 |
| SET_POSITION_TARGET 어드바이저리 변환 | 🔵 스켈레톤 | Phase 3 테스트 불완전 |
| SET_MODE RTL/Land | 🔵 스켈레톤 | Phase 3/4 부분만 가능 |
| Lost-Link Phase 2/3 | 🔵 부분 구현 | Phase 1만 완료 |

> 위 TODO 항목은 [`onboard_bridge.py`](../src/hardware/onboard_bridge.py) 구현 완료 후 재검증 필요.

---

관련 문서: [MAVLINK_SPEC.md](MAVLINK_SPEC.md) | [TEST_PROCEDURES.md](TEST_PROCEDURES.md)
