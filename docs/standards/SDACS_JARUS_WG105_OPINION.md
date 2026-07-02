# 🌍 국제 워킹그룹 의견서 — JARUS WG-105 (Phase 476)

*ODYSSEY Track 🏛 Standards & Policy — Phase 476 산출물*
*Created: 2026-06-25 · JARUS (Joint Authorities for Rulemaking on Unmanned Systems) WG-105 의견서*

> **정직성 공시**: 본 의견서는 SDACS 연구 산출물 기반 *JARUS WG-105 의견서 초안* 이며, 실 제출은 JARUS 회원국 (한국 — 국토교통부) 경유 필요. 본 문서는 *기술 자산 정렬 + 의견서 양식* 을 제공한다. Phase 472·474·475 자매.

---

## 1. 의견서 정보

| 항목 | 내용 |
|---|---|
| **대상 기구** | JARUS — WG-105 (Specific Operations Risk Assessment 확장) |
| **참조 문서** | SORA v2.5 (예정) + AMC Material 갱신 |
| **카테고리** | Subject Matter Expert (SME) Contribution |
| **제출자** | 국립 목포대학교 드론기계공학과 (Korea — JARUS 회원국 경유) |
| **제출 일자** | 2026-XX-XX (WG-105 차기 회의 한 달 전) |
| **자매 문서** | Phase 472·474·475 |

---

## 2. 요약

JARUS WG-105 의 *SORA v2.5* 갱신 검토에 SDACS 의 **결정적 SORA 산정**(`simulation/sora_assessment.py` Phase 302) + **5계층 안전망**(Phase 464 백서) + **결정적 시뮬레이션 평가 환경**(SDACS-SBS-10 Phase 465) 을 *공개 참조 구현* 으로 제시한다.

---

## 3. 행동 권고

1. **SORA 자동화 도구** — Phase 302 `soraAssess()` 의 결정적 SAIL 산정을 SORA v2.5 의 *참조 구현* 으로 평가.
2. **OSO #07 (DAA) 표준 시험 방법** — 5계층 안전망 정렬 + SDACS-SBS-10 시나리오 채택 검토.
3. **OSO #18 (자동 비상 절차)** — Phase 430 split-brain 4단계 사다리를 SORA OSO #18 *참조 구현* 으로 평가.
4. **OSO #24 (악천후 운용)** — Wind Model 강풍 자동 전환 (>10 m/s) 표준 정렬 권고.
5. **공개 참조 자료** — JARUS 자료실에 MIT 공개 자산 큐레이션.

---

## 4. SORA v2.0 → v2.5 격차 + SDACS 정렬

| SORA 요소 | v2.0 격차 | SDACS 정렬 |
|---|---|---|
| Intrinsic GRC | 정성 평가만 | `sora_assessment.py` 결정적 산정 |
| ARC (Air Risk Class) | 정성 | `airspace_class.py` ICAO A-G 결정적 |
| OSO #07 DAA | 단일 솔루션 가정 | 5계층 안전망 통합 (Phase 464) |
| OSO #18 비상 자동 | 미정의 | Phase 430 4단계 사다리 |
| OSO #24 악천후 | 정성 | Wind Model 임계 자동 전환 |
| Mitigation M1-M3 | 매뉴얼 | SDACS-SBS-10 시나리오 자동 검증 |

---

## 5. 표준화 권고 일정

| 시기 | 활동 |
|---|---|
| 2026-Q4 | JARUS 한국 대표 (국토부) 협의 — 의견서 회람 |
| 2027-Q1 | WG-105 차기 화상 회의 의견서 제출 |
| 2027-Q2 | SORA v2.5 초안 의견 반영 |
| 2027-Q3 | WG-105 대면 회의 발표 (옵션) |
| 2027-Q4 | SORA v2.5 발간 후속 정합 점검 |

---

## 6. 한계

- 본 의견서는 *학술 연구 산출물 기반 권고* 이며 SORA 인증 결정 아님.
- JARUS 회원국 (한국) 대표단 협의는 사용자 환경 의존.
- 실 비행·HITL 검증은 별도 트랙.

---

## 7. 참조

- JARUS: <http://jarus-rpas.org/> (외부)
- SORA v2.0 PDM: <https://www.easa.europa.eu/sora> (외부)
- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` — Phase 464 5계층 백서
- `simulation/sora_assessment.py` — Phase 302 결정적 SAIL
- `simulation/federation_split_brain.py` — Phase 430 4단계 사다리
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
