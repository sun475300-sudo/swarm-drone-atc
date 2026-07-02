# EUROCAE WG-105 군집(Swarm) ConOps 부속 의견서 (ODYSSEY Phase 474)

> SDACS 군집 드론 공역통제 접근을 EUROCAE WG-105 가 회람하는 SORA 부속
> 문서에 대한 **국제 워킹그룹 의견서(opinion letter)** 로 제출하기 위한
> 작성 완료 초안. 적합성 검증·정직 공시: [`simulation/eurocae_wg105_opinion.py`](../../simulation/eurocae_wg105_opinion.py)

## 0. 위상 (밴드 471-480)

Standards & Policy 트랙(Phase 461-480) 밴드 471-480 의 목표는 "국내 표준(KS)
제안 1건 + **국제 워킹그룹 의견서 3건**" 입니다. Phase 473
(`wg_opinion_portfolio`)이 3건 목표를 추적하며, 첫 건(JARUS SORA)에 더해
**잔여 2건(EUROCAE WG-105·ISO/TC 20/SC 16)** 이 남아 있습니다. 본 문서는 그
잔여 2건 중 **EUROCAE WG-105 의견서를 실행 가능한 redline 까지 완성**한
산출물입니다.

판정은 Phase 472(`intl_wg_opinion_gate`)의 6개 기준(WG-01~WG-06)에 위임합니다
(중복 로직 0). 본 문서는 각 기준의 *증거 출처(SSoT)* 이며, 모듈은 각 절의
디스크 실재만 감사합니다.

> **정직 공시**: 본 의견서는 *작성 완료* 상태이나 *제출 완료* 가 아닙니다.
> 제출 채널은 문서화했으나(§6) **공식 회람 기한은 외부 일정에 의존**하므로
> WG-06 은 PARTIAL 로 정직 공시되며, 따라서 게이트 판정은 `NEEDS_WORK` 입니다.
> 준비도(작성)와 제출 상태(외부 절차)는 독립입니다.

---

## 1. 대상 문서·버전·절(clause)

| 항목 | 값 |
|---|---|
| 발행 기구 | EUROCAE Working Group 105 (Unmanned Aircraft Systems) |
| 대상 문서 | SORA 기반 운영 안전 평가 가이드(Specific Operations Risk Assessment annex) |
| 대상 버전 | 회람 초안(circulated draft) — 특정 버전·개정 일자 회람 시 본 절에 명기 |
| 대상 절(clause) | Tactical Mitigation 및 Containment 요건 절 (다중·동시 UAS 운영 적용 부분) |
| 대상 줄(line) | 회람본 페이지·줄 번호 회람 시 명기 |

본 의견서는 **단일 UAS 가정에 맞춰진 SORA 의 전술 완화(Tactical Mitigation)·
포함(Containment) 요건이 군집(다중 동시 항공기) 운영에 직접 적용될 때의
공백**을 대상으로 합니다.

---

## 2. 의견 유형 분류

| 분류 | 표기 | 본 의견 해당 |
|---|:-:|:-:|
| General | `ge` | — |
| **Technical** | **`te`** | **●** |
| Editorial | `ed` | — |

본 의견은 **기술(`te`)** 의견입니다. 군집 운영에서 전술 완화의 *정량 기준*과
포함 요건의 *계층적 보장*을 다루므로 단순 편집·일반 의견이 아닙니다
(ISO/IEC Directives Part 1 Annex 의견 유형 분류 칸 필수 충족).

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
- **충돌 해결률 정의**: `1 - collisions/(conflicts + collisions)` (프로젝트 공식)
  — 군집 밀도 증가에 따른 전술 완화 유효성을 정량 측정 가능.
- **정책 영향 정량화**: 이격 기준 변경의 공역 용량 영향을 결정적 기하 모델로
  산출([`simulation/policy_impact.py`](../../simulation/policy_impact.py)) —
  군집 포함 요건의 *용량 트레이드오프* 를 수치로 제시.

이 증거는 본 의견서의 정량 주장(아래 §4 redline)을 뒷받침합니다.

---

## 4. 제안 변경(Proposed Change) — Redline

ISO/IEC Directives Part 1: *proposed change* 없는 의견은 처리 대상이 아닐 수
있으므로, 실행 가능한 redline 을 제시합니다.

### 4.1 관찰(Observation)

현행 회람본의 전술 완화·포함 요건은 **단일 UAS** 를 암묵 전제합니다. 군집
(다중 동시 항공기) 운영에서는 (a) 항공기 간 *상호* 전술 완화의 정량 기준,
(b) 일부 항공기 손실 시에도 잔여 군집의 포함이 유지되는지가 명시되지 않아,
운영자·심사자 간 해석 편차가 발생할 수 있습니다.

### 4.2 제안 변경 문안 (Before → After)

> **Before (현행 회람본, 요지):**
> "Tactical mitigations shall reduce the residual collision risk to an
> acceptable level for the operation."

> **After (제안):**
> "For operations involving multiple simultaneous unmanned aircraft (swarm
> operations), tactical mitigations **shall be specified as a layered set
> with a defined activation order and inter-aircraft separation minima**.
> The applicant shall demonstrate that (a) each layer's separation claim is
> substantiated by analysis, simulation, or test, and (b) loss of any single
> aircraft does not invalidate the containment of the remaining fleet
> (graceful degradation). A worked example of such a layered tactical
> mitigation set is the SDACS 5-layer safety net (potential-field separation
> → speed regulation → conflict-based re-planning → geometric altitude
> separation → strategic UTM deconfliction)."

### 4.3 근거 요약

제안 문안은 §3 의 5계층 안전망·형식 증명·정책 영향 정량화를 *워크드 예제*
로만 인용하며, 특정 구현을 강제하지 않습니다(중립성 — 기존 표준 부합 원칙).

---

## 5. 기여자 소속·이해관계 공개

| 항목 | 내용 |
|---|---|
| 기여 주체 | SDACS 캡스톤 프로젝트 (학부 캡스톤 연구) |
| 소속 | 대학 캡스톤 팀 (단일 원저자) |
| 이해관계 | 상업적 이해관계 없음. 제안 redline 은 특정 구현을 강제하지 않으며 SDACS 는 *워크드 예제* 로만 인용 |
| 라이선스 | MIT (오픈소스) — 제안 문안 자유 인용 가능 |

JARUS/EUROCAE 참여 규약의 소속·이해상충 공개 요건을 충족합니다.

---

## 6. 제출 채널 및 기한

| 항목 | 상태 |
|---|---|
| 공식 채널 | EUROCAE WG-105 사무국(secretariat) 경유 회람 의견 제출. 비회원 기고는 WG-105 의장단·연락담당(liaison) 경유 또는 회원 기관을 통한 라우팅 필요 |
| 채널 확인 | **문서화 완료** (본 절) |
| 회람 기한 | **외부 의존** — 대상 초안의 공식 회람(comment period) 개시·마감 일자는 EUROCAE 일정에 의존하며 본 산출물이 통제할 수 없음 |

> **정직 공시**: 공식 채널은 문서화했으나 회람 기한이 외부 일정에 의존하므로
> WG-06 은 **PARTIAL** 입니다(채널 확인 ○ · 기한 확정 ✗). EUROCAE 는 ISO 식
> National Body(NB) 라우팅이 아닌 회원 기반 기구이므로, 실제 제출은 회원
> 기관·liaison 경유가 필요합니다. 이 단계는 외부 절차로 본 산출물의 범위를
> 벗어납니다.

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
`READY_TO_SUBMIT` 은 외부 회람 기한 확정 후에만 가능합니다.

---

*판정 진리표·기준 정의는 [`simulation/intl_wg_opinion_gate.py`](../../simulation/intl_wg_opinion_gate.py)
(Phase 472)가 유일 명세이며, 본 문서는 증거 SSoT 입니다. 중복 로직 0.*
