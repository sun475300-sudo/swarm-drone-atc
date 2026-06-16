# 5계층 안전망 우선순위 불변식 — 형식 명세 (ODYSSEY Phase 441)

**대상:** SDACS 5계층 안전망의 Failsafe 에스컬레이션 우선순위
**형식 명세:** [`specs/SafetyNetPriority.tla`](../specs/SafetyNetPriority.tla)
**실행 검사기:** [`simulation/safety_net_invariant.py`](../simulation/safety_net_invariant.py)
**구현 근거:** [`simulation/failsafe_manager.py`](../simulation/failsafe_manager.py)

---

## 1. 무엇을 증명하는가

SDACS 의 5계층 안전망(경로계획 → 충돌예측 → APF 회피 → 비상 브레이크 → 자동
귀환)은 위험 수준에 따라 Failsafe 레벨을 자동 전환한다. 이 전환이 가져야 할
핵심 안전 속성은 **우선순위 비역전(no priority inversion)** 이다:

> 위험 상황의 드론은 그 위험이 요구하는 안전 우선순위보다 *낮은* 레벨에
> 머무르지 않는다.

레벨 사다리는 `failsafe_manager.FailsafeLevel` 과 동일하다:

| 값 | 레벨 | 조치 |
|:-:|---|---|
| 0 | NORMAL | continue_mission |
| 1 | WARN | alert_operator |
| 2 | LAND | land_in_place |
| 3 | RTL | return_to_launch |
| 4 | DISARM | force_disarm |
| 5 | EMERGENCY | emergency_stop |

## 2. 위험 차원 → 요구 레벨 (failsafe_manager 임계값 정렬)

| 차원 | 심각도 사다리 | 요구 레벨 |
|---|---|---|
| comm | >2s / >5s / >30s | WARN / RTL / DISARM |
| battery | ≤25% / ≤15% / ≤5% | WARN / LAND / DISARM |
| geofence | breach | RTL |
| collision | imminent | EMERGENCY |

`RequiredLevel` = 활성 위험 차원별 요구 레벨의 **최댓값**("worst hazard wins").
이는 `failsafe_manager.update()` 가 모든 트리거를 평가한 뒤 `_transition()` 의
래칫(`new_level.value <= state.level.value: return`)으로 가장 높은 레벨로
수렴하는 동작의 추상화다.

## 3. 불변식

환경(위험 변화)과 컨트롤러 반응이 *별개* 전이이므로 — 위험이 막 오른 직후
컨트롤러가 아직 안 따라온 *과도 상태* 가 존재 — `level ≥ RequiredLevel` 은
순수 상태 불변식이 아니다. 따라서 다음 *복원·래칫* 속성으로 표현한다:

- **RECOVERABLE (복원 가능성)** — 어떤 도달 가능 상태에서도 컨트롤러 1스텝이면
  SAFE 가 회복된다: `is_safe(controller_step(s))`.
- **NECESSARY (비공허성)** — 컨트롤러 없이 환경만 변하면 SAFE 를 위반하는 도달
  가능 상태가 *실제로 존재* 한다 — RECOVERABLE 이 공허한 참이 아님을 보인다.
- **MONOTONE (래칫)** — 컨트롤러 스텝은 레벨을 절대 낮추지 않는다.
- **RestoreSafe** — NORMAL 복귀는 *모든* 위험이 해제됐을 때만 일어난다.

## 4. 검증 방법 — 유한 상태 전수 탐색

TLA+ 명세는 TLC 로 모델 체킹할 수 있으나, 본 저장소의 최소 컨테이너에서도
재현 가능하도록 **동일한 전이계를 Python 으로 인코딩한 유한 모델 검사기**를
함께 제공한다(`safety_net_invariant.check_invariant`). 검사기는 초기 상태에서
환경 전이와 컨트롤러/복귀 응답 전이를 *모두* 따라가며 도달 가능한 *전* 상태를
**BFS(`deque.popleft`)** 로 전수 탐색하고, 각 상태에서 기본 불변식(복원
가능성)을 확인하며, 위반 시 *최단* 반례 경로를 돌려준다.

상태 공간 = (레벨 6) × (comm 4 × battery 4 × geofence 2 × collision 2 심각도)로
유한하므로 전수 탐색이 종료를 보장한다 — 표본 단위 테스트가 못 주는
"모든 도달 가능 상태에서 성립"을 보장한다.

**정직한 한계 — 검사의 실질적 가치는 차등 검증이다.** 정상(래칫) 컨트롤러에
대해 `is_safe(controller_step(s)) = (max(level, R) ≥ R)` 는 *산술적으로* 즉시
참이다. 따라서 양성 결과 자체는 깊은 정리가 아니다. 전수 탐색의 가치는
**컨트롤러/복귀 *로직 버그* 를 잡아내는 것** — `check_invariant` 에 위험 차원
하나를 빠뜨리는 약화 컨트롤러를 넘기면, 검사기가 *최단* 반례
(초기 → 충돌 임박, 2상태)를 실제로 찾아낸다(음성 테스트). 또한
`controller_necessary()` 가 과도 상태의 실재를 확인해 양성 결과의 비공허성을
보장한다.

```bash
pytest tests/test_safety_net_invariant.py -q   # 20건
```

## 5. 정직한 완화점

- **complete proof 아님 (위 §4)**: 양성 SAFE 결과는 래칫의 산술적 귀결이며,
  검사의 본 가치는 컨트롤러/복귀 로직 버그의 차등 검출이다.
- **collision → EMERGENCY 는 지향(aspirational)**: `failsafe_manager` 는
  `FailsafeLevel.EMERGENCY=5` 를 enum 에 예약했으나 `update()` 에 아직 충돌
  임박 트리거를 배선하지 않았다(현재 EMERGENCY 도달 경로 없음). 본 명세는 그
  트리거가 배선됐을 때 유지되어야 할 불변식을 *미리* 규정한다 — comm·battery·
  geofence 차원은 현 구현과 정합, collision 차원만 미래 정합 대상.
- **추상화 갭**: 본 명세는 *이산* Failsafe 레벨·심각도 사다리만 다룬다.
  연속 시간(comm_age 초)·지리(haversine geofence)·배터리 동역학은 심각도
  인덱스로 추상화됐다 — 임계값 경계 자체의 정합은 `failsafe_manager` 단위
  테스트 책임이며, 본 명세는 임계값을 *가정* 한다.
- **TLC 미실행**: 본 컨테이너에 TLA+ 툴체인이 없어 `.tla` 는 정적 명세이고,
  실제 전수 검증은 동형 Python 검사기가 수행한다. 두 모델의 전이 규칙은
  일대일 대응하도록 작성했으나, 동치성 자체는 수동 검토로만 보장된다(향후
  Phase 442 TLC 모델 체킹에서 기계 검증 예정).
- **단일 드론 범위**: 다중 드론 간 우선순위 협상(CBS·APF 상호작용)은 본
  명세 범위 밖이며 Phase 444(CBS 완전성)·443(APF Lyapunov)이 보완한다.
