# ✈ 국제 워킹그룹 의견서 — IFALPA RPAS Subcommittee (Phase 477)

*ODYSSEY Track 🏛 Standards & Policy — Phase 477 산출물*
*Created: 2026-06-25 · IFALPA (International Federation of Air Line Pilots' Associations) RPAS Subcommittee 의견서*

> **정직성 공시**: 본 의견서는 SDACS 연구 산출물 기반 *IFALPA RPAS Subcommittee 의견서 초안* 이며, 실 제출은 한국민간항공조종사협회 (KAPA) 또는 IFALPA 회원 협회 경유 필요. 본 문서는 *기술 자산 정렬 + 의견서 양식* 을 제공한다. Phase 472·474·475·476 자매 — 표준 dashboard 정합 완성.

---

## 1. 의견서 정보

| 항목 | 내용 |
|---|---|
| **대상 기구** | IFALPA — RPAS Subcommittee |
| **참조 문서** | IFALPA Position Paper on RPAS + ICAO Annex 2 정합 |
| **카테고리** | Position Paper Comment / Technical Brief |
| **제출자** | 국립 목포대학교 드론기계공학과 (Korea — via KAPA 경유) |
| **제출 일자** | 2026-XX-XX (IFALPA RPAS Subcommittee 차기 회의 한 달 전) |
| **자매 문서** | Phase 472·474·475·476 |

---

## 2. 요약

IFALPA 가 강조하는 **유인-무인 통합 공역 안전** 우려에 대해 SDACS 의 **5계층 안전망 + CPA 90s lookahead + ATC 명령 인터페이스** 자산을 제시한다. 본 의견서는 조종사 관점에서 RPAS 통합이 *유인 항공 안전 표준에 부합* 함을 보장하는 기술적 권고를 담는다.

---

## 3. 행동 권고

1. **유인-무인 분리 표준** — 본 SDACS 5계층 안전망 정렬 + SBS-10 시나리오 시험 채택.
2. **ATC 인터페이스** — `_sdacs.atcCommand()` 표준 명령 셋을 RPAS-ATC 통신 *참조* 로 평가.
3. **사고 보고 통일** — Phase 467 ICAO Annex 13 변환기를 RPAS 사고 보고 표준 정렬에 권고.
4. **조종자 자격 정렬** — Phase 309 1-4종 매핑을 *유인 조종사 라이센스와 호환* 측면에서 평가.
5. **공동 안전 백서** — Phase 464 5계층 백서를 IFALPA-ATSEP 공동 안전 자료로 채택 검토.

---

## 4. 유인-무인 통합 격차 + SDACS 정렬

| 격차 | 유인 항공 표준 | SDACS 정렬 |
|---|---|---|
| 분리 거리 | 1,000 ft 수직·5 nm 수평 | `inNFZ`·CPA 90s + 5계층 안전망 |
| ATC 명령 | ATIS·CPDLC·voice | `_sdacs.atcCommand()` 결정적 명령 셋 |
| 사고 보고 | ICAO Annex 13 | Phase 467 변환기 |
| 조종자 라이센스 | ATPL·CPL·PPL | Phase 309 1-4종 매핑 |
| 공역 클래스 | A-G ICAO | Phase 408 `airspace_class.py` |

---

## 5. IFALPA 권고와의 정합

| IFALPA Position | SDACS 정렬 |
|---|---|
| "RPAS 가 동일 안전 표준 충족 시만 통합" | 5계층 안전망 + 결정적 시뮬 충돌 95.9% 검증 |
| "유인 조종사 워크로드 증가 회피" | ATC 명령 자동화 + advisory 6단계 |
| "투명한 사고 조사" | Phase 429 SHA-256 해시 체인 + Phase 467 변환기 |
| "공역 분리 명확성" | Phase 408 ICAO A-G 결정적 분류 |

---

## 6. 표준화 권고 일정

| 시기 | 활동 |
|---|---|
| 2026-Q4 | KAPA (한국민간항공조종사협회) 협의 — 의견서 회람 |
| 2027-Q1 | IFALPA RPAS Subcommittee 차기 화상 회의 의견서 제출 |
| 2027-Q2 | Position Paper 갱신 의견 반영 |
| 2027-Q3 | IFALPA 연차 총회 발표 (옵션) |
| 2027-Q4 | 후속 의견서 |

---

## 7. 한계

- 본 의견서는 *학술 연구 산출물 기반 권고* 이며 IFALPA Position 결정 아님.
- KAPA 또는 IFALPA 회원 협회 경유 제출 필요.
- 실 유인-무인 공역 통합은 다자간 (FAA·ICAO·EASA·국토부) 협의 필요.
- SDACS 는 MIT 라이센스 — IFALPA 회원 협회·항공사·산업체 자유 사용 가능.

---

## 8. 참조

- IFALPA: <https://www.ifalpa.org/> (외부)
- IFALPA RPAS Position: <https://www.ifalpa.org/publications/library/position-papers> (외부)
- KAPA (한국민간항공조종사협회): <http://kapa.or.kr/> (외부)
- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` — Phase 464 (공동 안전 백서 후보)
- `docs/certification/PILOT_LICENSE_MAPPING.md` — Phase 309
- `simulation/incident_investigation_report.py` — Phase 467
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
