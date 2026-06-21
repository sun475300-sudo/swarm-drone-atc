# 대학 캡스톤 표준 커리큘럼 제안 — 군집 드론 공역 통제 시스템 설계

> **ODYSSEY Phase 468** · Standards & Policy 트랙(461-480)
> 적합성 게이트: [`simulation/capstone_curriculum_standard.py`](../../simulation/capstone_curriculum_standard.py)
> 강의 슬라이드 산출물(GENESIS Phase 383): [`docs/slides_deck.md`](../slides_deck.md)

## 0. 목적과 범위

본 문서는 SDACS(Swarm Drone Airspace Control System)를 *워크드 예제(worked
example)* 로 삼는 **학부 15주 캡스톤 디자인 표준 커리큘럼** 제안서다. GENESIS
Phase 383 이 강의 슬라이드 *산출물 자체* 를 제공한다면, 본 표준은 그 자료를
포함한 리포 교육 자산을 *재사용 가능한 표준 교과* 로 묶어 타 대학·교과 운영자가
도입할 수 있는 형식으로 제안한다.

**정직 공시:**
- 본 커리큘럼은 *제안* 이며 한국공학교육인증원(ABEEK)의 심사·인정을 보장하지
  않는다. 학습성과(PO) 매핑은 제안자의 자체 판단이다.
- 표준 *제안 준비 완료* 와 *외부 채택* 은 독립이다. 현 상태는 항상
  `NOT_PROPOSED`(외부 대학·인증원 미제안)로 공시한다.

## 1. 학습성과 매핑 (ABEEK KEC2015 프로그램 학습성과)

| 코드 | 학습성과 | 필수 |
|---|---|:-:|
| PO1 | 수학·기초과학·공학 지식의 응용 | ★ |
| PO2 | 자료의 분석·해석 및 실험 설계·수행 | ★ |
| PO4 | 공학 문제의 인식·정식화 및 창의적 해결 | ★ |
| PO5 | 공학 실무에 필요한 기술·도구·정보기술 활용 | ★ |
| PO6 | 보건·안전·경제·환경·지속가능성 영향 이해 | ★ |
| PO7 | 효과적 의사소통·발표 능력 | |
| PO9 | 팀 구성원으로서 협동 능력 | |
| PO10 | 공학적 해결책의 사회적 영향 이해 | |
| PO12 | 기술 변화 대응 자기주도·평생학습 | |

필수(★) 5개 학습성과는 표준 제안 준비 완료(`READY_FOR_PROPOSAL`) 판정의
**교차 불변식** 이다 — 모든 단원이 작성돼도 필수 학습성과 하나가 어느 단원에도
매핑되지 않으면 준비 미완으로 판정한다.

## 2. 15주 단원 구성

| 단원 | 주차 | 제목 | 학습성과 | 워크드 예제 |
|---|---|---|---|---|
| U01 | W01-02 | 공역 통제 문제 정의·시스템 개요 | PO1·PO4·PO10 | 4계층 아키텍처 |
| U02 | W03-04 | 이산 사건 시뮬레이션·드론 에이전트 | PO1·PO5 | SimPy 10Hz/1Hz |
| U03 | W05-06 | 충돌 회피 알고리즘(APF·CBS) | PO1·PO4 | 수렴·완전성 증명 |
| U04 | W07 | 5계층 안전망·형식 명세 | PO1·PO6 | TLA+ 안전망 |
| U05 | W08 | 중간 설계 검토·발표 | PO7·PO9 | DEFENSE_KIT |
| U06 | W09-10 | 실험 설계: 시나리오·MC·KPI | PO2·PO5 | 표준 시나리오 |
| U07 | W11 | Sim-to-Real: 하드웨어 인 더 루프 | PO5·PO12 | Pixhawk HITL |
| U08 | W12 | 재현성·연구 윤리 | PO6·PO12 | 의존성 핀 재현 |
| U09 | W13 | 논문 작성·학술 기여 *(개요)* | PO2·PO7 | IROS outline |
| U10 | W14-15 | 최종 발표·산학·사업화 | PO7·PO10 | Track F 산학 |

> **U09 는 개요(OUTLINED) 단계** — IROS 형식 논문 outline 은 있으나 실측 그래프
> 보강이 필요하다(기존 잔여 항목 P707 §4-§7 과 동일 의존). 이로 인해 현 표준
> 준비도는 `PARTIAL` 로 정직 공시된다.

## 3. 평가 방법

각 단원은 강의 자산(슬라이드·가이드·증명 문서)을 **워크드 예제** 로 사용하며,
평가는 (1) 단원별 실습 산출물과 (2) 캡스톤 최종 산출물(시뮬레이터·논문·발표)로
구성한다. 표준 시나리오 셋(Phase 465 `SDACS-SBS-10`)과 충돌 해결률 KPI 가
정량 평가 기준선을 제공한다.

## 4. 적합성 게이트 사용

```bash
python simulation/capstone_curriculum_standard.py --report     # 준비도·채택 상태
python simulation/capstone_curriculum_standard.py --coverage   # 학습성과 커버리지
python simulation/capstone_curriculum_standard.py --gaps       # 미완 단원·미커버
python simulation/capstone_curriculum_standard.py --matrix     # 주차별 단원 매트릭스
```

게이트는 (1) 각 DRAFTED 단원의 인용 강의 자산이 디스크에 실재하는지, (2) 필수
학습성과가 *증거 실재 DRAFTED 단원* 에 의해 커버되는지를 결정적으로 검증한다.
작성 주장만으로는 자료 완비로 인정하지 않는다(거짓 커버 금지).

## 5. 채택 경로 (외부 절차 의존)

`NOT_PROPOSED → PROPOSED → PILOTED → ADOPTED`. 현 단계는 `NOT_PROPOSED`.
타 대학 공학교육혁신센터·ABEEK 워킹그룹 제안은 본 리포 범위 밖이며, 준비도
판정과 독립적으로 공시된다.
