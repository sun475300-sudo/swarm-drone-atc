# 🎓 SDACS 대학 캡스톤 표준 커리큘럼 (Phase 468)

*ODYSSEY Track 🏛 Standards & Policy — Phase 468 산출물*
*GENESIS Phase 383 (15주 강의 슬라이드) 확장*
*Created: 2026-06-25 · 학부 4학년 1학기 캡스톤 표준 제안*
> **자매 산출물 (Phase 468 이중 트랙)**: 본 문서는 *제출용 산문 트랙*. 기계 검증 게이트 트랙은 [`CAPSTONE_CURRICULUM_STANDARD.md`](../standards/CAPSTONE_CURRICULUM_STANDARD.md) + `simulation/capstone_curriculum_standard.py` (결정적 준비도 판정·회귀 테스트 포함) — 두 트랙은 상보적이며 서로 대체하지 않는다.


> **목적**: SDACS 가 목포대 캡스톤(2026) 에서 실증한 200+ Phase 자산을 기반으로, **무인이동체·드론·UAS·UTM** 영역의 대학 학부 4학년 캡스톤 과목의 **표준 커리큘럼** 을 제안한다. 다른 대학(항공대·서울대 우주공학·KAIST 항공우주·인하대 항공우주·세종대 항공우주 등) 채택 가능 형태.

---

## 1. 과목 개요

| 항목 | 내용 |
|---|---|
| 과목명 | 드론 관제 시스템 캡스톤 설계 (Drone Air Traffic Control System Capstone Design) |
| 학점 | 3학점 (이론 1 + 실습 2) |
| 학기 | 4학년 1학기 (16주) — 또는 4학년 2학기 (15주) |
| 선수 과목 | C/Python 프로그래밍 · 자료구조 · 운영체제 · (권장: 항공역학 입문) |
| 평가 | 중간발표(20) + 기말발표(40) + 산출물(30) + 참여(10) |

---

## 2. 학습 목표 (Course Learning Outcomes)

수강 후 학생은:

1. **CLO-1**: 5계층 안전망 (APF·CBS·CPA·ATC·UTM) 의 정의와 우선순위를 설명할 수 있다.
2. **CLO-2**: 결정적 시뮬레이션 (numpy.random.default_rng) 기반 충돌 시나리오를 설계하고 측정할 수 있다.
3. **CLO-3**: SDACS-SBS-10 표준 시나리오 10종을 실행하고 conflict resolution rate 를 보고할 수 있다.
4. **CLO-4**: 항공안전법·KC 전파인증·EASA SORA 의 기본 요건을 SDACS 모듈에 매핑할 수 있다.
5. **CLO-5**: ASTM F38·ISO/TC 20/SC 16 의 핵심 표준을 인지하고 정합 가능성을 평가할 수 있다.
6. **CLO-6**: 팀(3-5인) 으로 신규 시나리오 또는 안전망 모듈을 설계·구현·발표할 수 있다.
7. **CLO-7**: Git/GitHub PR·CI/CD·코드 리뷰 워크플로를 준수할 수 있다.

---

## 3. 15주 커리큘럼

### Part I — 기초 (1-5주)

| 주차 | 주제 | 학습 활동 | 산출물 |
|:-:|---|---|---|
| 1 | 과목 개요 + SDACS 데모 | 시뮬레이터 라이브 데모 + GitHub 레포 클론 | 환경 설정 보고서 |
| 2 | 무인이동체 운용 개요 (항공안전법·KAIA 표준) | `docs/certification/AIR_SAFETY_ACT_MATRIX.md` 정독 | 법령 요약 |
| 3 | 결정적 시뮬레이션 (SimPy·numpy.random.default_rng) | `simulation/simulator.py` 코드 워크스루 | 시드 5종 시나리오 실행 |
| 4 | 5계층 안전망 — L1 APF (반응형) | `simulation/apf_engine/apf.py` 분석 + 파라미터 변경 실험 | APF 회피 영상 |
| 5 | 5계층 안전망 — L2 CBS (MAPF) | `src/airspace_control/planning/` CBS 알고리즘 분석 | CBS 경로 비교 보고 |

### Part II — 핵심 (6-10주)

| 주차 | 주제 | 학습 활동 | 산출물 |
|:-:|---|---|---|
| 6 | 5계층 안전망 — L3 CPA (90s lookahead) | `airspace_controller.py` advisory 6단계 분석 | CPA 시각화 |
| 7 | 5계층 안전망 — L4 ATC + L5 UTM | `_sdacs.atcCommand()` + Federation 9 모듈 데모 | ATC 명령 시퀀스 |
| 8 | **중간 발표** (팀 프로젝트 주제 확정) | 팀 5분 발표 + Q&A | 프로젝트 계획서 |
| 9 | 표준 시나리오 SDACS-SBS-10 | `simulation/standard_scenarios.py` 10종 실행 | 벤치마크 표 |
| 10 | 사고 조사 + ICAO Annex 13 | `simulation/incident_investigation_report.py` 사용 | 가상 사고 보고서 |

### Part III — 응용 (11-15주)

| 주차 | 주제 | 학습 활동 | 산출물 |
|:-:|---|---|---|
| 11 | 국제 표준 (ASTM F38 + ISO 23629) | `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` + ISO tracker 학습 | 표준 정합 매트릭스 |
| 12 | 인증 가능 ML (EASA AI Roadmap) | `docs/research/RL_GENERALIZATION_SURVEY.md` 정독 | RL 1A 시나리오 설계 |
| 13 | 팀 프로젝트 구현 (1) — 신규 시나리오 또는 모듈 | 팀 작업 + 코드 리뷰 | PR 초안 (Draft) |
| 14 | 팀 프로젝트 구현 (2) — CI 통합 + 회귀 | CI green + 4 사본 md5 + API 게이트 | PR Ready for Review |
| 15 | **기말 발표** + 종합 평가 | 팀 15분 발표 + 산출물 시연 + Q&A | 최종 보고서 + 데모 영상 |

---

## 4. 팀 프로젝트 주제 예시 (선택)

| # | 주제 | 난이도 | SDACS 정렬 |
|:-:|---|:-:|---|
| 1 | 신규 시나리오 1종 추가 (SDACS-SBS-10 확장 후보) | 🟢 | `simulation/standard_scenarios.py` |
| 2 | 신규 어드바이저리 1종 (현 6단계 → 7+) | 🟡 | `_classifyAdvisory()` |
| 3 | Voronoi 분할 알고리즘 대안 (Lloyd's 등) | 🟡 | `simulation/voronoi_airspace/` |
| 4 | 기상 모델 확장 (마이크로버스트 외) | 🟡 | (신규 모듈) |
| 5 | 신규 federation 모듈 (예: 다중 USS 부하 분산) | 🔴 | `simulation/federation_*.py` |
| 6 | 신규 시각화 (예: 2D 평면 분석 뷰) | 🟢 | `swarm_3d_simulator.html` |
| 7 | 신규 인증 매트릭스 (예: 일본 항공법) | 🟢 | `docs/certification/` |
| 8 | 신규 RL 시나리오 (Phase 451 §5 권고 단계) | 🔴 | `src/rl/` |

> 🟢 기본 (3-4주 작업) · 🟡 중급 (4-5주) · 🔴 고급 (5+주, 팀 5인 권장)

---

## 5. 평가 기준 (Rubric)

### 5.1 산출물 평가 (30점)

| 항목 | 만점 | 기준 |
|---|:-:|---|
| 코드 작성 (PR) | 10 | merge 가능 + CI green |
| 회귀 테스트 | 5 | 신규 케이스 ≥ 5건 + 모두 PASS |
| 문서 작성 | 5 | `docs/` 신규 1건 + ROADMAP 갱신 |
| 정직성 공시 | 5 | 한계 명시 + 거짓 양성 차단 흔적 |
| 4 사본 동기 | 5 | md5 일치 + API 정합성 게이트 |

### 5.2 중간 발표 (20점) + 기말 발표 (40점) + 참여 (10점) = 70점

총합 100점.

---

## 6. 다른 대학 채택 가이드

본 커리큘럼을 다른 대학에서 채택할 때:

1. **SDACS GitHub 레포 fork** (MIT License — 자유 사용)
2. **로컬화** (기관 명·평가 비율·선수과목 조정)
3. **지도교수** 1명 + **TA** 1명 (대학원생 권장) 권장
4. **장비** : 학생당 노트북 1대 (16GB RAM·SSD 권장, GPU 미필수 — 헤드리스 SwiftShader 가능)
5. **결과 보고**: 학기말 SDACS 레포에 PR 또는 issue 로 사례 보고 권장

**제약**: 실 비행 검증(Track A) 은 외부 환경 의존. 본 커리큘럼은 *시뮬레이션 + 표준 + 거버넌스* 영역만 다룸.

---

## 7. 한계 (정직성 공시)

- 본 커리큘럼은 *제안 초안* 이며 실제 채택은 각 대학 학사 위원회·전공 트랙 의존.
- 평가 비율은 예시 — 대학별 조정 가능.
- 실 비행·HITL 검증은 외부 환경 (사용자 HW) 필요.
- 영어 강의 자료는 후속 작업 (현재 한국어 우선, Phase 305 영문 확장 후속).

---

## 8. 참조

- `docs/SIMULATOR_GENESIS_PLAN.md` Track 🎓 — Phase 381-400 Education & Legacy
- `docs/standards/SDACS_BENCHMARK_SUITE.md` — Phase 465 SDACS-SBS-10 (Week 9)
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` — Phase 464 5계층 백서 (Week 4-7)
- `docs/research/RL_GENERALIZATION_SURVEY.md` — Phase 451 인증 가능 ML (Week 12)
- `docs/certification/AIR_SAFETY_ACT_MATRIX.md` — GENESIS 301 항공안전법 (Week 2)
- `docs/certification/PILOT_LICENSE_MAPPING.md` — Phase 309 조종자 자격
- `LICENSE` — MIT License (자유 사용)
