# 🔬 RL 일반화 + 인증 가능 ML 조사 (Phase 451)

*ODYSSEY Track 🔬 Formal & Research Frontier — Phase 451 산출물*
*Created: 2026-06-24*

## 1. 목적 + 범위

본 문서는 SDACS 의 **RL 일반화 (RL Generalization)** + **인증 가능 ML (Certifiable ML, EASA AI Roadmap)** 두 축을 학술·표준 문헌 기반으로 조사한다. 본 PR 의 자매 phase #430·#433 (Phase 452·453) 와 분리된 *연구 조사 baseline* 으로, 신규 코드를 추가하지 않는 **순수 문헌 정리** 다.

**정직성**: 본 문서는 외부 출처를 인용한 정리이며 SDACS 가 제안하는 새로운 알고리즘이 아니다. 출처는 모두 공개 학술/표준 문서이고 직접 참조 가능한 형태로 명시한다.

---

## 2. RL 일반화 — 핵심 문제 정의

### 2.1 분포 일반화 (Distributional Shift)

**문제**: 학습 시나리오와 다른 운용 환경에서 RL 정책이 silent failure.

| 분포 변화 유형 | SDACS 시뮬 컨텍스트 | 예시 |
|---|---|---|
| **Covariate shift** | 드론 수 학습 50 → 평가 500 | 군집 밀도 변화 |
| **Concept shift** | 학습 시 NFZ 정적 → 평가 시 동적 | NFZ 변경 (Phase 425 NOTAM) |
| **Domain shift** | 학습 환경 → 실 비행 | sim-to-real gap (`src/training/sim_real_gap.py`) |
| **Adversarial shift** | 학습 시 정상 → 평가 시 적대적 | GPS jamming, hijacking (Phase 447 퍼저) |

### 2.2 평가 프로토콜 핵심 (학술 합의)

| 프로토콜 | 출처 | SDACS 정렬 |
|---|---|---|
| **Train-test split (random seeds)** | Henderson et al. 2018 (Deep RL that Matters) | 시드 분리 (학습 1-1000, 평가 1001-2000) |
| **In-distribution + OOD evaluation** | OpenAI 2019 (Quantifying Generalization in RL) | Phase 447 fuzzer 변이 시나리오 |
| **Multi-seed average + 95% CI** | Henderson et al. 2018 | Monte Carlo (`config/monte_carlo.yaml`) |
| **Per-scenario breakdown** | Cobbe et al. 2020 (Leveraging Procedural Generation) | Phase 465 표준 시나리오 10종 분해 |

### 2.3 대표 벤치마크

| 벤치마크 | 도메인 | SDACS 정렬 가능성 |
|---|---|---|
| **Procgen** (Cobbe et al. 2020) | 2D 게임 procedural | (간접) |
| **CARL** (Benjamins et al. 2023) | Continuous control | 가능 (드론 dynamics) |
| **MetaWorld** (Yu et al. 2019) | Manipulation | (간접) |
| **NetHack** (Küttler et al. 2020) | Long-horizon | (간접) |
| **SDACS-SBS-10** (Phase 465) | 군집 ATC | **본 프로젝트** |

---

## 3. 인증 가능 ML — EASA AI Roadmap

### 3.1 EASA AI Roadmap 2.0 (2023)

EASA 가 항공 시스템의 ML/AI 인증을 단계별로 명세:

| 레벨 | 명칭 | 자율성 | 검증 요건 |
|:-:|---|:-:|---|
| **AI/ML 1A** | Decision support (학습 후 고정) | 0% | Traceable + Explainable |
| **AI/ML 1B** | Decision support (online learning) | 0% | + Online monitoring |
| **AI/ML 2A** | Human + AI/ML cooperation | 부분 | + HMI + override |
| **AI/ML 2B** | Human supervised AI/ML | 부분 | + Override SLA |
| **AI/ML 3A** | Autonomous (탐지·회피 한정) | 높음 | + Formal verification |
| **AI/ML 3B** | Fully autonomous | 100% | (미정의, 미래) |

### 3.2 EASA AI Concept Paper (2024) 의 핵심 요건

1. **Data Quality** — 학습 데이터의 대표성·균형·청결 (CRISP-ML(Q))
2. **Learning Process Assurance** — 학습 절차의 결정성·재현성 (시드·소프트 버전 고정)
3. **Model Implementation** — 모델 → 코드 변환의 정확성 (DO-178C 호환)
4. **Inference / Runtime Monitoring** — OOD 탐지·confidence threshold
5. **Adversarial Robustness** — 입력 변조에 대한 강건성

### 3.3 SDACS 정렬 자산

| EASA 요건 | SDACS 정렬 모듈 |
|---|---|
| Data Quality | Phase 466 `simulation/telemetry_validator.py` JSON Schema 검증 |
| Learning Process | `np.random.default_rng(seed)` 결정성 (CLAUDE.md §11) |
| Model Implementation | (현재 RL 미사용 — `src/rl/ppo_collision.py` 는 PoC) |
| Inference Monitoring | TRANSCENDENCE Phase 203 Mock Detector (mock 호출 시 console.warn) |
| Adversarial Robustness | Phase 447 `simulation/scenario_fuzzer.py` Hypothesis 퍼저 |

---

## 4. 인증 가능 ML — 추가 표준

### 4.1 RTCA DO-178C (Software Considerations in Airborne Systems)

전통적 항공 SW 의 결정적 인증 표준. 학습 기반 시스템에는 **불충분** 하므로 보강 표준 사용:

- **DO-330** (Tool Qualification) — 학습/평가 도구 자체의 검증
- **DO-331** (Model-Based Development) — 모델 SDLC
- **DO-332** (Object-Oriented Technology)
- **DO-333** (Formal Methods) — TLA+/Coq (SDACS Phase 441 정렬)

### 4.2 ISO/IEC 22989 (AI Concepts and Terminology)

용어 표준 — 본 백서·SDACS 문서의 용어 사용 준수.

### 4.3 ISO/IEC 23053 (AI Framework for ML)

ML 시스템 프레임워크 — 데이터·모델·평가 분리.

### 4.4 ISO/IEC 5469 (AI Trustworthiness Functional Safety)

AI 시스템의 functional safety 통합.

### 4.5 EUROCAE ED-324 (Functional Safety of AI/ML in Aerospace)

DO-178C 보완 — AI/ML 특화 안전 요건.

---

## 5. SDACS 권고 연구 방향 (학술·표준 합의 기반)

본 권고는 SDACS 가 RL 통합을 진행할 경우의 *학술 합의 정렬* 방향이며, 구체 구현은 별도 phase (#430·#433 phase 452·453) 에서 진행된다.

### 5.1 단기 (~2027)

1. **결정적 평가 프로토콜 채택**: SDACS-SBS-10 (Phase 465) 위에서 multi-seed evaluation
2. **OOD 탐지 회귀**: Phase 447 fuzzer 결과를 OOD 지표로 사용
3. **Mock Detector 활용**: production/beta API 만 학습 데이터 source 로 인정

### 5.2 중기 (2027-2029)

1. **AI/ML 1A 레벨 시범**: APF 파라미터 튜닝을 RL 로 (다른 계층 불변)
2. **CRISP-ML(Q) 데이터 거버넌스**: telemetry_validator + audit_log (Phase 429)
3. **Adversarial robustness baseline**: Phase 447 fuzzer + Hypothesis 통합

### 5.3 장기 (2029+)

1. **AI/ML 2A**: APF + CBS hybrid RL (L2·L1 통합, L3·L4·L5 불변)
2. **DO-333 formal methods**: TLA+ 명세를 RL 정책 검증에 확장
3. **EASA AI Concept Paper 2025+** 반영

---

## 6. 한계 (정직성 공시)

본 조사가 다루지 않는 것:
- **AGI**: Phase 91 (Stellar) 의 AGI 시드는 *speculative* — 본 조사 범위 외
- **실 비행 RL**: Track A HW 의존, 사용자 환경
- **메타 학습**: 별도 연구 트랙
- **다중 에이전트 RL (MARL)**: Phase 453 (draft #433) 가 처리

본 문서는 ✅ *연구 조사* — 알고리즘 제안·구현 검증·논문 발표 아님.

---

## 7. 참조

### 7.1 SDACS 정렬 모듈

- `src/rl/ppo_collision.py` (Phase 736) RL PoC — PPO + SDACSGymEnv
- `src/training/sim_real_gap.py` Sim-to-Real gap 측정
- `simulation/scenario_fuzzer.py` (Phase 447) 퍼저
- `simulation/standard_scenarios.py` (Phase 465) SDACS-SBS-10
- `simulation/telemetry_validator.py` (Phase 466)

### 7.2 학술 출처 (대표)

- Henderson, P. et al. (2018). "Deep Reinforcement Learning that Matters." AAAI.
- Cobbe, K. et al. (2019). "Quantifying Generalization in Reinforcement Learning." ICML.
- Cobbe, K. et al. (2020). "Leveraging Procedural Generation to Benchmark Reinforcement Learning." ICML.
- Benjamins, C. et al. (2023). "CARL: A Benchmark for Contextual and Adaptive Reinforcement Learning." TMLR.
- Yu, T. et al. (2019). "Meta-World: A Benchmark and Evaluation for Multi-Task and Meta Reinforcement Learning." CoRL.

### 7.3 표준 출처

- EASA AI Roadmap 2.0 (2023): <https://www.easa.europa.eu/ai-roadmap>
- EASA AI Concept Paper (2024): <https://www.easa.europa.eu/ai-concept-paper>
- RTCA DO-178C / DO-330 / DO-331 / DO-332 / DO-333
- ISO/IEC 22989, 23053, 5469
- EUROCAE ED-324

### 7.4 자매 문서

- `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` — Phase 461
- `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md` — Phase 462
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` — Phase 464
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🔬 — Phase 451-460
