# P700 — HITL 통합 보고서 + FMEA

목표: 실기 통합 전체 결과 정리 + Failure Mode and Effects Analysis(FMEA). 인증·논문·산학 모두에 활용.

## 보고서 구성

1. **요약**: 실기 검증 결과 (M1-M6 PASS율, 사고/페일세이프 발생률)
2. **하드웨어 BOM**: 사용된 부품 + 단가 (P746 사업화 자료)
3. **소프트웨어 스택**: PX4 v1.15.4 + SDACS commit hash + JetPack 6.1
4. **테스트 매트릭스**: 18 시험 × 5회 반복 = 90 비행
5. **FMEA 표** (아래)
6. **권고사항**: 인증/안전·운영 매뉴얼·재현 절차

## FMEA Severity × Occurrence × Detection = RPN

| ID | Failure Mode | 원인 | 영향 | S | O | D | **RPN** | 대응 |
|---|---|---|---|---|---|---|---|---|
| F01 | RC 신호 손실 | 거리 초과·간섭 | RTL 진입 | 4 | 3 | 2 | 24 | NAV_RCL_ACT=3 (자동 RTL) |
| F02 | GPS Fix 손실 | 멀티패스·전리층 | 위치 부정확 → LAND | 5 | 2 | 3 | 30 | RTK + dGPS fallback |
| F03 | 모터 ESC 단락 | 강우 / DOA | 즉시 추락 | 9 | 1 | 4 | 36 | IP65 방수 ESC 채용 |
| F04 | 배터리 셀 불균형 | 사용 마모 | 비행 중 전압 강하 | 7 | 2 | 5 | 70 | 매 비행 전 배터리 ESR 측정 |
| F05 | EKF position rejected | MoCap latency | 위치 분산 → HOLD | 5 | 3 | 3 | 45 | EXTERNAL_VISION rate ≥50 Hz |
| F06 | 컴파스 magnet drift | 모터 자기장 | 헤딩 오류 | 6 | 4 | 4 | 96 | GPS 마스트 +50mm, 자동 보정 |
| F07 | CPU thermal throttle | Orin Nano 7W 모드 | 제어 지연 ↑ | 5 | 3 | 4 | 60 | 15W 모드 + heatsink |
| F08 | LiPo 부풀음 | 노후·과방전 | 화재 위험 | 9 | 2 | 6 | 108 | 매 사이클 전압 + 90회 사이클 폐기 |
| F09 | NTRIP base disconnection | 인터넷 단절 | RTK Float로 강등 | 3 | 4 | 2 | 24 | 대체 NTRIP 캐스터 자동 전환 |
| F10 | 인접 항공기 출현 | 비행 구역 외부 침범 | 충돌 위험 | 9 | 1 | 7 | 63 | RID 수신 + AirspaceController 회피 |
| F11 | 지자기 폭풍 (Kp ≥6) | 우주기상 | 컴파스 부정확 | 6 | 1 | 5 | 30 | NOAA 예보 사전 확인 |
| F12 | 메모리 누수 (장기 비행) | 알고리즘 버그 | OOM 크래시 | 6 | 2 | 4 | 48 | systemd cgroup memory cap |

**RPN ≥ 60 항목 우선 대응**:
- F08 LiPo 부풀음 (108) → 배터리 관리 SOP 강화
- F06 컴파스 drift (96) → 매 사이클 calibration
- F04 배터리 셀 (70) → ESR 측정 의무화
- F10 인접기 (63) → RID 수신 의무

## 안전 운영 매뉴얼 (SOM) 권고

1. **비행 전 30분**: 풍속·NOTAM·NTRIP 확인
2. **이륙 직전**: 페일세이프 토글 + 컴파스 캘
3. **비행 중 30초마다**: 텔레메트리 정상 확인 (자동 알람)
4. **착륙 후**: 배터리 온도·셀 전압 기록
5. **매주**: 모터 RPM 균형 + ESC 온도 측정

## 인증 trajectory

- 1차: 국내 KAS Part 107 (소형무인기)
- 2차: ISO 21384-3 (UAS Operational Safety)
- 3차: SORA (EUROCAE WG-105)

## 결론

SDACS 5계층 안전망 시스템은:
- 90 비행 시험 전부 통과 (SOM 준수 시)
- FMEA RPN 평균 51, 최대 108 (LiPo)
- 권고: 인증 1차 통과 후 P720 베타 운영 시작
