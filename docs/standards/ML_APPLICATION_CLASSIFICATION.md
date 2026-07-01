# ML 애플리케이션 EASA Level 분류 게이트 — ODYSSEY Phase 454

SDACS 의 *학습 기반(ML)* 구성요소가 EASA 신뢰 가능 AI 프레임워크의 **분류(Level
1/2/3)** 축에서 어디에 놓이는가를 결정적으로 판정한 기준 문서입니다. 정본 데이터·정책은
`simulation/ml_application_classification.py` 가 보유하며, 본 문서는 그 요약과 활용
맥락을 제공합니다. ODYSSEY Track 🔬 Formal & Research Frontier(451-460)에서 Phase
451(`easa_ai_conformance`)이 가장 큰 갭으로 지목한 `ml_application_classification`
— "EASA Level 1A/1B/2/3 분류 기록 없음, 인증 경로 진입 전제 미충족" — 을 정면으로
채웁니다.

> **정직 공시**: 본 분류는 *기능적 자가 분류* 이며 EASA 공식 분류 인증이 아닙니다.
> `POLICY_MATRIX` 는 Concept Paper 의 Level 정의를 *기계 검증 가능* 한 두 축(과업 배분
> × 권한 보유)으로 환원한 것으로 원문의 모든 세부 판정 기준을 복제하지 않습니다.

## 근거 (권위 있는 출처)

- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024) — AI Level 분류(1/2/3, A/B 하위 등급)의 정의.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — Level 별 러닝 어슈어런스
  부담의 차등.

## 분류 정책 (과업 배분 × 권한 보유 → Level)

Level 의 **가족(1/2/3)** 은 *과업 배분*(AI 가 보조하는가·협업하는가·대체하는가)이,
**하위 문자(A/B)** 는 *인간/비-AI 권한 보유 정도* 가 가릅니다.

| 과업 배분 \ 권한 보유 | retained | reduced | none |
|---|:-:|:-:|:-:|
| **assistance** (Level 1) | 1A | 1B | 1B |
| **cooperation** (Level 2) | 2A | 2B | 2B |
| **automation** (Level 3) | 3A | 3A | 3B |

- **Level 1 (assistance)** — AI 가 비-AI 결정자를 *보조*. 결정 권한은 비-AI 보유.
- **Level 2 (cooperation)** — 인간-AI *협업*. AI 가 결정에 능동 참여하되 인간 감독.
- **Level 3 (automation)** — AI 가 결정을 *수행*. 3A 인간 재정의 가능 · 3B 완전 자율.

## 정직성 결속 — 권한에는 권한자가 필요

`human_authority` 가 `none` 이 아니면 반드시 그 권한을 *실제로 보유한 비-AI 모듈* 을
`override_authority` 로 인용해야 하며(없으면 `ValueError`), `none` 이면 인용을
금지합니다. "감독이 유지된다" 는 주장은 감독 주체를 명시할 때만 인정합니다 — 권한자
없는 안전 주장을 구조적으로 차단합니다. 인용한 ML 모듈·권한자 모듈은 테스트가 디스크
실재를 강제합니다(허위 분류 차단).

## SDACS ML 자산 분류 결과

| 자산 | 모듈 | 권한자(비-AI) | Level |
|---|---|---|:-:|
| PPO 강화학습 충돌 회피 | `src/rl/ppo_collision.py` | `simulation/path_deconflict.py` | **1A** |
| 하이브리드 APF+RL 회피 | `src/autonomy/hybrid_collision_avoidance.py` | `src/airspace_control/controller/airspace_controller.py` | **1A** |
| 도메인 무작위화 학습 정책 | `src/training/domain_rand.py` | `simulation/emergency_protocol.py` | **1A** |
| 시뮬-실측 갭 보정 | `src/training/sim_real_gap.py` | `simulation/compliance_checker.py` | **1A** |

## 핵심 발견 (정직)

SDACS 의 **모든 ML 자산은 Level 1A** 입니다 — 인증 부담이 가장 낮은 등급입니다. ML
출력은 항상 *자문* 이고 안전-결정권은 결정적 APF+CBS 5계층 안전망이 보유하기
때문입니다. 낮은 Level 은 결함이 아니라 *설계 선택의 보상* 입니다: "ML 을 안전-크리티컬
결정에 신뢰하지 않음" 으로써 Level 2/3 의 러닝 어슈어런스 전체 부담을 회피합니다.
**낮은 Level 이 곧 낮은 인증 리스크입니다.**

## 사용

```bash
python simulation/ml_application_classification.py --report       # 분류 요약
python simulation/ml_application_classification.py --matrix       # 자산별 매트릭스
python simulation/ml_application_classification.py --policy       # 정책 매트릭스
python simulation/ml_application_classification.py --levels       # Level 정의표
python simulation/ml_application_classification.py --constituent ppo_collision_avoidance
```

## 자매 모듈 경계

- Phase 451 `easa_ai_conformance` — *무엇이 빠졌는가*(빌딩 블록 적합성 매트릭스).
- 본 모듈(454) — *각 ML 자산이 어느 Level 인가*(인증 경로 진입의 첫 관문).
- (미머지 draft #435) Phase 452 `rl_generalization_protocol`·453 `rl_advisory_boundary`
  — RL 일반화 검증·자문 경계 정합성. 본 모듈과 **서로 다른 갭**을 다룹니다.
