# P699 — 환경 시나리오 실측 (풍동·강우·저조도)

## 목표
SDACS의 외란 견딤 능력 정량화. SP3 논문(P707) 결과 §4.3의 실험 근거.

## 시나리오

| 환경 | 측정 변수 | 기준 |
|---|---|---|
| **풍동** (실내) | 5/7/10/15 m/s 정상풍 | 위치 오차 <3m, RTL 성공률 100% |
| **강우** (실외/인공) | 강수 5/10 mm/h | 카메라/센서 동작, 모터 방수 OK |
| **저조도** (옥내) | 50/200/1000 lux | 시각 SLAM 동작, 카메라 게인 자동 |
| **온도** | -5°C / 35°C / 50°C | 배터리·LiPo 성능 ±10% |
| **고도** | 50m / 100m / 120m | RTK Fix 유지, 풍속 보정 |
| **EMI** | 2.4/5GHz Wi-Fi 혼잡 | 텔레메트리 손실률 <5% |

## 풍동 시험 (한국항공우주연구원 등 협력)

```bash
# 풍속 5/7/10/15 m/s 4단계
for v in 5 7 10 15; do
    python scripts/wind_tunnel_test.py --wind-speed $v --duration 180
done

# 자동 분석
python scripts/analyze_wind_response.py
# 출력:
#   APF_PARAMS_WINDY 전환 트리거 정확도
#   위치 오차 RMS (m)
#   배터리 소모 증가율 (%)
```

## 강우 시험 (인공 강우 장비 또는 자연)

```bash
# 인공 강우: 정원 스프링클러 5/10 mm/h
# 측정 항목:
#   - 모터 ESC 단락 0건
#   - 카메라 영상 노이즈 (FLIR 셔터 가동)
#   - RTK 안테나 cover 누수
#   - GPS HDOP 변화

python scripts/rain_test.py --intensity 10 --duration 600
```

## 저조도 시험

```bash
# 야간 또는 암실
# 측정:
#   - EO 카메라 게인 자동 조정 < 2초
#   - IR 카메라 표적 검출 능력
#   - DnI 정확도 (P735 모델)

python scripts/low_light_test.py --lux 50 --vessel-type small
```

## EMI / Wi-Fi 혼잡 시험

```bash
# iperf3 로 2.4/5GHz 채널 부하 80% 인가
# 측정:
#   - MAVLink 텔레메트리 손실률
#   - CSAC 시간 동기화 jitter
#   - RC 채널 끊김 빈도

python scripts/emi_stress_test.py --channel 6 --load 80
```

## 데이터 활용

각 시험 → CSV → 논문 §4.3 fig 5/6/7/8 생성.

```bash
# Aggregate
python scripts/aggregate_env_results.py docs/hardware/data/
# → docs/paper/figures/env_results.png
```

## 다음 단계
P699 → [P700 HITL FMEA 보고서](fmea_report.md)
