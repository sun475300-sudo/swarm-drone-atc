# 🇺🇸 국제 워킹그룹 의견서 — FAA UTM ConOps Working Group (Phase 475)

*ODYSSEY Track 🏛 Standards & Policy — Phase 475 산출물*
*Created: 2026-06-25 · FAA (Federal Aviation Administration) UTM ConOps v2.0 의견서*

> **정직성 공시**: 본 의견서는 SDACS 연구 산출물 기반 *FAA UTM ConOps 의견서 초안* 이며, 실 제출은 FAA Federal Register Notice 공개 의견 수렴 기간 또는 RTCA SC-228 (Minimum Operational Performance Standards for UAS DAA) 경유 필요. 본 문서는 *기술 자산 정렬 + 의견서 양식* 을 제공한다. Phase 472·474 자매.

---

## 1. 의견서 정보

| 항목 | 내용 |
|---|---|
| **대상 기구** | FAA (Federal Aviation Administration) — UAS Integration Office |
| **참조 문서** | UTM ConOps v2.0 + RTCA SC-228 MOPS · UAS Type Certification |
| **카테고리** | Public Comment (Federal Register) / RTCA Working Paper |
| **제출자** | 국립 목포대학교 드론기계공학과 (Republic of Korea — international comment) |
| **제출 일자** | 2026-XX-XX (FAA Federal Register 공개 의견 수렴 기간) |
| **자매 문서** | `docs/standards/SDACS_ICAO_RPASP_OPINION.md` (Phase 472), `docs/standards/SDACS_GUTMA_HARMONY_OPINION.md` (Phase 474) |

---

## 2. 요약 (Executive Summary)

FAA UTM ConOps v2.0 의 핵심 5 기능 (Strategic Conflict Management, Tactical Conflict Resolution, Network Information Service, Constraint Management, USS-to-USS Communication) 에 대해 SDACS 의 **연합 운영(Federation Operations) 9 모듈** + **5계층 안전망**(APF + CBS + CPA + ATC + UTM) + **결정적 시뮬레이션** 자산을 *공개 참조 구현* 으로 제시한다. MIT 라이센스.

---

## 3. 행동 권고 (Recommended Actions)

FAA UAS Integration Office 가 다음을 *고려* 할 것을 요청한다:

1. **결정적 시험 환경 표준화** — RTCA SC-228 MOPS 평가에 SDACS-SBS-10 (10종 표준 시나리오) 채택 검토.
2. **5계층 안전망 통합 요건** — UTM ConOps v2.0 의 *defense in depth* 권고에 5계층 정렬 명시.
3. **USS-to-USS Interoperability** — ASTM F3548-21 정합 SDACS Federation 9 모듈을 RTCA WG 참조 구현으로 평가.
4. **공개 참조 구현 자료실** — FAA UTM 자료실에 SDACS (MIT) 와 같은 공개 자산 큐레이션.

---

## 4. UTM ConOps v2.0 5 기능 ↔ SDACS 정렬

| FAA ConOps 기능 | SDACS 모듈 | 정합 상태 |
|---|---|:-:|
| **SCM** (Strategic Conflict Management) | `simulation/operational_intent.py` (Phase 422 F3548-21) | 🟢 |
| **TCR** (Tactical Conflict Resolution) | `airspace_controller.py` CPA 90s + `apf_engine/apf.py` | 🟢 |
| **NIS** (Network Information Service) | `simulation/federation_discovery.py` (Phase 421) | 🟢 |
| **CM** (Constraint Management — NOTAM/NFZ) | `simulation/federation_notam.py` (Phase 425) + `inNFZ` | 🟢 |
| **USS-to-USS** | Federation 9 모듈 (Phase 421-432) | 🟢 |

---

## 5. 표준화 권고 일정

| 시기 | 활동 |
|---|---|
| 2026-Q4 | Federal Register 공개 의견 수렴 기간 모니터링 (FAA 공식 알림) |
| 2027-Q1 | RTCA SC-228 회의 옵저버 등록 (사용자 환경 의존) |
| 2027-Q2 | RTCA Working Paper 제출 |
| 2027-Q3 | MOPS 초안 의견 반영 |
| 2027-Q4 | FAA Federal Register 후속 의견서 |

---

## 6. 한계 (Limitations)

- 본 의견서는 *학술 연구 산출물 기반 권고* 이며 FAA 인증 결정 아님.
- RTCA 멤버십 + 위원회 활동은 사용자 환경 (목포대 산학·해외 출장) 의존.
- 실 비행 데이터·HITL 검증은 Track A 사용자 HW 의존.
- 본 의견서는 MIT 라이센스 공개 자산만 제공 — 상업적 활용 별개.

---

## 7. 참조

- FAA UTM ConOps v2.0: <https://www.faa.gov/uas/research_development/traffic_management> (외부)
- RTCA SC-228: <https://www.rtca.org/sc-228/> (외부)
- Federal Register: <https://www.federalregister.gov/agencies/federal-aviation-administration> (외부)
- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470
- `docs/standards/SDACS_ICAO_RPASP_OPINION.md` — Phase 472 (자매)
- `docs/standards/SDACS_GUTMA_HARMONY_OPINION.md` — Phase 474 (자매)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
