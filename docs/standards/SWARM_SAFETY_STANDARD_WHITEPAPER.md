# 군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구 (ODYSSEY Phase 464)

*Created: 2026-06-21 · Track I (ODYSSEY) Standards & Policy (461-480)*
*기계 검증 골격: [`simulation/swarm_safety_standard.py`](../../simulation/swarm_safety_standard.py)*

> **목적.** 군집(swarm) 무인기 공역 운용의 안전 기준을 SDACS 의 **5계층 안전망**을
> 사례로 제안한다. 본 백서는 산문(이 문서)이 *유일 출처(SSoT)* 이고, 동반 모듈은
> 각 계층의 안전 주장이 *실제 선적 산출물로 입증되는가* 를 결정적으로 감사한다.

---

## 1. 배경과 범위

단일 무인기 안전 기준(ASTM F3322 낙하산, JARUS SORA 운영 위험 등)은 성숙했으나,
**다수 기체가 동시에 같은 공역을 공유하는 군집 운용**의 안전 기준은 아직 표준화
초기 단계다. 본 백서는 SDACS 가 캡스톤 전 과정에서 구축·검증한 5계층 안전망을
*사례 연구*로 제시하여, 군집 안전 기준 표준화 논의(ASTM F38·ISO TC20/SC16·국토부
K-드론)에 기여하는 것을 목표로 한다.

**범위.** 본 백서는 *설계 원칙과 검증 가능성* 을 다룬다. 실 하드웨어 비행 검증은
Track A(P691-700)에 의존하며 본 문서 범위 밖임을 정직히 공시한다 — 따라서 본
백서가 입증하는 것은 "안전망 설계가 형식·경험적 산출물로 뒷받침된다" 이지
"실 비행이 안전하다" 가 아니다.

## 2. 5계층 안전망 정의

군집 안전은 *단일 기법*이 아니라 **시간 척도와 결정 단위가 서로 다른 다섯 계층의
중첩**으로 달성된다. 한 계층이 놓친 위험을 다음 계층이 포착하는 심층 방어
(defense-in-depth) 구조다.

| 계층 | 이름 | 주기 | 결정 단위 | 역할 |
|---|---|:-:|:-:|---|
| **L1** | APF (Artificial Potential Field) | 10 Hz | 개별 드론 | 가까운 장애물 즉시 척력 회피 |
| **L2** | CBS (Conflict-Based Search) | 0.1 Hz | 다중 에이전트 | 사전 경로 충돌 해소 (MAPF) |
| **L3** | CPA (Closest Point of Approach) | 1 Hz | 쌍별 예측 | 미래 충돌 시점 외삽 경보 + 4D 경로 충돌 감지 |
| **L4** | ATC (Air Traffic Controller) | 1 Hz | 전역 관제 | 명령·우선순위·관제권 핸드오프 |
| **L5** | UTM (Unmanned Traffic Management) | 0.1 Hz | 전략적 | NFZ·회랑·Remote ID·UTM 적합성 |

계층 *정의* 의 요구사항→설계→구현→검증 추적성은 RTM(Phase 306,
[`RTM_5LAYER_COVERAGE.md`](../certification/RTM_5LAYER_COVERAGE.md))이 SSoT 다.
본 백서는 정의를 복제하지 않고 *사례 연구 입증* 만 더한다(중복 없는 계층).

## 3. 안전 기준 제안 (proposed)

군집 안전망이 충족해야 할 기준을 제안한다. **모든 임계는 제안(proposed)이며 채택된
표준이 아니다.** SDACS 시험 방법(Phase 461,
[`ASTM_F38_SWARM_TEST_METHOD.md`](ASTM_F38_SWARM_TEST_METHOD.md))의 합격 기준과 정합한다.

1. **계층 독립성** — 각 계층은 다른 계층의 실패와 무관하게 자신의 위험 차원을
   처리할 수 있어야 한다(단일 실패점 최소화).
2. **우선순위 단조성** — 더 긴급한 안전 응답은 덜 긴급한 응답을 *덮어쓸* 수 있어야
   하며, 그 역은 금지된다(래칫). Phase 441 이 형식 모델 검사로 검증.
3. **검증 가능성** — 각 계층의 안전 주장은 형식 증명·모델 검사·경험적 ablation 중
   하나 이상의 *재현 가능한 산출물* 로 뒷받침되어야 한다.
4. **정직한 한계 공시** — 보장하지 못하는 조건(국소 최소·타임박스 폴백·HW 미검증)을
   명시해야 한다.

## 4. 사례 연구 — 계층별 입증 근거

각 계층의 안전 주장이 리포에 선적된 산출물로 입증됨을 보인다. 동반 모듈
`swarm_safety_standard.py` 가 아래 인용 경로의 *디스크 실재* 를 결정적으로 감사하며,
하나라도 부재하면 해당 계층은 SUBSTANTIATED 로 판정되지 않는다(거짓 입증 차단).

| 계층 | 형식/실행 근거 | 보조 문서 |
|---|---|---|
| **L1 APF** | [`apf_lyapunov.py`](../../simulation/apf_lyapunov.py) — F=−∇U 보존성 + Lyapunov 전역 수렴 | [`APF_CONVERGENCE_PROOF.md`](../APF_CONVERGENCE_PROOF.md) |
| **L2 CBS** | [`cbs_optimality.py`](../../simulation/cbs_optimality.py) — 완전성·최적성 독립 BFS 검증 | [`CBS_COMPLETENESS_OPTIMALITY.md`](../CBS_COMPLETENESS_OPTIMALITY.md) |
| **L3 CPA** | [`path_deconflict.py`](../../simulation/path_deconflict.py) — 4D 경로 충돌 감지 코어 | RTM (Phase 306) |
| **L4 ATC** | [`handoff_model_checker.py`](../../simulation/handoff_model_checker.py) — 교착 부재·단일 관제권 불변식 | RTM (Phase 306) |
| **L5 UTM** | [`icao_utm_conformance.py`](../../simulation/icao_utm_conformance.py) · [`remote_id.py`](../../simulation/remote_id.py) | — |

### 계층 횡단(cross-cutting) 근거

5계층의 *결합* 안전(어느 한 계층이 아닌 전체)을 입증하는 산출물:

- [`safety_net_invariant.py`](../../simulation/safety_net_invariant.py) — 계층 우선순위 단조성 불변식 유한 모델 검사 (Phase 441)
- [`SafetyNetPriority.tla`](../../specs/SafetyNetPriority.tla) — 우선순위 TLA+ 형식 명세
- [`SAFETY_NET_TLA_SPEC.md`](../SAFETY_NET_TLA_SPEC.md) — TLA+ 명세 해설
- [`ablation_study.py`](../../scripts/ablation_study.py) — 계층 제거 경험적 효과 측정 (Phase 286)
- [`RTM_5LAYER_COVERAGE.md`](../certification/RTM_5LAYER_COVERAGE.md) — 요구사항 추적 매트릭스 (Phase 306)

## 5. 입증 현황 (자동 산출)

동반 모듈을 실행하면 현 리포 상태의 입증 현황이 출력된다:

```bash
python simulation/swarm_safety_standard.py --report     # 입증 현황 요약
python simulation/swarm_safety_standard.py --markdown   # 사례 연구 매트릭스
python simulation/swarm_safety_standard.py --gaps       # 누락 근거(미실재)
```

현 리포 기준 5계층 전부 SUBSTANTIATED · 가중 커버리지 100% · 횡단 근거 5/5 실재.
(근거 산출물이 삭제·이동되면 자동으로 PARTIAL/UNSUBSTANTIATED 로 강등되어 백서
주장과 코드 현실의 괴리를 드러낸다.)

## 6. 정직한 한계

1. 본 백서가 입증하는 것은 *설계·검증 산출물의 실재* 이며 *실 비행 안전* 이 아니다.
   하드웨어-인-더-루프(HITL)·실외 비행 검증은 Track A 에 의존한다(미충족).
2. 제안 임계(§3)는 채택된 표준이 아니다 — ASTM F38·ISO 등 외부 표준화 절차를 거쳐야
   한다.
3. 형식 검증(L1 Lyapunov·L4 모델 검사)은 *추상 모델* 에 대한 보장이며, 모델이
   실제 시스템을 충실히 반영한다는 가정 하에서만 유효하다(각 산출물에 가정 명시).

---

*본 문서는 SDACS 캡스톤 ODYSSEY 트랙 Phase 464 의 산출물입니다. 군집 안전 기준
표준화 논의에 자유롭게 인용·기여 가능합니다.*
