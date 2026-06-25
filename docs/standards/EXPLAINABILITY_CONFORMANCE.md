# EASA AI 설명가능성(Explainability) 적합성 — ODYSSEY Phase 456

> SDACS 의 ML 구성요소가 EASA 신뢰 가능 AI 프레임워크의 **설명가능성(explainability)**
> 목표를 어디까지 충족하는가를 *이해관계자별·수명주기 단계별* 로 결정적으로 평가한다.
> 자문(advisory)이며 집행(enforcement)이 아니다. EASA 공식 인증이 아니다.

## 1. 위치 — Phase 451 설명가능성 블록의 심층 분해

Phase 451(`simulation/easa_ai_conformance.py`)은 신뢰 가능 AI 6개 빌딩 블록을 한 행씩
*개괄* 했고, 거기서 설명가능성 블록은 단 2행(개발용·운영용)으로 모두 `gap` 으로 뭉뚱그려졌다.
본 모듈(`simulation/explainability_conformance.py`)은 그 한 블록만을 **13개 세부 목표**로
분해해, 실제 리포 자산이 설명가능성을 *부분적으로* 떠받친다는 사실을 정직하게 가시화한다.

| | Phase 451 | Phase 456 (본 문서) |
|---|---|---|
| 범위 | 신뢰 가능 AI 6개 블록 개괄 | 설명가능성 한 블록 심층 |
| 설명가능성 행 수 | 2 (모두 gap) | 13 (충족 2·부분 5·갭 6) |
| 분류 축 | building block | audience (developer·end_user·regulator) |

## 2. 근거 (권위 있는 출처)

- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024): 설명가능성을 *개발 단계*(설계자·V&V·인증 근거용)와 *운영 단계*(최종
  사용자·관제사용, 적시·상황 인식)로 구분하고, 설명 요구 식별·의미 적절성·타당성 검증을
  목표로 제시.
- **EASA Artificial Intelligence Roadmap 2.0** (2023): 설명가능성을 러닝 어슈어런스·안전
  위험 완화와 함께 신뢰 구축의 한 기둥으로 둠.

`anchor` 토큰(EXP:ND/DEV/IN/OP/CE-xx)은 SDACS 의 해석이며 EASA 문서의 정확한 목표 번호를
복제하지 않는다.

## 3. 평가 모델

- `ExplObjective` (frozen dataclass): `objective_id`·`name`·`audience`·`anchor`·
  `foundational`·`status`·`sdacs_module`·`summary`.
- **정직성 결속(불변식):** `status == "gap"` ⟺ `sdacs_module is None`. 충족/부분은 반드시
  실재 경로를 인용하며, 테스트가 인용 경로의 디스크 실재를 강제한다(허위 충족 차단).
- **상태 척도:** `conformant`(1.0) · `partial`(0.5) · `gap`(0.0). 메커니즘만 존재하면
  `partial`, EASA 의미 적절성·타당성까지 검증돼야 `conformant`.
- `ExplainabilityReport`: 카운트 불변식 + `by_audience` 읽기 전용(MappingProxyType) +
  미지 audience 키 거부 + audience 합 교차검증.

## 4. 현재 판정 (`--report`)

```
가중 점수   : 35% (충족 2 · 부분 5 · 갭 6 / 총 13)
기반 목표   : 2/5 완전 충족 (40%) — 기반 미완전 있음

이해관계자별 (충족/부분/갭):
  Developer / V&V        : 1/5/0
  End user / operator    : 0/0/2
  Regulator / certification : 1/0/4
```

### 충족(conformant) — SDACS 의 진짜 강점

| anchor | 목표 | 근거 |
|---|---|---|
| EXP:IN-01 | 본질적 해석 가능 안전 결정 로직 | `simulation/decision_tree_atc.py` — 안전-크리티컬 결정을 블랙박스 ML 이 아닌 IF-THEN 규칙·결정적 디컨플릭션이 내림 |
| EXP:CE-01 | 불변 결정 추적성(감사) | `simulation/audit_trail.py` — 모든 결정이 해시 체인 감사 추적으로 사후 추적·재구성 가능 |

### 부분(partial) — 메커니즘 존재, 검증 미완

| anchor | 목표 | 근거 |
|---|---|---|
| EXP:DEV-01 | 블랙박스 ML 특성화 | `src/rl/ppo_collision.py` |
| EXP:DEV-02 | 특성 중요도(SHAP 류) | `simulation/explainable_ai.py` |
| EXP:DEV-03 | 로컬 대리모델(LIME 류) | `simulation/explainable_ai.py` |
| EXP:DEV-04 | 반사실 설명 | `simulation/explainable_ai.py` |
| EXP:IN-02 | 결정적 해결 추적성 | `simulation/path_deconflict.py` |

### 갭(gap) — Phase 457-460 후속 연구 과제와 정합

설명 요구 식별(EXP:ND)·운영용 실시간 설명 인터페이스(EXP:OP)·의미 적절성/타당성 검증
(EXP:CE) — 즉 *검증된* 설명가능성이 잔여 과제다.

## 5. 정직 공시 (CLAUDE.md)

SDACS 의 ML 설명은 연구 수준이다(대리모델 존재·검증 미완). 그러나 설명가능성의 *핵심* —
안전-크리티컬 결정의 추적·해석 — 은 ML 이 아닌 결정적 로직·감사 추적에서 충족된다. 낮은
가중 점수(35%)는 결함이 아니라 인증 경로의 현 위치를 정직하게 보고하는 것이다.

## 6. CLI

```bash
python simulation/explainability_conformance.py --matrix       # 전체 매트릭스
python simulation/explainability_conformance.py --report       # 요약
python simulation/explainability_conformance.py --audience end_user
python simulation/explainability_conformance.py --gaps         # 미충족(갭)
python simulation/explainability_conformance.py --foundational # 기반(필수)
```

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가. 단위 48건 PASS.
