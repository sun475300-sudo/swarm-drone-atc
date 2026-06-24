# ML 데이터 관리(Data Management) 적합성 — ODYSSEY Phase 455

> EASA *Concept Paper: Guidance for Level 1&2 ML applications* (Issue 02, 2024) 의 신뢰 가능 AI
> 빌딩 블록 **러닝 어슈어런스(Learning Assurance) W-shape 좌측 팔** — *데이터 라이프사이클
> 관리* 목표를 SDACS 의 ML(RL) 자산이 어디까지 충족하는가를 결정적으로 평가하는 자문 게이트.
>
> 구현: [`simulation/ml_data_management.py`](../../simulation/ml_data_management.py) ·
> 테스트: [`tests/test_ml_data_management.py`](../../tests/test_ml_data_management.py) (**77건 PASS**)

## 1. 배경 — 451 이 지목한 갭의 입력측 세분

Phase 451(`easa_ai_conformance`)은 SDACS 의 학습 어슈어런스 최대 갭으로
`learning_process_verification`(미학습 시나리오 전이 일반화)을 지목했다. 그 검증의 *출력측*
(평가 프로토콜)은 Phase 452(`rl_generalization_protocol`)가 게이트하지만, *입력측* — 학습
데이터가 애초에 관리되는가 — 는 빈칸이었다. 본 Phase 455 가 그 빈칸을 EASA Data Management
목표로 세분해 채운다.

| Phase | 축 | 본 모듈과의 경계 |
|---|---|---|
| 451 `easa_ai_conformance` | 빌딩 블록 6종 전체 매트릭스 | 상위 — 본 모듈이 데이터 블록을 세분 |
| 452 `rl_generalization_protocol` | W 우측 — 전이 평가 프로토콜 | 검증 *방법*, 본 모듈은 데이터 *관리* |
| 453 `rl_advisory_boundary` | ML 자문 경계(구조적) | 안전 *경계*, 무관 |
| 454 `ml_application_classification` | EASA Level 분류 | 분류 *대상*, 본 모듈은 데이터 *품질* |
| **455 (본 모듈)** | **W 좌측 — 데이터 라이프사이클** | 요구·수집·전처리·검증 |

## 2. 라이프사이클 단계와 목표 (12종)

| 단계 | 목표 | 중요도 | 현 상태 | 근거 |
|---|---|:-:|:-:|---|
| 요구 | 데이터 요구사항 스키마 명세 | 기반 | ✓ 충족 | `simulation/scenario_schema.py` |
| 요구 | ML 데이터셋 정의 (코퍼스+DR) | 기반 | ✓ 충족 | `src/training/domain_rand.py` |
| 수집 | 표준 시나리오 코퍼스 큐레이션 | 권장 | ✓ 충족 | `docs/standards/SDACS_BENCHMARK_SUITE.md` |
| 수집 | 데이터 분포 운영 포락선 대표 | 기반 | ◐ 부분 | `src/training/domain_rand.py` |
| 수집 | **실세계 데이터 출처·이력** | 기반 | ✗ **갭** | — (실 비행 로그 미수집) |
| 전처리 | 결정적 데이터 파이프라인 | 권장 | ✓ 충족 | `src/utils/rng.py` |
| 전처리 | 시뮬-실측 갭 보정 | 권장 | ◐ 부분 | `src/training/sim_real_gap.py` |
| 전처리 | 데이터 의존성·버전 핀 | 권장 | ◐ 부분 | `requirements.lock.txt` |
| 검증 | train/test 홀드아웃 분리 | 기반 | ✓ 충족 | `simulation/rl_generalization_protocol.py` |
| 검증 | 독립 평가 테스트 셋 | 권장 | ✓ 충족 | `simulation/standard_scenarios.py` |
| 검증 | 데이터 완전성·스키마 감사 | 권장 | ✓ 충족 | `config/scenario_params/nominal_baseline.yaml` |
| 검증 | 데이터 편향·공정성 평가 | 권장 | ✗ 갭 | — (표집 편향 미평가) |

## 3. 판정 로직

기반(foundational) 목표 상태가 판정을 게이트한다(서로소 우선순위):

1. 기반 목표 하나라도 **갭** → `DATA_NOT_READY`
2. 기반 목표가 **부분** → `DATA_AT_RISK`
3. 기반 목표 **전부 충족** → `DATA_MANAGED`

기반 목표가 하나도 없으면 공허한 MANAGED 가 아니라 `DATA_NOT_READY`. 권장 목표의 미완은
판정을 게이트하지 않고 가중 점수(충족 1.0·부분 0.5·갭 0.0)에만 반영된다.

**라이브 산출물 감사**: `audit_cited_artifacts()` 가 인용 경로의 디스크 실재를 강제한다.
인용 산출물이 삭제되면 해당 목표의 정적 `satisfied`/`partial` 선언이 `gap` 으로 강등되고
(근거도 None 으로 제거해 정직성 결속 유지), 판정이 함께 강등된다 — 정적 카탈로그와 실측의
불일치를 정직하게 표면화한다.

## 4. 현 리포 판정 (정직 공시)

```
판정       : DATA_NOT_READY
가중 점수   : 71% (충족 7 · 부분 3 · 갭 2 / 총 12)
기반 목표   : 3/5 충족
```

SDACS 의 RL 학습 데이터는 **시뮬레이션 생성** 이다 — 시나리오 코퍼스(YAML SSoT 10종)와
도메인 무작위화 분포가 곧 데이터셋이고, 실 비행 로그는 수집되지 않았다(Track A 하드웨어
의존). 데이터 *요구 명세*·*홀드아웃 분리*·*결정적 파이프라인* 등 **소프트웨어로 통제 가능한**
골격은 갖췄으나, **실세계 데이터 출처(provenance)** 가 갭인 한 인증용 데이터 관리는 미완이다.

이는 Phase 451 의 보수적 33% 자가 공시·Track A 실기 검증 잔여와 정합한다. `DATA_NOT_READY`
는 결함의 은폐가 아니라 *준비도 ≠ 완수* 의 정직한 보고다.

## 5. 설계 원칙

- **자문이지 집행 아님**: 판정은 권고일 뿐 빌드/머지를 차단하지 않는다.
- **정직성 결속**: `gap` ⟺ `evidence is None`. 충족/부분은 반드시 실재 경로 인용(테스트가
  디스크 실재를 강제 — 허위 충족 주장 차단).
- **결정적**: 무작위성 0 · 부수효과 0 · 기존 모듈 무수정 순수 추가.
- **읽기 전용 교환**: `data_matrix()`·`by_stage` 는 `MappingProxyType` 로 동결.

## 6. CLI

```bash
python simulation/ml_data_management.py --report        # 판정 요약 (기본)
python simulation/ml_data_management.py --objectives    # 전체 목표 매트릭스
python simulation/ml_data_management.py --audit         # 인용 산출물 디스크 감사
python simulation/ml_data_management.py --gaps          # 갭 목표
python simulation/ml_data_management.py --foundational  # 기반 목표만
python simulation/ml_data_management.py --stage collection  # 라이프사이클 단계별
```
