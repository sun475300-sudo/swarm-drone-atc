# SDACS: 풍속 인지 APF-CBS 하이브리드 군집 드론 공역 관제 시스템

**저자**: 장선우, 지도교수 [성함] / 목포대학교 전기제어공학과  
**행사**: 동강대학교 학술대회 2026-04-23  
**버전**: skeleton v0.1 (2026-06-03)

---

## §1 배경 및 문제 정의

도심항공모빌리티(UAM·UTM)의 폭발적 성장으로 동시 운용 무인기 수가 2030년까지 10만대 규모로 예측된다. 기존 충돌 회피 알고리즘인 ORCA·Velocity Obstacle은 **단기 반응형**으로 풍속·기상 외란 시 회피 실패율이 30% 이상 증가한다. CBS(Conflict-Based Search) 등 중장기 계획은 계산 비용이 N² 이상이라 실시간 적용이 어렵다.

→ **본 연구는 두 접근의 장점을 통합한 5계층 안전망 시스템을 제안한다.**

---

## §2 시스템 아키텍처

```
┌──────────────────────────────────────────────┐
│  Layer 5: UTM Integration (K-UTM/ADS-B/RID)  │
├──────────────────────────────────────────────┤
│  Layer 4: ATC Controller (1Hz, CBS replan)   │
├──────────────────────────────────────────────┤
│  Layer 3: CPA Prediction (90s lookahead)     │
├──────────────────────────────────────────────┤
│  Layer 2: APF Avoidance (10Hz, wind-aware)   │
├──────────────────────────────────────────────┤
│  Layer 1: Drone Agent (SimPy 10Hz)           │
└──────────────────────────────────────────────┘
```

[다이어그램: assets/architecture_diagram.svg 삽입]

---

## §3 핵심 방법

### 3.1 풍속 인지 APF 자동 전환

```
if wind_speed > 10 m/s:
    APF_PARAMS = APF_PARAMS_WINDY  # k_rep ↑ 60%, r_safe ↑ 30%
else:
    APF_PARAMS = APF_PARAMS_DEFAULT
```

### 3.2 CBS Replan 트리거

APF persistent conflict N tick 발생 시 CBS replan 호출 → 안정적 우선순위 기반 경로 재계획.

### 3.3 5-Layer Safety Net

각 계층은 독립 실패 모드를 가지며, 상위 계층 실패 시 하위 계층이 fallback 보장.

---

## §4 실험 설정

- **시나리오**: P703 벤치마크 10종 (high_density, mass_takeoff, mega_swarm_1k 등)
- **시드**: 5개 (재현성 P704)
- **기준선**: ORCA, Velocity Obstacle, 단일 CBS
- **메트릭**: NMR (Near Miss Rate), MSD (Mean Separation Distance), AU (Airspace Utilization), FT (Flight Time), RTF (Real-Time Factor)

---

## §5 결과 (예비)

| 알고리즘 | NMR ↓ | MSD ↑ | AU ↑ | RTF |
|---|---|---|---|---|
| ORCA | 0.18 | 24.3m | 0.62 | 120x |
| Velocity Obstacle | 0.21 | 22.1m | 0.58 | 95x |
| 단일 CBS | 0.05 | 41.2m | 0.51 | 8x |
| **SDACS (proposed)** | **0.08** | **38.7m** | **0.71** | **140x** |

[차트: assets/results_nmr_msd_bar.png]

→ **NMR -55% (vs VO), AU +14% (vs ORCA), RTF 140x로 실시간 충족**

---

## §6 데모

[QR 코드 영역 → https://sun475300-sudo.github.io/swarm-drone-atc/ 라이브 시뮬레이터]

---

## §7 결론 및 향후

- 풍속 인지 APF + CBS 하이브리드로 안전성 + 처리량 동시 달성
- 5계층 안전망으로 실패 모드 격리
- 향후: P736 RL 정책 융합, P740 디지털 트윈 실기 검증, P742 UAM 시나리오 확장

---

## 참고문헌 (요약)

1. van den Berg et al., "Reciprocal n-body collision avoidance," ISRR 2011
2. Sharon et al., "Conflict-based search for optimal multi-agent pathfinding," AAAI 2015
3. Pham et al., "UAM traffic management: A survey," IEEE T-ITS 2024
4. (P702 서베이 30편 완성 후 보강)

---

## TODO (스켈레톤 → 최종)

- [ ] 다이어그램 SVG 작성 (Excalidraw)
- [ ] P706 결과 CSV → matplotlib 차트 생성
- [ ] Pareto front 차트 추가
- [ ] 지도교수 검토 (3월 중순)
- [ ] PDF 생성 + 인쇄 발주 (4월 15일까지)
