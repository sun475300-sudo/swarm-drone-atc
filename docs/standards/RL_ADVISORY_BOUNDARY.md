# RL 자문 경계(Advisory Boundary) 명세 — ODYSSEY Phase 453

> 본 문서는 `simulation/rl_advisory_boundary.py` 게이트의 **유일한 산문 출처(SSoT)** 다.
> 모듈은 각 불변식의 상태·근거 경로만 보유하고, 근거·맥락은 본 문서가 보유한다.

## 1. 목적

ODYSSEY Phase 451(`easa_ai_conformance`)은 SDACS 의 *진짜 강점* 이 러닝 어슈어런스가
아니라 **AI 안전 위험 완화** 에 있다고 진단했다. 그 근거는 단 하나의 아키텍처 선택이다:

> **ML(RL) 은 항상 자문(advisory)이며, 안전-결정권은 결정적 5계층 안전망이 보유한다.**

Phase 451 매트릭스에서 유일하게 `conformant` 였던 두 항목(`runtime_safety_monitoring`·
`classical_safety_net_authority`)은 모두 이 선택에서 나온다. 본 Phase 453 은 그 *주장* 을
**검증 가능한 구조 불변식**으로 명문화하고, 리포 구조에서 실제로 성립하는지 결정적
게이트로 판정한다.

| Phase | 질문 | 산출 |
|---|---|---|
| 451 `easa_ai_conformance` | ML 이 EASA 신뢰 가능 AI 를 *어디까지 충족하는가* | 적합성 매트릭스 |
| 452 `rl_generalization_protocol` | *신뢰할 수 있는 일반화 주장* 의 전제가 갖춰졌는가 | 평가 프로토콜 게이트 |
| **453 `rl_advisory_boundary`** | **451·452 가 의지하는 전제("ML=자문")가 구조적으로 성립하는가** | **자문 경계 게이트** |

## 2. 핵심 통찰 — 경계는 약속이 아니라 구조적 사실

SDACS 의 RL/ML 자산은 다음과 같이 **연구 코드로 격리**되어 있다:

- `src/rl/ppo_collision.py` — SB3 PPO 충돌 회피 (학습 전용)
- `simulation/rl_path_selector.py` — Q-테이블 경로 선택 (연구)
- `simulation/deep_rl_controller.py`·`simulation/rl_agent.py`·
  `simulation/reinforcement_learning_trainer.py`·`simulation/marl_coordinator.py`

이들은 **활성 제어/안전 결정 경로의 어떤 모듈도 임포트하지 않는다.** 활성 루프
(관제기·드론 에이전트·시뮬레이터·Failsafe·비상 프로토콜)는 오직 결정적 컴포넌트만
호출한다:

- 충돌 회피 자문: `src.airspace_control.avoidance.resolution_advisory.AdvisoryGenerator`
- 디컨플릭션: `simulation/path_deconflict.py` (4D), CBS, per-drone A* 폴백
- 척력장: `simulation/apf_engine/apf.py` (APF)
- 안전 사다리: `simulation/failsafe_manager.py` → `simulation/emergency_protocol.py`

따라서 자문 경계는 *런타임 클램프* 로 강제되는 것이 아니라 **ML 출력이 안전-크리티컬
결정에 도달할 경로 자체가 없음** 으로써 성립한다.

## 3. 구조 불변식

| ID | 중요도 | 상태 | 근거 |
|---|:-:|:-:|---|
| `ml_isolated_from_active_loop` | 임계 | ✓ 성립 | 활성 루프 라이브 임포트 감사 |
| `deterministic_safety_net_authority` | 임계 | ✓ 성립 | `failsafe_manager.py` (Phase 441 형식 검사) |
| `deterministic_conflict_resolution` | 임계 | ✓ 성립 | `path_deconflict.py` (4D·CBS·A*) |
| `emergency_authority_non_ml` | 임계 | ✓ 성립 | `emergency_protocol.py` |
| `graceful_degradation_without_ml` | 권장 | ✓ 성립 | `apf_engine/apf_gpu.py` (torch 선택 폴백) |
| `runtime_conformance_monitoring` | 권장 | ✓ 성립 | `compliance_checker.py` |
| `reproducible_safety_decisions` | 권장 | ◐ 부분 | `src/utils/rng.py` (시드 RNG 규약) |
| `advisory_role_documented` | 권장 | ✓ 성립 | 본 문서 + Phase 451 |

### 3.1 라이브 감사가 핵심 불변식을 집행한다

`ml_isolated_from_active_loop` 는 정적 선언이 아니라 **라이브 감사**
(`audit_active_loop_imports`)로 뒷받침된다. 이 함수는 활성 루프 모듈 소스를 `ast` 로
파싱해 임포트 노드(`import`·`from ... import`)의 모듈 경로·임포트 이름·별칭을 RL/ML
토큰(`rl_path_selector`·`deep_rl_controller`·`ppo_collision`·`stable_baselines3` 등)과
대조한다 — 주석·문서 문자열은 오탐하지 않고, 괄호 다중 줄 임포트·`as` 별칭·연속 줄
임포트 이름도 누락 없이 탐지한다(문자열 라인 스캔의 위양성/위음성 제거). 누군가 RL 을
활성 루프에 배선하면:

1. `audit_active_loop_imports()` 가 위반을 반환하고,
2. `assess_boundary()` 가 정적 `upheld` 선언을 `partial` 로 **강등** 해 판정을
   `BOUNDARY_AT_RISK` 로 낮추며,
3. 회귀 테스트 `test_active_loop_has_no_ml_imports` 가 즉시 실패한다.

즉 경계는 추측이 아니라 **집행 가능** 하다.

## 4. 판정 규칙

서로소 우선순위로 임계 불변식 상태가 판정을 결정한다(권장 불변식은 점수에만 반영):

1. 임계 불변식 1건이라도 `unverified` → **`BOUNDARY_NOT_ENFORCED`**
2. 임계 불변식이 `partial` → **`BOUNDARY_AT_RISK`**
3. 임계 불변식 전부 `upheld` → **`BOUNDARY_ENFORCED`**

가중 점수: `upheld` 1.0 · `partial` 0.5 · `unverified` 0.0.

**현 리포 판정: `BOUNDARY_ENFORCED`** (임계 4/4 성립, 라이브 감사 위반 0건).

## 5. 정직 공시 (CLAUDE.md)

1. `BOUNDARY_ENFORCED` 는 **"ML 이 활성 루프에서 격리되어 있음"** 의 정직한 보고이지,
   장차 RL 을 활성 루프에 배선할 때 필요한 *능동 가드*(출력 클램프·결정적 재정의·
   감시 트립)가 검증됐다는 뜻이 **아니다**. RL 을 배선하는 순간 본 불변식들은 능동
   가드로 강화되어야 하며, 그때는 본 게이트도 정적 격리 검사에서 능동 가드 검증으로
   확장되어야 한다.
2. `reproducible_safety_decisions` 는 시드 RNG 규약의 존재만 확인하므로 `partial` 이다 —
   전 안전 경로 결정성의 형식 감사는 별도 과제(Phase 450 재현성 패키지 연계).
3. 본 게이트는 자문이며 부수효과가 없다. 무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

## 6. 사용

```bash
python simulation/rl_advisory_boundary.py --report      # 판정 요약
python simulation/rl_advisory_boundary.py --invariants  # 전체 불변식 매트릭스
python simulation/rl_advisory_boundary.py --audit       # 라이브 임포트 감사
python simulation/rl_advisory_boundary.py --gaps        # 미검증 불변식
python simulation/rl_advisory_boundary.py --critical    # 임계 불변식만
```
