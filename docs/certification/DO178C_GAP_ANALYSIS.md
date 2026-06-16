# 🏭 DO-178C / ED-12C 소프트웨어 수명주기 갭 분석 (GENESIS Phase 305)

*Created: 2026-06-13 · 기준: RTCA DO-178C / EUROCAE ED-12C (Software Considerations in Airborne Systems and Equipment Certification)*
*면책: 본 문서는 SDACS 가 DO-178C 인증 대상 항공 탑재 소프트웨어가 **아님**을 전제로 한, 수명주기 목표(objectives) 대비 현 자산의 **자가 갭 분석**이다. 실제 인증은 DER/감항 당국의 심사를 거쳐야 하며 본 문서로 갈음되지 않는다.*

---

## 0. 적용 범위와 보증 수준(DAL)

SDACS 는 지상 기반 공역 통제·시뮬레이션 스택으로, 탑재 비행 제어 소프트웨어가 아니다. 따라서 DO-178C 의 직접 적용 대상은 아니나, **5계층 안전망**(L1 APF · L2 CBS · L3 CPA · L4 ATC · L5 UTM)의 개발 엄정성을 DO-178C 목표 체계로 자가 평가한다.

| 항목 | 설정 | 근거 |
|---|---|---|
| 가정 소프트웨어 등급 | **DAL-D** (Minor 고장영향) | 지상 의사결정 보조 — 단일 고장이 항공기 직접 상실로 이어지지 않음 |
| DAL-D 적용 목표 수 | 26개 (DO-178C Annex A, Table A-1~A-10) | Level D 에서 "satisfied" 표시 목표 |
| 독립성 요구 | 없음 (DAL-D) | A·B·C 등급에서만 검증 독립성 요구 |

---

## 1. 수명주기 프로세스 갭 매트릭스 (DO-178C Annex A)

| Table | 프로세스 | DAL-D 목표 | SDACS 충족 자산 | 상태 |
|---|---|:-:|---|:-:|
| A-1 | 소프트웨어 계획 | 1 | `docs/SIMULATOR_*_PLAN.md` (계획 체계) + `MASTER_PLAN_2026H2.md` | 🟢 충족 |
| A-2 | 개발 프로세스 | 2 | 4계층 아키텍처(`CLAUDE.md §7`) + 모듈 명세 | 🟢 충족 |
| A-3 | 고수준 요구 검증 | 1 | `docs/certification/RTM_5LAYER_COVERAGE.md` (REQ 21건) | 🟢 충족 |
| A-4 | 저수준 요구·아키텍처 검증 | — (DAL-D 면제) | RTM DSN 계층 추적 | 🟡 부분 |
| A-5 | 소스코드 검증 | 1 | `code-reviewer` 게이트 + ruff/black | 🟢 충족 |
| A-6 | 통합 검증(테스트) | 3 | pytest 4,062 + E2E 263 + Hypothesis(P447·448) | 🟢 충족 |
| A-7 | 검증 결과 검증 | 1 | `scripts/independent_reproduction.sh` (P486) | 🟢 충족 |
| A-8 | 형상 관리(SCM) | 6 | git + `requirements.lock.txt` 핀 + md5 사본 동기화 | 🟢 충족 |
| A-9 | 품질 보증(SQA) | 1 | CI 6 워크플로 + 코드 리뷰 규칙(`.claude/rules/`) | 🟢 충족 |
| A-10 | 인증 연락(SOI) | 1 | 본 갭 분석 + 인증 디렉터리 | 🟡 부분 |

---

## 2. 추적성(Traceability) — DO-178C §6.5

DAL-D 핵심은 **요구 ↔ 검증** 양방향 추적이다. GENESIS Phase 306 의 RTM 이 이를 담당한다.

| 추적 링크 | 도구/산출물 | 커버리지 |
|---|---|:-:|
| 요구 → 설계 (REQ→DSN) | `RTM_5LAYER_COVERAGE.md` | 21/21 |
| 설계 → 구현 (DSN→IMP) | RTM + 소스 경로 명시 | 21/21 |
| 구현 → 검증 (IMP→VER) | RTM + pytest 노드 | 21/21 |
| 요구 → 검증 (REQ→VER, 역추적) | `scripts/generate_rtm.py` 자동 | 자동 생성 |

**갭**: 저수준 요구(LLR) 의 형식적 분리 미흡 — 현재는 고수준 요구와 코드가 직접 연결됨(DAL-D 에서 허용). DAL-C 이상 격상 시 LLR 계층 신설 필요.

---

## 3. 구조 커버리지 — DO-178C §6.4.4

| 등급 | 요구 커버리지 | SDACS 현황 |
|---|---|---|
| DAL-D | 요구 기반 테스트 (구조 커버리지 **불요구**) | pytest 4,062 통과 |
| DAL-C | + 문장(statement) 커버리지 | CI 측정 88.18% (이미 초과 달성) |
| DAL-B | + 결정(decision) 커버리지 | 미측정 |
| DAL-A | + MC/DC | 미측정 |

DAL-D 는 구조 커버리지를 요구하지 않으나, 본 프로젝트는 이미 문장 커버리지 88% 로 **DAL-C 수준 커버리지 목표를 사실상 충족**한다.

---

## 4. 종합 갭 요약

| 갭 ID | 영역 | 현 상태 | 격상 작업 |
|---|---|---|---|
| GAP-D1 | 저수준 요구(LLR) 계층 부재 | HLR↔코드 직접 연결 | DAL-C 격상 시 LLR 신설 (장기) |
| GAP-D2 | SOI(인증 연락) 공식화 미흡 | 자가 분석만 존재 | 본 문서 + 향후 DER 검토 |
| GAP-D3 | 결정/MC-DC 커버리지 미측정 | 문장 88% 만 측정 | DAL-B 이상 시 `coverage --branch` 도입 |
| GAP-D4 | 도구 검증(DO-330) 미수행 | 자동화 도구 자가 검증 부재 | pytest·extract_sdacs_api 검증 계획 |

**결론**: DAL-D 기준 26개 목표 중 22개 🟢 충족, 4개 🟡 부분. 지상 의사결정 보조 소프트웨어로서 현 엄정성은 DAL-D 를 충족하고 커버리지는 DAL-C 수준에 도달한다. 탑재 소프트웨어 인증이 필요한 경우(예: 온보드 RL 추론 — GENESIS 361) 별도 DAL 재평가가 필요하다.

## 🔗 관련
- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 추적성 매트릭스 (Phase 306)
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 항공안전법 적합성 (Phase 301)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 인증 Phase 301-320
- [`../TECH_DEBT_LEDGER.md`](../TECH_DEBT_LEDGER.md) — mock/speculative 성숙도 공시 (Phase 388)
