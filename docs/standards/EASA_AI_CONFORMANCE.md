# EASA 신뢰 가능 AI(Learning Assurance) 적합성 자가 평가 — ODYSSEY Phase 451

SDACS 의 *학습 기반(ML)* 구성요소가 EASA 가 제시한 신뢰 가능 AI 프레임워크의 목표를
어디까지 충족하는가를 **동일한 빌딩 블록 축** 으로 정렬해 평가한 기준 문서입니다.
정본 데이터는 `simulation/easa_ai_conformance.py` 가 보유하며, 본 문서는 그 요약과
활용 맥락을 제공합니다. ODYSSEY Track 🔬 Formal & Research Frontier(451-460,
"RL 일반화 연구 + 인증 가능 ML 조사")의 착수 산출물입니다.

> **정직 공시**: 본 평가는 *기능적 자가 평가* 이며 EASA 공식 적합성 인증이 아닙니다.
> SDACS 의 ML 은 **연구 수준** 이므로 본 평가는 의도적으로 보수적입니다 — 가중 점수가
> 낮은 것이 곧 정직함입니다. 안전은 ML 이 아니라 결정적 APF+CBS 5계층 안전망이
> 보장하며, 이 점이 본 매트릭스에서 유일하게 충족(`conformant`)인 항목들의 근거입니다.

## 근거 (권위 있는 출처)

- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024) — 신뢰 가능 AI 빌딩 블록(6종)을 분류 축으로 사용.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — Learning Assurance 의
  W-shaped 단계(데이터 관리·학습 프로세스 관리·모델 훈련·학습 프로세스 검증·모델 구현·
  추론 모델 검증)를 러닝 어슈어런스 목표 세분화에 차용.

## 빌딩 블록 (6종)

| 블록 id | 라벨 |
|---|---|
| `trustworthiness_analysis` | AI 특성화·Level 분류·ODD |
| `learning_assurance` | W-shaped 데이터·학습·검증 |
| `explainability` | AI 설명가능성 |
| `human_factors` | 인적 요소·human-AI teaming |
| `safety_risk_mitigation` | AI 안전 위험 완화 |
| `ethics_assessment` | 윤리 기반 평가 |

## 적합성 상태 (3값)

- `conformant` (가중 1.0) — 완전 충족, 실재 모듈 근거 필수
- `partial` (가중 0.5) — 부분 충족, 실재 모듈 근거 필수
- `gap` (가중 0.0) — 미충족, **근거 모듈 없음(None)**

`gap` ⟺ `sdacs_module is None` 정직성 결속을 dataclass `__post_init__` 가 강제하며,
인용한 모든 경로의 디스크 실재를 테스트(`test_cited_modules_exist_on_disk`)가 강제합니다.

## 현 리포 판정 (스냅샷)

| 지표 | 값 |
|---|---|
| 가중 점수 | **33%** (충족 2 · 부분 8 · 갭 8 / 총 18) |
| 기반(필수) 목표 | **1/10** 완전 충족 (10%) |

블록별 (충족/부분/갭):

| 블록 | 충족 | 부분 | 갭 |
|---|:-:|:-:|:-:|
| trustworthiness_analysis | 0 | 2 | 1 |
| learning_assurance | 0 | 3 | 4 |
| explainability | 0 | 0 | 2 |
| human_factors | 0 | 2 | 0 |
| safety_risk_mitigation | **2** | 1 | 0 |
| ethics_assessment | 0 | 0 | 1 |

## 핵심 해석

- **SDACS 의 강점은 러닝 어슈어런스가 아니라 안전 위험 완화에 있습니다.** ML(RL) 은
  항상 *자문* 이고, 안전-결정권은 결정적 안전망(`simulation/emergency_protocol.py`)이
  보유합니다. "ML 을 안전-크리티컬 결정에 신뢰하지 않음" 이라는 아키텍처 선택이 본
  매트릭스에서 유일하게 충족인 두 항목(`runtime_safety_monitoring`·
  `classical_safety_net_authority`)의 근거입니다.
- **인증 경로의 가장 큰 갭은 학습 프로세스 검증(일반화)** 입니다
  (`learning_process_verification`). 미학습 시나리오로의 전이 검증 프로토콜이 없으며,
  이는 Track 🔬 451-460 의 핵심 연구 과제와 정확히 일치합니다.
- **Level 분류 미수행**(`ml_application_classification`)이 인증 경로 진입 전제 자체를
  막고 있습니다 — 형식 분류 기록이 후속 작업의 선결 조건입니다.

## CLI

```bash
python simulation/easa_ai_conformance.py --report          # 적합성 요약
python simulation/easa_ai_conformance.py --matrix          # 전체 매트릭스
python simulation/easa_ai_conformance.py --block learning_assurance  # 블록별 목표
python simulation/easa_ai_conformance.py --gaps            # 미충족(갭) 목표
python simulation/easa_ai_conformance.py --foundational    # 기반(필수) 목표
```
