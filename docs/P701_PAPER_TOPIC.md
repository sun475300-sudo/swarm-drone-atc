# P701 — 논문 주제 확정 및 기여 포인트

> 작성: 2026-05-31  
> 목표 투고처: IROS 2026 (IEEE/RSJ Intl Conf on Intelligent Robots and Systems) 또는 AIAA SciTech 2027

---

## 1. 논문 제목 (안)

**한국어**: 도심 항공 모빌리티 환경에서의 CBS-APF 하이브리드 프레임워크 기반 실시간 군집 드론 공역 충돌 해결

**영어 (투고용)**:  
*"A Hybrid CBS-APF Framework for Real-Time Swarm Drone Airspace Conflict Resolution in Urban UTM Environments"*

---

## 2. 연구 배경 및 문제 정의

### 2.1 문제
도심 저고도 공역(UTM, UAS Traffic Management)에서 다수 드론이 동시 비행할 때 발생하는 충돌 위험은 기존 단일 알고리즘으로는 해결하기 어렵다.

- **CBS (Conflict-Based Search)**: 최적 다중 에이전트 경로 계획이 가능하나 계산 복잡도 O(b^d), 실시간성 미흡
- **ORCA/VO (Velocity Obstacles)**: 반응형으로 빠르나, 밀집 환경에서 교착(deadlock) 및 진동(oscillation) 발생
- **APF (Artificial Potential Fields)**: 즉각 반응형이지만 국소 최솟값(local minimum) 함정 문제

### 2.2 제안 접근법
CBS의 **전역 계획** + APF의 **반응형 회피**를 계층 구조로 결합:
- CPA(Closest Point of Approach) 기반 90초 선제 예측 → CBS로 경로 재계획
- 예측 범위 밖의 긴급 회피 → APF(풍속 적응형 파라미터 자동 전환)
- Voronoi 동적 공역 분할로 계산 부하 O(N²) → O(N log N) 감소

---

## 3. 기여 포인트 3개 (Contribution Claims)

### C1 — 계층형 CBS-APF 하이브리드 충돌 해결 프레임워크

**기여 내용**:
- CPA 선제 예측 계층 (90초 룩어헤드) + CBS 경로 재계획 계층 + APF 즉각 회피 계층의 3계층 구조
- 풍속 임계값(>10 m/s)에 따른 APF 파라미터 자동 전환 (APF_PARAMS_WINDY)
- 9개 표준 시나리오에서 기준선(ORCA, VO, 단일 CBS) 대비 충돌 해결률 비교

**검증 방법**: SimPy 이산 이벤트 시뮬레이션, Monte Carlo 30 seeds × 10 시나리오

**기대 결과**: ORCA 대비 NMR(Near-Miss Rate) 40%↓, AU(Airspace Utilization) 15%↑

---

### C2 — Voronoi 기반 동적 공역 분할을 통한 확장 가능한 충돌 스캔

**기여 내용**:
- 기존 브루트포스 충돌 스캔 O(N²) → KD-Tree + Voronoi 분할 O(N log N) 실현
- 드론 밀도에 따른 동적 셀 재분할 (Adaptive Voronoi Partitioning)
- 100기 이상 스웜에서 실시간(1Hz ATC 루프) 유지 검증

**검증 방법**: 드론 수(N=10~100) 스케일링 벤치마크, CPU 시간 vs N 그래프

**기대 결과**: N=100에서 O(N²) 대비 8.7× 속도 향상 (기존 벤치마크 수치)

---

### C3 — 공개 벤치마크 데이터셋 및 재현 가능한 평가 프레임워크

**기여 내용**:
- 10개 표준 시나리오 벤치마크 (`benchmarks/scenarios/`) CC-BY-4.0 공개
- 8종 공식 평가 메트릭 정의: NMR, MSD, PE, MS, FT, AU, RID_CR, RTF
- Dockerfile 기반 완전 재현 환경 (PYTHONHASHSEED=0, 난수 시드 고정)
- 3개 기준선(ORCA, VO, CBS) 어댑터 포함

**검증 방법**: GitHub Actions 재현성 검증 워크플로우 통과

**기대 효과**: 커뮤니티 공통 평가 기준 제공, 후속 연구 비교 기반 마련

---

## 4. 투고 전략

| 항목 | 내용 |
|------|------|
| **1순위 투고처** | IROS 2026 (IEEE/RSJ) — 제출 마감 3월, 로보틱스 최고 학회 |
| **2순위 투고처** | AIAA SciTech 2027 — UAM/UTM 전문 트랙 |
| **국내 발표** | 한국항공우주학회 추계학술대회 (11월) |
| **프리프린트** | arXiv cs.RO 섹션 (IROS 제출 동시) |
| **페이지 수** | IROS: 8 페이지 (IEEE 2열 형식) |

---

## 5. 선행 연구와의 차별점

| 방법 | 최적성 | 반응성 | 확장성 | 본 연구 대비 |
|------|--------|--------|--------|------------|
| CBS (Sharon+15) | ✅ | ❌ | ❌ | 본 연구는 APF 반응층 추가 |
| ORCA (Van den Berg+11) | ❌ | ✅ | ✅ | 본 연구는 글로벌 최적 경로 추가 |
| APF (Khatib+86) | ❌ | ✅ | ✅ | 본 연구는 국소최솟값 탈출 CBS로 해결 |
| **CBS-APF (본 연구)** | 준최적 | ✅ | ✅ | 3계층 통합 + 동적 Voronoi |

---

## 6. 일정 (잠정)

| 마일스톤 | 목표일 |
|---------|--------|
| P702 선행 연구 서베이 완료 | 2026-06-07 |
| P706 비교 실험 데이터 확정 | 2026-06-14 |
| P707 논문 초안 (IROS 형식) | 2026-07-15 |
| P708 지도교수 1차 리뷰 | 2026-08-01 |
| P709 IROS 2026 제출 | 2026-09-01 (마감 확인 필요) |
| P710 발표 슬라이드 완성 | 2026-10-01 |

---

*작성자: SDACS 팀 (장선우) — 목포대학교 캡스톤 디자인*
