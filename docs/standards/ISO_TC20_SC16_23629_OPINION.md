# ISO/TC 20/SC 16 — 23629 시리즈(UTM) 군집 운용 의견서 (Standards 잔여 완결)

> SDACS 군집 드론 공역통제 접근을 **ISO/TC 20/SC 16 (Unmanned aircraft
> systems)** 의 UTM 표준 시리즈(ISO 23629)에 대한 **국제 워킹그룹
> 의견서(opinion letter)** 로 제출하기 위한 작성 완료 초안.
> 적합성 검증·정직 공시: [`simulation/iso_tc20_sc16_opinion.py`](../../simulation/iso_tc20_sc16_opinion.py)

## 0. 위상 (밴드 471-480)

Standards & Policy 트랙(Phase 461-480) 밴드 471-480 의 목표는 "국내 표준(KS)
제안 1건 + **국제 워킹그룹 의견서 3건**" 입니다. Phase 473
(`wg_opinion_portfolio`)이 3건 목표를 추적하며, 첫 건(JARUS SORA)·둘째 건
(EUROCAE WG-105, Phase 474 완성)에 이어 본 문서가 **잔여 마지막 1건
(ISO/TC 20/SC 16)** 을 실행 가능한 redline 까지 완성한 산출물입니다.

판정은 Phase 472(`intl_wg_opinion_gate`)의 6개 기준(WG-01~WG-06)에 위임합니다
(중복 로직 0). 본 문서는 각 기준의 *증거 출처(SSoT)* 이며, 모듈은 각 절의
디스크 실재만 감사합니다. 외부 ISO 표준 *동향 추적* 은 Phase 462
(`iso_tc20_sc16_tracker`)의 몫이고, 본 문서는 그중 한 표준에 다는 *의견서
그 자체* 입니다 — 경계 분리, 중복 없음.

> **정직 공시**: 본 의견서는 *작성 완료* 상태이나 *제출 완료* 가 아닙니다.
> 제출 채널(National Body 라우팅)은 문서화했으나(§6) **체계적 검토(systematic
> review) 투표·의견 접수 기한은 ISO 일정에 의존**하므로 WG-06 은 PARTIAL 로
> 정직 공시되며, 따라서 게이트 판정은 `NEEDS_WORK` 입니다. 준비도(작성)와
> 제출 상태(외부 절차)는 독립입니다.

---

## 1. 대상 문서·버전·절(clause)

| 항목 | 값 |
|---|---|
| 발행 기구 | ISO/TC 20/SC 16 (Unmanned aircraft systems) |
| 대상 문서 | ISO 23629-12:2022 — UAS traffic management (UTM) — Part 12: Requirements for UTM service providers |
| 대상 버전 | 발행본(2022) — 차기 체계적 검토(systematic review) 주기 대상 |
| 대상 절(clause) | 충돌 관리(conflict management)·분리 제공(separation provision) 서비스 요건 절 (운영 의도(operational intent) 단위 서비스 정의 부분) |
| 대상 줄(line) | 구독본(licensed copy) 절·줄 번호는 NB 제출 시 명기 |

본 의견서는 **운영 의도(operational intent)를 단일 항공기 단위로 암묵 전제한
UTM 서비스 공급자 요건이 군집(다중 동시 항공기, 단일 운영자) 운영에 적용될
때의 공백**을 대상으로 합니다. 발행 표준에 대한 의견이므로 제출 시점은 차기
체계적 검토 주기이며, 이는 §6 의 채널·기한 절에서 정직하게 공시합니다.

---

## 2. 의견 유형 분류

| 분류 | 표기 | 본 의견 해당 |
|---|:-:|:-:|
| General | `ge` | — |
| **Technical** | **`te`** | **●** |
| Editorial | `ed` | — |

본 의견은 **기술(`te`)** 의견입니다. 군집 운영의 *집합 운영 의도(aggregate
operational intent)* 정의와 부분 손실 시 *격납 유지(graceful degradation)*
요건을 다루므로 단순 편집·일반 의견이 아닙니다 (ISO/IEC Directives Part 1
Annex 의견 유형 분류 칸 필수 충족).

---

## 3. 기술 근거 (SDACS 시뮬 증거)

본 의견은 관찰에 그치지 않고 SDACS 시뮬레이션 실측 증거로 정당화합니다
(WG-03 te 의견의 기술적 정당화 요건).

- **5계층 안전망(L1→L5)**: APF 분리(L1) → 속도 조정(L2) → CBS 재계획(L3) →
  기하 고도 분리(L4) → UTM 전략 디컨플릭션(L5). 각 계층의 안전 주장은 선적된
  산출물로 입증됩니다 — APF 수렴성 Lyapunov 증명
  ([`docs/APF_CONVERGENCE_PROOF.md`](../APF_CONVERGENCE_PROOF.md)), CBS
  완전성·최적성 정리([`docs/CBS_COMPLETENESS_OPTIMALITY.md`](../CBS_COMPLETENESS_OPTIMALITY.md)),
  5계층 우선순위 단조성 TLA+ 명세([`docs/SAFETY_NET_TLA_SPEC.md`](../SAFETY_NET_TLA_SPEC.md)).
- **텔레메트리 데이터 모델 정합**: 군집 텔레메트리의 기계 검증 스키마
  ([`docs/schemas/telemetry.schema.json`](../schemas/telemetry.schema.json),
  Phase 466)가 ISO 23629-7(공간 데이터 모델) 주제와 정합하며, 집합 운영 의도의
  데이터 표현이 실장 가능함을 보입니다.
- **충돌 해결률 정의**: `1 - collisions/(conflicts + collisions)` (프로젝트 공식)
  — 군집 밀도 증가에 따른 충돌 관리 서비스 유효성을 정량 측정 가능.
- **정책 영향 정량화**: 이격 기준 변경의 공역 용량 영향을 결정적 기하 모델로
  산출([`simulation/policy_impact.py`](../../simulation/policy_impact.py)) —
  군집 단위 분리 제공 요건의 *용량 트레이드오프* 를 수치로 제시.

이 증거는 본 의견서의 정량 주장(아래 §4 redline)을 뒷받침합니다.

---

## 4. 제안 변경(Proposed Change) — Redline

ISO/IEC Directives Part 1: *proposed change* 없는 의견은 처리 대상이 아닐 수
있으므로, 실행 가능한 redline 을 제시합니다.

### 4.1 관찰(Observation)

현행 발행본의 UTM 서비스 공급자 요건은 운영 의도(operational intent)를
**항공기 한 대 단위**로 암묵 전제합니다. 군집(단일 운영자·다중 동시 항공기)
운영에서는 (a) N 대를 하나의 운영 의도(공유 4D 볼륨)로 다루는 *집합 운영
의도* 의 수리(acceptance) 기준, (b) 군집 일부 항공기 손실·이탈 시 잔여
군집에 대한 분리 제공·충돌 관리 서비스가 유지되는지가 명시되지 않아,
서비스 공급자·운영자 간 해석 편차가 발생할 수 있습니다.

### 4.2 제안 변경 문안 (Before → After)

> **Before (현행 발행본, 요지):**
> "The UTM service provider shall provide separation provision and conflict
> management services on the basis of the operational intent submitted for
> the unmanned aircraft."
> *(저작권 보호 문서이므로 원문 축자 인용 대신 요지를 적시 — NB 제출 시
> 구독본 원문·절/줄 번호로 대체)*

> **After (제안):**
> "For operations involving multiple simultaneous unmanned aircraft under a
> single operator (swarm operations), the UTM service provider **shall
> accept an aggregate operational intent covering the swarm as a single
> deconfliction subject**, with declared inter-aircraft separation minima
> managed by the operator inside the aggregate volume. The service provider
> shall ensure that (a) separation provision and conflict management
> services remain valid for the remaining fleet upon loss or departure of
> any single aircraft from the aggregate intent (graceful degradation), and
> (b) the operator substantiates intra-swarm separation by analysis,
> simulation, or test. A worked example of such intra-swarm layered
> separation is the SDACS 5-layer safety net (potential-field separation →
> speed regulation → conflict-based re-planning → geometric altitude
> separation → strategic UTM deconfliction)."

### 4.3 근거 요약

제안 문안은 §3 의 5계층 안전망·형식 증명·텔레메트리 스키마·정책 영향
정량화를 *워크드 예제* 로만 인용하며, 특정 구현을 강제하지 않습니다
(중립성 — 기존 표준 부합 원칙). 집합 운영 의도는 ISO 23629-5(기능 구조)·
23629-7(데이터 모델)의 기존 개념과 정합하도록 *확장* 형태로 제안합니다.

---

## 5. 기여자 소속·이해관계 공개

| 항목 | 내용 |
|---|---|
| 기여 주체 | SDACS 캡스톤 프로젝트 (학부 캡스톤 연구) |
| 소속 | 대학 캡스톤 팀 (단일 원저자) |
| 이해관계 | 상업적 이해관계 없음. 제안 redline 은 특정 구현을 강제하지 않으며 SDACS 는 *워크드 예제* 로만 인용 |
| 라이선스 | MIT (오픈소스) — 제안 문안 자유 인용 가능 |

ISO/IEC Directives 및 국내 NB 참여 규약의 소속·이해상충 공개 요건을
충족합니다.

---

## 6. 제출 채널 및 기한

| 항목 | 상태 |
|---|---|
| 공식 채널 | ISO 의견은 회원국 표준화기구(National Body) 경유 제출. 한국: 국가기술표준원(KATS) 관할, 한국공업표준협회(KSA) 경유 접수 후 ISO/TC 20/SC 16 국내 전문위원회가 처리 — Phase 462 추적 문서([`SDACS_ISO_TC20_SC16_TRACKER.md`](SDACS_ISO_TC20_SC16_TRACKER.md)) §제약 과 동일 경로 |
| 채널 확인 | **문서화 완료** (본 절) |
| 제출 기한 | **외부 의존** — 발행 표준(ISO 23629-12:2022)에 대한 의견은 차기 체계적 검토(systematic review) 투표·의견 접수 창구가 열릴 때 제출 가능하며, 그 개시·마감 일자는 ISO 중앙사무국·NB 일정에 의존해 본 산출물이 통제할 수 없음 |

> **정직 공시**: 공식 채널(NB 라우팅)은 문서화했으나 체계적 검토 기한이 외부
> 일정에 의존하므로 WG-06 은 **PARTIAL** 입니다(채널 확인 ○ · 기한 확정 ✗).
> 실제 제출은 KATS/KSA 경유 국내 전문위원회 절차가 필요하며, 이 단계는 외부
> 절차로 본 산출물의 범위를 벗어납니다(사용자 환경 의존).

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
PARTIAL). 점수 0.95/1.0. 이는 sandbox 에서 도달 가능한 정직한 천장입니다 —
`READY_TO_SUBMIT` 은 외부 체계적 검토 기한 확정 후에만 가능합니다.

---

*판정 진리표·기준 정의는 [`simulation/intl_wg_opinion_gate.py`](../../simulation/intl_wg_opinion_gate.py)
(Phase 472)가 유일 명세이며, 본 문서는 증거 SSoT 입니다. 중복 로직 0.*
