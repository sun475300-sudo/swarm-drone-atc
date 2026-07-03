# JARUS SORA — 군집 운용(swarm) 보완 의견서 (밴드 첫 후보 redline 완결)

> SDACS 군집 드론 공역통제 접근을 **JARUS (Joint Authorities for Rulemaking
> on Unmanned Systems)** 의 SORA (Specific Operations Risk Assessment) 에 대한
> **국제 워킹그룹 의견서(opinion letter)** 로 제출하기 위한 작성 완료 초안.
> 적합성 검증·정직 공시: [`simulation/jarus_sora_opinion.py`](../../simulation/jarus_sora_opinion.py)

## 0. 위상 (밴드 471-480)

Standards & Policy 트랙(Phase 461-480) 밴드 471-480 의 목표는 "국내 표준(KS)
제안 1건 + **국제 워킹그룹 의견서 3건**" 입니다. Phase 473
(`wg_opinion_portfolio`)이 3건 목표를 추적하며, 둘째 건(EUROCAE WG-105,
Phase 474 완성)·셋째 건(ISO/TC 20/SC 16, Standards 잔여 완결)에 이어 본
문서가 **첫 후보(JARUS SORA)** 를 산문 수준(Phase 472 `shipped_letter` 의
WG-02 PARTIAL 정직 공시)에서 실행 가능한 redline 까지 완성한 산출물입니다.
이로써 밴드 국제 의견서 3건 전부가 redline 작성 완료 상태입니다.

판정은 Phase 472(`intl_wg_opinion_gate`)의 6개 기준(WG-01~WG-06)에 위임합니다
(중복 로직 0). 본 문서는 각 기준의 *증거 출처(SSoT)* 이며, 모듈은 각 절의
디스크 실재만 감사합니다. JARUS 대상 *행동 권고·일정* 은 Phase 476
([`SDACS_JARUS_WG105_OPINION.md`](SDACS_JARUS_WG105_OPINION.md))의 몫이고,
본 문서는 SORA 문안에 다는 *의견서 그 자체(redline 포함)* 입니다 — 경계
분리, 중복 없음.

> **정직 공시**: 본 의견서는 *작성 완료* 상태이나 *제출 완료* 가 아닙니다.
> 제출 채널(JARUS 회원기관 라우팅)은 문서화했으나(§6) **차기 SORA 갱신
> 회람의 의견 접수 기한은 JARUS WG 일정에 의존**하므로 WG-06 은 PARTIAL 로
> 정직 공시되며, 따라서 게이트 판정은 `NEEDS_WORK` 입니다. 준비도(작성)와
> 제출 상태(외부 절차)는 독립입니다.

---

## 1. 대상 문서·버전·절(clause)

| 항목 | 값 |
|---|---|
| 발행 기구 | JARUS (Joint Authorities for Rulemaking on Unmanned Systems) — SORA 유지 관리 워킹그룹 |
| 대상 문서 | JARUS SORA v2.0 패키지 (Main Body + Annexes) |
| 대상 버전 | 발행본 v2.0 — 차기 갱신(v2.5) 회람 주기 대상 (Phase 476 일정 문서와 동일 전제) |
| 대상 절(clause) | Main Body Step #2 (Intrinsic Ground Risk Class 결정 — 운영 볼륨·항공기 전제 부분) 및 Step #9 (Adjacent Area / containment 요건) |
| 대상 줄(line) | 회람 초안의 절·줄 번호는 WG 제출 시 명기 |

본 의견서는 **운영(operation) 한 건을 항공기 한 대 단위로 암묵 전제한 SORA
위험 평가 절차가 군집(다중 동시 항공기, 단일 운영자) 운영에 적용될 때의
공백**을 대상으로 합니다. 발행본 v2.0 에 대한 의견이므로 제출 시점은 차기
갱신 회람 주기이며, 이는 §6 의 채널·기한 절에서 정직하게 공시합니다.

---

## 2. 의견 유형 분류

| 분류 | 표기 | 본 의견 해당 |
|---|:-:|:-:|
| General | `ge` | — |
| **Technical** | **`te`** | **●** |
| Editorial | `ed` | — |

본 의견은 **기술(`te`)** 의견입니다. 군집 운영의 *집합 운영 볼륨(aggregate
operational volume)* 선언과 개별 항공기 손실 시 *격납 유지(graceful
degradation)* 요건을 다루므로 단순 편집·일반 의견이 아닙니다 (ISO/IEC
Directives Part 1 Annex 의견 유형 분류 칸 필수 충족 — Phase 472 WG-04).

---

## 3. 기술 근거 (SDACS 시뮬 증거)

본 의견은 관찰에 그치지 않고 SDACS 시뮬레이션 실측 증거로 정당화합니다
(WG-03 te 의견의 기술적 정당화 요건).

- **결정적 SORA 산정 참조 구현**: SORA v2.0 의 iGRC·SAIL 산정을 결정적으로
  구현한 `_sdacs.soraAssess()`
  ([`swarm_3d_simulator.html`](../../swarm_3d_simulator.html), Phase 302)와
  동일 표(`SORA_IGRC`·`SORA_SAIL_TABLE`)의 Python 복제 + EASA 운영 카테고리
  판정 [`simulation/sora_category.py`](../../simulation/sora_category.py)
  (Phase 403) — 제안 문안의 산정 가능성(implementability)을 공개 코드로 입증.
- **5계층 안전망(L1→L5)**: APF 분리(L1) → 속도 조정(L2) → CBS 재계획(L3) →
  기하 고도 분리(L4) → UTM 전략 디컨플릭션(L5). 각 계층의 안전 주장은 선적된
  산출물로 입증됩니다 — APF 수렴성 Lyapunov 증명
  ([`docs/APF_CONVERGENCE_PROOF.md`](../APF_CONVERGENCE_PROOF.md)), CBS
  완전성·최적성 정리([`docs/CBS_COMPLETENESS_OPTIMALITY.md`](../CBS_COMPLETENESS_OPTIMALITY.md)),
  5계층 우선순위 단조성 TLA+ 명세([`docs/SAFETY_NET_TLA_SPEC.md`](../SAFETY_NET_TLA_SPEC.md)).
- **비상 자동화(OSO #18 정렬)**: 연합 분할(split-brain) 시 4단계 완충 사다리
  ([`simulation/federation_split_brain.py`](../../simulation/federation_split_brain.py),
  Phase 430) — 개별 항공기·링크 손실에서 잔여 편대의 안전 절차가 자동
  유지됨을 결정적 시뮬로 재현.
- **악천후 운용(OSO #24 정렬)**: 풍속 >10 m/s 에서 APF 강풍 파라미터 자동
  전환(WindModel) — 환경 열화 시 격납 유지의 정량 증거.
- **충돌 해결률 정의**: `1 - collisions/(conflicts + collisions)` (프로젝트
  공식) — 군집 밀도 증가에 따른 분리 유효성을 정량 측정 가능.

이 증거는 본 의견서의 정량 주장(아래 §4 redline)을 뒷받침합니다.

---

## 4. 제안 변경(Proposed Change) — Redline

ISO/IEC Directives Part 1 준용(Phase 472 WG-02): *proposed change* 없는
의견은 처리 대상이 아닐 수 있으므로, 실행 가능한 redline 을 제시합니다.

### 4.1 관찰(Observation)

현행 SORA v2.0 은 위험 평가 대상 운영을 **항공기 한 대 단위**로 암묵
전제합니다. 군집(단일 운영자·다중 동시 항공기) 운영에서는 (a) N 대를 하나의
운영으로 다룰 때 *집합 운영 볼륨* 의 선언·수리 기준, (b) intrinsic GRC 산정이
군집 규모(대수·집합 footprint)를 어떻게 반영하는지, (c) 군집 일부 항공기
손실·이탈 시 잔여 편대에 대해 격납(containment)·비상 절차가 유지되는지가
명시되지 않아, 신청자·심사 당국 간 해석 편차가 발생할 수 있습니다.

### 4.2 제안 변경 문안 (Before → After)

> **Before (현행 발행본, 요지):**
> "The intrinsic Ground Risk Class is determined from the maximum UA
> characteristic dimension and the operational scenario of the unmanned
> aircraft; containment requirements apply to the operational volume of the
> operation."
> *(회람 배포 문서이므로 원문 축자 인용 대신 요지를 적시 — WG 제출 시 회람
> 초안 원문·절/줄 번호로 대체)*

> **After (제안):**
> "For operations involving multiple simultaneous unmanned aircraft under a
> single operator (swarm operations), the applicant **shall declare a single
> aggregate operational volume covering the swarm as one operation**, with
> declared inter-aircraft separation minima managed by the operator inside
> the aggregate volume. The intrinsic Ground Risk Class shall be determined
> using the aggregate footprint of the swarm together with the declared
> number of aircraft, rather than per-aircraft values alone. The applicant
> shall substantiate that (a) intra-swarm separation inside the aggregate
> volume is maintained by analysis, simulation, or test, and (b) containment
> and emergency procedures remain valid for the remaining fleet upon loss or
> departure of any single aircraft from the aggregate volume (graceful
> degradation). A worked example of such intra-swarm layered separation is
> the SDACS 5-layer safety net (potential-field separation → speed
> regulation → conflict-based re-planning → geometric altitude separation →
> strategic UTM deconfliction)."

### 4.3 근거 요약

제안 문안은 §3 의 결정적 SORA 참조 구현·5계층 안전망·형식 증명·비상 사다리를
*워크드 예제* 로만 인용하며, 특정 구현을 강제하지 않습니다(중립성 — 기존
표준 부합 원칙). 집합 운영 볼륨은 SORA 의 기존 operational volume 개념을
군집으로 *확장* 하는 형태이며, ISO 23629 계열 의견서
([`ISO_TC20_SC16_23629_OPINION.md`](ISO_TC20_SC16_23629_OPINION.md))의 집합
운영 의도(aggregate operational intent) 제안과 용어·개념이 정합합니다.

---

## 5. 기여자 소속·이해관계 공개

| 항목 | 내용 |
|---|---|
| 기여 주체 | SDACS 캡스톤 프로젝트 (학부 캡스톤 연구) |
| 소속 | 대학 캡스톤 팀 (단일 원저자) |
| 이해관계 | 상업적 이해관계 없음. 제안 redline 은 특정 구현을 강제하지 않으며 SDACS 는 *워크드 예제* 로만 인용 |
| 라이선스 | MIT (오픈소스) — 제안 문안 자유 인용 가능 |

JARUS 참여 규약(기여자 소속·이해상충 공개 — Phase 472 WG-05 근거)을
충족합니다.

---

## 6. 제출 채널 및 기한

| 항목 | 상태 |
|---|---|
| 공식 채널 | JARUS 의견은 회원 기관(member authority) 경유 제출. 한국: 국토교통부 관할 — Phase 476 문서([`SDACS_JARUS_WG105_OPINION.md`](SDACS_JARUS_WG105_OPINION.md)) §5 표준화 권고 일정과 동일 경로(국토부 협의 → WG 회의 제출) |
| 채널 확인 | **문서화 완료** (본 절) |
| 제출 기한 | **외부 의존** — 발행본 SORA v2.0 에 대한 의견은 차기 갱신(v2.5) 회람의 의견 접수 창구가 열릴 때 제출 가능하며, 그 개시·마감 일자는 JARUS WG 일정·회원 기관 협의에 의존해 본 산출물이 통제할 수 없음 |

> **정직 공시**: 공식 채널(회원기관 라우팅)은 문서화했으나 회람 기한이 외부
> 일정에 의존하므로 WG-06 은 **PARTIAL** 입니다(채널 확인 ○ · 기한 확정 ✗).
> 실제 제출은 국토교통부 경유 협의 절차가 필요하며, 이 단계는 외부 절차로 본
> 산출물의 범위를 벗어납니다(사용자 환경 의존).

---

## 7. 게이트 판정 (현 상태)

| 기준 | 충족 | 근거 절 |
|---|:-:|---|
| WG-01 대상 문서·버전·절 | MET | §1 |
| WG-02 제안 변경 redline | MET | §4 (실행 가능한 Before→After) |
| WG-03 기술 근거 결속 | MET | §3 |
| WG-04 의견 유형 분류 | MET | §2 (`te`) |
| WG-05 소속·이해관계 공개 | MET | §5 |
| WG-06 제출 채널·기한 | PARTIAL | §6 (채널 ○·기한 외부 의존) |

**종합 판정: `NEEDS_WORK`** (CRITICAL 전부 충족, 권장 WG-06 외부 의존으로
PARTIAL). 점수 0.95/1.0. redline 완성으로 산문 초안(0.8, Phase 472 최초
공시) 대비 정직하게 격상되었으며, 이는 sandbox 에서 도달 가능한 정직한
천장입니다 — `READY_TO_SUBMIT` 은 외부 회람 기한 확정 후에만 가능합니다.

---

*판정 진리표·기준 정의는 [`simulation/intl_wg_opinion_gate.py`](../../simulation/intl_wg_opinion_gate.py)
(Phase 472)가 유일 명세이며, 본 문서는 증거 SSoT 입니다. 중복 로직 0.*
