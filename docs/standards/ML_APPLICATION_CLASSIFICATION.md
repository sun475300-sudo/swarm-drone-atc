# SDACS ML 애플리케이션 분류 (EASA AI Level) — ODYSSEY Phase 452

> **자문 문서**입니다. SDACS 의 *운영(추론) 시점* 기계학습(ML) 구성요소를 EASA 가
> 제시한 AI Level(1A/1B/2A/2B/3A/3B) 분류 체계에 따라 **결정적으로** 분류합니다.
> 본 문서는 산문(rationale)의 유일 출처(SSoT)이고, 동반 모듈
> [`simulation/ml_application_classification.py`](../../simulation/ml_application_classification.py)
> 는 분류 *규칙* 과 *기계 검증* 을 보유합니다.

## 1. 동기 — Phase 451 이 남긴 갭의 해소

Phase 451([`EASA_AI_CONFORMANCE.md`](EASA_AI_CONFORMANCE.md))은 SDACS ML 의 EASA 신뢰
가능 AI 적합성을 평가하면서, **최대 갭**으로 다음을 명시했습니다:

> `ml_application_classification` — *EASA Level 1A/1B/2/3 분류 기록 없음 — 인증 경로 진입
> 전제 미충족 (갭)*

EASA Concept Paper 의 인증 경로는 *분류가 선행* 합니다. AI 애플리케이션의 Level 을 먼저
정해야 *어떤 러닝 어슈어런스 목표가 적용되는지* 가 결정됩니다. 본 Phase 452 는 그
**분류 자체를 결정적으로 기록**하여 451 이 지목한 전제 갭을 메웁니다.

### 451 과의 경계 (중복 0)

| | Phase 451 (`easa_ai_conformance`) | Phase 452 (본 모듈) |
|---|---|---|
| 질문 | ML 이 신뢰 가능 AI *목표를 얼마나 충족* 하는가 | 각 ML 구성요소가 *어느 Level 인가* |
| 산출 | 적합성 매트릭스 (conformant/partial/gap) | 분류 매트릭스 (1A…3B/N-A) |
| 인증 순서 | 분류 *이후* (적용 목표 평가) | 분류 — 적용 목표를 *결정* 하는 선행 단계 |

## 2. 근거 (권위 있는 출처)

- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). AI 애플리케이션을 *인간/시스템 대비 AI 의 자율 수준* 으로 분류:
  - **Level 1** — AI 보조: 인간/시스템이 결정·행위 (1A 인간 증강 · 1B 인지 보조)
  - **Level 2** — human-AI teaming: AI 가 행위, 감독자가 재정의 (2A 인간 감독 · 2B AI 감독)
  - **Level 3** — AI 가 결정 (3A 인간 폴백 동반 · 3B 폴백 없는 자율)
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — Level 이 오를수록 러닝
  어슈어런스 의무가 *단조 증가* 합니다. Level 1 이 가장 가벼운 의무 계층입니다.

## 3. 분류 모델 (결정적)

각 구성요소는 세 속성으로 *선언* 되고, `classify()` 가 그로부터 Level 을 **유일하게**
도출합니다(무작위성 0). 무관한 보조 축은 반드시 `None` 이어야 하며 `__post_init__` 가
강제합니다.

| 1차 축 `ai_role` | 2차 축 | → Level |
|---|---|---|
| `advisory` (정보/권고만, 결정권 비-ML) | `emits=information` | **1A** |
| `advisory` | `emits=recommendation` | **1B** |
| `supervised_actor` (AI 행위, 감독자 재정의) | `oversight_by=human` | **2A** |
| `supervised_actor` | `oversight_by=ai` | **2B** |
| `decider` (AI 최종 결정) | `human_fallback=True` | **3A** |
| `decider` | `human_fallback=False` | **3B** |
| `not_operational` (학습-시점, 운영 루프 밖) | — | **N/A** |

`POLICY_MATRIX` 의 7칸 전부가 `classify()` 와 정확히 일치함을 테스트가 강제합니다.

## 4. SDACS ML 구성요소 분류 결과

| 구성요소 | 역할 | Level | 구현 경로 |
|---|---|:-:|---|
| PPO 충돌 회피 정책 | advisory (recommendation) | **1B** | `src/rl/ppo_collision.py` |
| DQN 충돌 회피 컨트롤러 | advisory (recommendation) | **1B** | `simulation/deep_rl_controller.py` |
| 강화학습 경로 선택기 | advisory (recommendation) | **1B** | `simulation/rl_path_selector.py` |
| 다중 에이전트 RL 조정기 | advisory (recommendation) | **1B** | `simulation/marl_coordinator.py` |
| Isolation Forest 이상 탐지 | advisory (information) | **1A** | `simulation/anomaly_detector_isolation.py` |
| 도메인 무작위화 (Sim-to-Real) | not_operational | **N/A** | `src/training/domain_rand.py` |

- **운영 5 · 비운영 1**, 최고 운영 Level **1B** (어슈어런스 의무 강도 **2/6**).
- 인용된 모든 경로는 리포에 **실재**합니다(`test_cited_modules_exist_on_disk` 강제).

## 5. 정직 공시 (CLAUDE.md)

1. 본 문서는 *기능적 자가 분류* 이며 EASA 공식 분류 결정이 아닙니다. Level 정의는 SDACS
   해석이며 EASA 문서를 복제하지 않습니다.
2. **SDACS 의 모든 운영 ML 구성요소는 `advisory` 입니다.** 안전-결정권은 결정적
   APF+CBS 5계층 안전망([`simulation/emergency_protocol.py`](../../simulation/emergency_protocol.py))이
   보유하며, ML 은 절대 작동기에 직접 연결되지 않습니다(CLAUDE.md "검증 안 된 RL 모듈을
   규칙 기반 로직에 직접 연결 금지"). 따라서 분류 결과는 전부 **Level 1**(최저 의무 계층)에
   머뭅니다.
3. **이것은 결함이 아니라 아키텍처의 정직한 귀결입니다.** 연구 수준 ML 을 안전-크리티컬
   권한에서 배제함으로써 *인증 부담을 최소 계층에 유지* 합니다 — Level 1 ML 은 Level 2/3
   대비 러닝 어슈어런스 의무가 가볍습니다. SDACS 의 ML 이 미성숙해도 시스템 안전은
   비-ML 결정적 안전망이 보장하므로, 이 분류는 안전 주장이 아니라 *책임 구조* 의 선언입니다.
4. 학습-시점 자산(도메인 무작위화)은 `not_operational` 로 명시 분류해 *범위 경계* 를
   기계 검증합니다 — 운영 구성요소가 아니므로 Level 집계에서 제외(N/A)됩니다.

## 6. CLI

```bash
python simulation/ml_application_classification.py --constituents  # 구성요소+분류
python simulation/ml_application_classification.py --report        # 분류 요약
python simulation/ml_application_classification.py --levels        # Level 체계·의무
python simulation/ml_application_classification.py --matrix        # 분류 규칙 매트릭스
python simulation/ml_application_classification.py --manifest       # JSON 매니페스트
```

## 7. 검증

`tests/test_ml_application_classification.py` — dataclass 축 결속 불변식·결정적 분류·
정직성(인용 경로 디스크 실재) 강제·`ClassificationReport` 카운트/Level키/읽기전용 불변식·
`POLICY_MATRIX` 와 `classify` 정확 일치·매트릭스 완전성·매니페스트 직렬화·CLI 5종으로
**46건 PASS**. 대상 기존 `.py` 무수정 순수 추가 → 회귀 무영향. code-reviewer 어드바이저
MEDIUM 2 반영(매트릭스 7개 잎 경로 완전성 게이트·`by_level` 0 카운트 항목 거부).
