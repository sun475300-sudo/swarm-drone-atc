# CBS 완전성·최적성 조건 정리 (ODYSSEY Phase 444)

> 다중 에이전트 경로 계획기 `simulation/cbs_planner/cbs.py` 가 구현하는
> Conflict-Based Search(CBS)의 **완전성**·**최적성** 보장이 성립하는 전제를
> 형식화하고, 본 구현이 그 전제를 어디까지 충족하고 어디서 완화하는지를 정직히
> 공시한다. 수치 검증부는 `simulation/cbs_optimality.py`, 핀 고정 테스트는
> `tests/test_cbs_optimality.py`.

참고: Sharon, Stern, Felner, Sturtevant (2015),
*"Conflict-based search for optimal multi-agent pathfinding"*, Artificial Intelligence 219:40–66.

---

## 1. CBS 구조 요약

CBS 는 2계층 탐색이다.

- **고수준(high-level)**: 충돌 트리(CT)를 탐색한다. 각 CT 노드는 *제약 집합* 과
  그에 부합하는 *경로 집합*, 그리고 비용 합(sum-of-costs)을 갖는다. 경로 집합에
  충돌이 있으면 충돌을 *두 자식* 으로 분기한다 — 각 자식은 충돌에 연루된 한
  에이전트에 "그 (위치, 시각)을 점유하지 말라"는 제약을 추가한다.
- **저수준(low-level)**: 한 에이전트에 대해 제약을 지키는 *비용 최소* 경로를
  시공간 A\* 로 찾는다.

본 구현의 격자는 6-이웃 + 대기(wait), 단위 비용, 맨해튼 거리 휴리스틱이다.

---

## 2. 최적성 정리 (Sharon et al. 2015, Thm 1)

**정리.** 다음이 성립하면 CBS 는 비용 합 최적해를 반환한다.

- **(O1)** 저수준이 제약 하에서 *비용 최적* 일치 경로를 반환한다.
- **(O2)** 고수준이 CT 노드를 비용을 1순위 키로 *최선 우선* 으로 확장한다.

**(O1) 충족** — 저수준은 허용적(admissible) 휴리스틱을 쓰는 A\* 다. 6-이웃+대기
단위 비용 시공간 그래프에서 한 스텝은 좌표 하나만 ±1 바꾸므로, 맨해튼 거리는
실제 최소 스텝 수를 결코 과대평가하지 않는다(허용적). 허용적 A\* 는 최적이다.
`cbs_optimality.heuristic_is_admissible` 과 `low_level_is_optimal` 이 독립 BFS
기준해와 비교해 표본 검증한다.

**(O2) 충족** — `cbs_plan` 의 고수준 우선순위 큐는 `heapq` 에 `(cost, …)` 키로
push 하므로 항상 최소 비용 CT 노드를 먼저 확장한다.

→ **결론**: 무한 탐색을 가정하면 본 구현은 (정점 충돌만 있는 인스턴스에서) 최적이다.
`CBSGuaranteeAudit.is_optimal_when_terminates == True`.

---

## 3. 완전성 정리 (Sharon et al. 2015, Thm 2)

**정리.** 다음이 성립하면 CBS 는 해가 존재할 때 반드시 찾는다.

- **(C1)** 저수준이 완전하다(해가 있으면 찾는다).
- **(C2)** 충돌 분기가 *건전(sound)* 하다 — 두 자식 제약의 논리합이 충돌을 빠짐없이
  덮어 어떤 해도 잃지 않는다.
- **(C3)** 탐색이 무한(노드 수 무제한)하다.

**(C2) 정점 충돌에 대해 충족** — 정점 충돌은 두 드론이 같은 `(node, t)` 를 점유한다.
충돌 없는 어떤 해도 "A 가 node@t 에 없음" 또는 "B 가 node@t 에 없음" 중 *적어도
하나* 를 만족한다. 두 자식 제약 `{A≠node@t}`, `{B≠node@t}` 의 논리합은 전체 해
공간을 덮으므로 분기로 잃는 해가 없다. `vertex_branching_is_sound` 가 이를 형식화하고,
`test_branching_disjunction_resolves_crossing_conflict` 가 교차 충돌을 실제 해소함을
실증한다.

---

## 4. 본 구현의 완화점 (honest gap)

직전 Phase 443(APF Lyapunov)이 속도 증폭 비보존성을 정직히 공시했듯, 본 구현도
교과서 CBS 와의 차이를 숨기지 않는다.

| # | 완화점 | 영향 |
|---|---|---|
| **R1** | **에지(swap) 충돌**도 정점 제약 `(node, t)` 으로 근사한다. 정준 CBS 의 에지 제약이 아니다. | 충돌 `node = v`(A 가 t 에 도달하는 칸 = B 의 t-1 위치)에 대해 두 드론에 `≠v@t` 를 추가하는데, **B 측 제약 `B≠v@t` 는 공허(vacuous)** 하다 ─ B 는 t 에 이미 `u(≠v)` 에 있으므로 B 경로에 영향이 없다. 스왑이 해소되지 않을 수 있어 **완전성(C2)이 에지 충돌에 대해 깨진다**(최적성은 불변). |
| **R2** | `max_ct_nodes`·`max_astars`·`max_time`·`max_iterations` 상한. | *유한·anytime* 변형. 해가 깊으면 최적·완전 보장이 끊기고 best-effort 경로를 반환한다(C3 미충족). |
| **R3** | 고수준 동률 타이브레이크가 `id(node)`(메모리 주소). | 비결정적이라 프로젝트 재현성 규칙과 충돌. 해의 *최적성* 은 비용이 1순위 키라 불변이나, 동률 최적해 *선택* 이 실행마다 흔들릴 수 있다. |

`cbs_optimality.is_edge_conflict` 가 R1 의 발현 조건(스왑)을 판정하고,
`test_branching_disjunction_resolves_crossing_conflict` 의 head-on 변형(스왑)이
실제로 정점 근사로 미해소됨을 발견했다(본 Phase 검증 중). `audit_sdacs_cbs` 는
R1·R2·R3 를 모두 `False` 로 공시한다.

→ **결론**: `CBSGuaranteeAudit.is_textbook_complete == False`. 본 구현은
**정점 충돌 인스턴스에서 종료 시 최적**인 *anytime bounded* CBS 변형이며, 에지
충돌·심층 인스턴스의 완전성은 상위 계층(APF 충돌 회피·5계층 안전망)으로 완화한다.

---

## 5. 향후 보강 (선택)

- **에지 제약 도입**(R1 해소): `Constraint` 에 에지 종류를 추가하고 `detect_conflict`
  가 스왑을 에지 제약으로 분기하면 완전성을 정점·에지 모두로 확장할 수 있다 —
  단 본 Phase 는 `cbs.py` 무수정 원칙이라 *진단·공시* 에 한정한다.
- **결정적 타이브레이크**(R3 해소): `id(node)` → `(cost, 생성 순번)` 또는 충돌 수
  등 결정적 2순위 키.
- **`GridNode` 불변화**(기존 부채): `cbs.py` 의 `GridNode` 는 `frozen=True` 가 아니라
  필드 변경 시 해시 불변성이 깨질 수 있다(딕셔너리·집합 키로 광범위 사용). 본 Phase 는
  `cbs.py` 무수정 원칙이라 공시만 한다 ─ 향후 `@dataclass(frozen=True)` 권장.

---

## 6. 재현

```bash
pytest tests/test_cbs_optimality.py -v
python -c "from simulation.cbs_optimality import audit_sdacs_cbs; a=audit_sdacs_cbs(); \
print('optimal_when_terminates =', a.is_optimal_when_terminates); \
print('textbook_complete       =', a.is_textbook_complete)"
```

---

## 참고문헌

1. Sharon, G., Stern, R., Felner, A., Sturtevant, N. R. (2015).
   *Conflict-based search for optimal multi-agent pathfinding.*
   Artificial Intelligence, 219, 40–66.
2. Hart, P. E., Nilsson, N. J., Raphael, B. (1968).
   *A formal basis for the heuristic determination of minimum cost paths.*
   IEEE Trans. SSC, 4(2), 100–107. (A\* 허용성·최적성)
