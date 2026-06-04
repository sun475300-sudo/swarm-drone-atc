# P698 — 실외 소규모 스웜 비행 프로토콜

## 목표
3-5기 스웜 실외 비행 시험. 정지비행 → 포메이션 → APF 회피 → CBS 경로 양보 단계적 검증.

## 사전 요건
- ✅ P691-P697 모두 PASS
- ✅ 항공안전법 사전 비행 승인 (국토부 e민원24)
- ✅ 드론 책임보험 5억 이상
- ✅ 비행 구역: 안성·고흥·서산 등 시범 운영 구역
- ✅ 기상: 풍속 < 7 m/s, 강수 없음, 시정 1km+

## 비행 매트릭스

| Mission | 드론 | 시간 | 검증 항목 |
|---|---|---|---|
| M1 | 1기 호버 | 1분 | RTL·LOITER 정상 |
| M2 | 1기 사각 경로 | 3분 | RTK Fix 유지율 >95% |
| M3 | 2기 동시 호버 (5m 이격) | 2분 | 충돌 없음 |
| M4 | 3기 V-formation | 5분 | 형성 유지, 위치 오차 <2m |
| M5 | 3기 APF 회피 | 5분 | 침입자 회피 성공 |
| M6 | 5기 CBS 양보 | 10분 | 회랑 우선순위 동작 |

## 매 비행 전 체크리스트 (10분)

- [ ] 풍속 측정 (휴대 풍속계)
- [ ] GPS Sat ≥ 14, HDOP < 1.5
- [ ] RTK Fix 5분 유지
- [ ] 배터리 만충 + 예비 1팩
- [ ] RC 페어링 + 페일세이프 토글 1회
- [ ] 컴파스 캘 OK (적색 X 없음)
- [ ] Kill switch 작동 확인
- [ ] 관찰자 1명 배치
- [ ] 비행구역 NOTAM 확인

## 데이터 수집

```bash
# 비행 중 자동 로깅
python scripts/log_flight_data.py \
    --output flights/2026-06-15_M4/ \
    --rate 10 \
    --include rtk gps barometer mavlink controller

# 비행 후 분석
python scripts/analyze_flight.py flights/2026-06-15_M4/
# 출력: 위치 오차, RTK 손실, CPU 사용률, 배터리 효율
```

## 사고 대응

| 상황 | 대응 |
|---|---|
| 의도치 못한 모터 정지 | 즉시 RC takeover → LAND |
| RTK 손실 | LOITER 후 dGPS 모드로 진행 |
| 1기 RTL 실패 | 다른 기는 안전 거리 유지하며 호버, 수동 회수 |
| 관제 명령 통신 실패 | 마지막 명령 유지, 5분 후 RTL |
| 인접 항공기 출현 | 즉시 LAND in place |

## 보고

비행 후 24시간 내:
- [`docs/track_b/flight_logs/`](../track_b/flight_logs/) 에 로그 + 영상 + KPI 표 저장
- 사고 발생 시 국토부 항공사고 신고

## 다음 단계
P698 → [P699 환경 시나리오](environmental_test.md)
