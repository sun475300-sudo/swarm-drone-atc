# Track A 실기 통합 가이드 (P691-P700)

목포대 캡스톤 SDACS의 SITL 검증 완료 제어 스택을 **실제 하드웨어**로 이식하는 통합 가이드.

## 하드웨어 요구사항

| 구성요소 | 권장 모델 | 비고 |
|---|---|---|
| **FC** | Pixhawk 6X / Cube Orange | PX4 v1.15+ |
| **컴패니언 컴퓨터** | NVIDIA Jetson Orin Nano 8GB | MAVLink 브릿지 |
| **RTK-GPS** | u-blox ZED-F9P + base station | <2cm 정밀도 |
| **무선통신** | TBS Crossfire / Herelink Long-Range | 30km+ |
| **모터/ESC** | T-Motor MN3110 / 4-in-1 50A | 5kg+ MTOW |
| **카메라(선택)** | FLIR Boson 320 (P735 연동) | EO/IR |

**필수 검증**: 모든 단계는 시뮬레이션 → SITL → HITL → 실외 순서. 단계 건너뛰기 금지.

## Phase별 가이드

| Phase | 가이드 문서 | 추정 기간 |
|---|---|---|
| P691 | [pixhawk_setup.md](pixhawk_setup.md) | 3일 |
| P692 | [jetson_mavlink.md](jetson_mavlink.md) | 5일 |
| P693 | [remote_id_broadcast.md](remote_id_broadcast.md) | 2일 |
| P694 | [rtk_gps.md](rtk_gps.md) | 3일 |
| P695 | [failsafe_logic.md](failsafe_logic.md) | 4일 |
| P696 | [time_sync.md](time_sync.md) | 3일 |
| P697 | [mocap_hitl.md](mocap_hitl.md) | 5일 |
| P698 | [outdoor_test_protocol.md](outdoor_test_protocol.md) | 7일 |
| P699 | [environmental_test.md](environmental_test.md) | 10일 |
| P700 | [fmea_report.md](fmea_report.md) | 5일 |

**총 추정**: 47일 (개인 기준, 병렬 일부 가능)

## 안전 체크리스트

- [ ] **법적 절차**: 항공안전법 사전 비행 승인(국토부)
- [ ] **보험**: 드론 책임보험 가입 (5억 이상)
- [ ] **장소**: 실외 비행 허용 구역 (안성 등) 확인
- [ ] **인력**: 조종사 1명 + 안전 감독관 1명 최소
- [ ] **킬 스위치**: 모든 단계 RC 조종기 페일세이프 동작 확인
- [ ] **거리**: 인구 밀집지 100m 이상 이격
- [ ] **시야**: VLOS(Visual Line of Sight) 유지

## SITL 회귀 검증 (실기 진입 전)

```bash
# 풀 회귀: 2,823+ 테스트
pytest tests/ -v

# Track A SW 컴포넌트만
pytest tests/test_p691_p700_track_a.py -v

# Monte Carlo 안전성 (failure 시나리오 30회)
python main.py monte-carlo --mode hardware-pre-flight
```
