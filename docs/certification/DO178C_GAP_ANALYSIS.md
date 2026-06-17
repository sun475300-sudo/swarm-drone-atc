# DO-178C 소프트웨어 수명주기 갭 분석 (GENESIS Phase 305)

*Created: 2026-06-17 · 근거: DO-178C/ED-12C (Software Considerations in Airborne Systems and Equipment Certification), RTCA DO-330 (Tool Qualification), DAL-D (Minor)*
*면책: 본 문서는 SDACS 시뮬레이터 소프트웨어와 DO-178C 목표 간 격차를 분석한 **개발자 참고 자료**이며, 공식 DER/DAH 인증 심사를 갈음하지 않는다. 실 인증 시 해당 인증 기관(EASA/FAA/MOLIT)의 최신 가이던스를 확인해야 한다.*

---

## 1. DO-178C 개요

DO-178C는 항공기 탑재 시스템의 소프트웨어 개발·검증에 대한 국제 표준이다. RTCA(미국)와 EUROCAE(유럽, ED-12C)가 공동 발간하며, FAA AC 20-115D 및 EASA AMC 20-115D를 통해 법적 효력을 갖는다.

### 1.1 소프트웨어 수명주기 프로세스

| 프로세스 | DO-178C 절 | 설명 |
|---|:-:|---|
| **소프트웨어 계획** | §4 | SW Plan, SDP, SVP, SCM Plan, SQA Plan 수립 |
| **소프트웨어 요구사항** | §5.1-5.2 | 고수준 요구사항(HLR) 개발 및 파생 요구사항 식별 |
| **소프트웨어 설계** | §5.3 | 저수준 요구사항(LLR), 아키텍처, 자료흐름 설계 |
| **소프트웨어 코딩** | §5.4 | 코딩 표준 준수, 소스-객체 추적성 |
| **소프트웨어 통합** | §5.5 | 구성요소 통합, 통합 테스트 |
| **소프트웨어 검증** | §6 | 리뷰, 분석, 테스트 (요구사항·설계·코드 기반) |
| **소프트웨어 형상관리** | §7 | 기선(baseline), 변경 통제, 문제 보고 |
| **소프트웨어 품질보증** | §8 | 프로세스 준수 감사, 독립성 확보 |
| **인증 연계** | §9 | PSAC, SAS, SCI 등 인증 산출물 제출 |

### 1.2 설계 보증 수준 (DAL)

| DAL | 영향 | 고장 조건 | 요구 엄격도 |
|:-:|---|---|---|
| A | 치명적 (Catastrophic) | 항공기 손실 | 최고 — MC/DC 필수 |
| B | 위험 (Hazardous) | 심각 부상 | 높음 |
| C | 주요 (Major) | 불편/경미 부상 | 중간 |
| **D** | **경미 (Minor)** | **운용 제한** | **낮음 — 본 분석 대상** |
| E | 영향 없음 (No Effect) | — | 없음 |

> **SDACS 적용 근거**: 군집드론 공역통제 시뮬레이터는 직접 항공기를 제어하지 않으며, 고장 시 운용 제한 수준의 영향을 미친다. 따라서 **DAL-D (Minor)** 를 적용한다.

---

## 2. DAL-D 요구사항 매트릭스

DO-178C Table A-1 ~ A-10에서 DAL-D에 해당하는 목표(Objective)를 추출하고, SDACS 현 상태를 대조한다.

### 2.1 소프트웨어 계획 프로세스 (§4, Table A-1)

| # | DO-178C 목표 | DAL-D 적용 | SDACS 현 상태 | 충족도 |
|:-:|---|:-:|---|:-:|
| A1-1 | 소프트웨어 개발 계획(SDP) 수립 | **적용** | `CLAUDE.md` + `SIMULATOR_GENESIS_PLAN.md`로 개발 프로세스 정의 | **Partial** |
| A1-2 | 소프트웨어 검증 계획(SVP) 수립 | **적용** | pytest 테스트 체계 존재, 별도 SVP 문서 부재 | **Partial** |
| A1-3 | SCM 계획 수립 | **적용** | git workflow 정의 (`CLAUDE.md §8`), 별도 SCMP 문서 부재 | **Partial** |
| A1-4 | SQA 계획 수립 | **적용** | 코드 리뷰 프로세스 존재, 별도 SQAP 문서 부재 | **Partial** |
| A1-5 | 표준 정의 (요구·설계·코딩) | **적용** | `CLAUDE.md` 코딩 스타일 규칙 + pylint/mypy | **Partial** |

### 2.2 소프트웨어 개발 프로세스 (§5, Table A-2 ~ A-5)

| # | DO-178C 목표 | DAL-D 적용 | SDACS 현 상태 | 충족도 |
|:-:|---|:-:|---|:-:|
| A2-1 | 고수준 요구사항(HLR) 개발 | **적용** | `RTM_5LAYER_COVERAGE.md` 21개 REQ 정의 | **Fulfilled** |
| A2-2 | 파생 요구사항 식별 | **적용** | 횡단 요구사항(X-R1~R4) 정의 | **Fulfilled** |
| A2-3 | HLR 정확성·일관성 검토 | 독립성 불요 | GENESIS 306 RTM 내부 검토 완료 | **Partial** |
| A3-1 | 소프트웨어 아키텍처 개발 | **적용** | 4계층 아키텍처 (`CLAUDE.md §7`) | **Fulfilled** |
| A3-2 | 저수준 요구사항(LLR) 개발 | **적용** | 모듈별 docstring 수준, 별도 설계 문서 부재 | **Gap** |
| A4-1 | 코딩 표준 준수 | **적용** | pylint + mypy + `CLAUDE.md` 규칙 | **Partial** |
| A4-2 | 소스코드 추적성 (LLR → 코드) | **적용** | 부분적 (RTM에 IMP 열 존재) | **Partial** |
| A5-1 | 통합 절차 | **적용** | pytest 통합 테스트, CI/CD 파이프라인 | **Fulfilled** |

### 2.3 소프트웨어 검증 프로세스 (§6, Table A-6 ~ A-7)

| # | DO-178C 목표 | DAL-D 적용 | SDACS 현 상태 | 충족도 |
|:-:|---|:-:|---|:-:|
| A6-1 | HLR에 대한 테스트 케이스·절차 | **적용** | pytest 4,291+ 테스트, 89% 커버리지 | **Fulfilled** |
| A6-2 | LLR에 대한 테스트 케이스·절차 | **적용** | 유닛 테스트 존재, LLR 문서와 명시적 연결 부재 | **Partial** |
| A6-3 | 테스트 결과 평가 | **적용** | CI 자동 합격/불합격 판정 | **Fulfilled** |
| A6-4 | 요구사항 기반 테스트 커버리지 | **적용** | RTM VER 열 100% 매핑 | **Fulfilled** |
| A6-5 | 구조적 커버리지 (Statement) | DAL-D 최소 | pytest-cov 89% statement coverage | **Fulfilled** |
| A6-6 | 구조적 커버리지 (Decision) | DAL-D 불요 | — | **N/A** |
| A6-7 | 구조적 커버리지 (MC/DC) | DAL-D 불요 | — | **N/A** |
| A7-1 | 검증 독립성 | 독립성 불요 | 개발자 자체 검증 | **Fulfilled** |

### 2.4 소프트웨어 형상관리 프로세스 (§7, Table A-8)

| # | DO-178C 목표 | DAL-D 적용 | SDACS 현 상태 | 충족도 |
|:-:|---|:-:|---|:-:|
| A8-1 | 형상 식별 | **적용** | git tag + `CHANGELOG.md` + 시맨틱 버저닝 | **Fulfilled** |
| A8-2 | 기선 및 추적성 | **적용** | git commit history + RTM | **Fulfilled** |
| A8-3 | 문제 보고 | **적용** | GitHub Issues + `TECH_DEBT_LEDGER.md` | **Fulfilled** |
| A8-4 | 변경 통제 | **적용** | PR 기반 코드 리뷰, 별도 CCB 절차 부재 | **Partial** |
| A8-5 | 변경 검토 | **적용** | 코드 리뷰 프로세스 존재 | **Fulfilled** |
| A8-6 | 릴리스 통제 | **적용** | git tag 기반, 빌드 환경 문서화 부족 | **Partial** |

### 2.5 소프트웨어 품질보증 프로세스 (§8, Table A-9)

| # | DO-178C 목표 | DAL-D 적용 | SDACS 현 상태 | 충족도 |
|:-:|---|:-:|---|:-:|
| A9-1 | SQA 프로세스 활동 | **적용** | 코드 리뷰 + CI 게이트 | **Partial** |
| A9-2 | 프로세스 준수 감사 | 독립성 불요 | 자체 CLAUDE.md 규칙 준수 확인 | **Partial** |
| A9-3 | 편차·비준수 보고 | **적용** | `TECH_DEBT_LEDGER.md` 기술 부채 추적 | **Partial** |
| A9-4 | SQA 기록 | **적용** | git log + PR 기록, 별도 SQA 기록부 부재 | **Partial** |

---

## 3. SDACS 현 상태 대조

### 3.1 요구사항 (Requirements)

| 항목 | 현 상태 | 평가 |
|---|---|:-:|
| 고수준 요구사항 | `RTM_5LAYER_COVERAGE.md` (GENESIS 306) — 5계층 21개 REQ 정의, REQ→DSN→IMP→VER 추적 완료 | **Strong** |
| 시스템 요구사항 사양서 (SRS) | 별도 문서 부재 — RTM이 부분 대체 | **Gap** |
| 파생 요구사항 | 횡단 요구사항 X-R1~R4 식별 완료 | **Adequate** |
| 요구사항 검증 | RTM VER 열 100% 커버 | **Strong** |

### 3.2 설계 (Design)

| 항목 | 현 상태 | 평가 |
|---|---|:-:|
| 소프트웨어 아키텍처 | `CLAUDE.md §7` 4계층 아키텍처 정의 (드론→제어→시뮬→UI) | **Adequate** |
| 저수준 설계 | 모듈별 docstring + inline 주석 수준, SDD 문서 부재 | **Gap** |
| 자료흐름/제어흐름 | 시각화 3D 대시보드에 표현, 문서화 미흡 | **Gap** |

### 3.3 코딩 (Coding)

| 항목 | 현 상태 | 평가 |
|---|---|:-:|
| 코딩 표준 | `CLAUDE.md` 규칙 + pylint + mypy 정적 분석 | **Adequate** |
| 소스코드 추적성 | RTM IMP 열에 파일 경로 기재, 함수 수준 추적성 부족 | **Partial** |
| 코드 복잡도 관리 | 50줄/함수, 800줄/파일 규칙 적용 | **Adequate** |

### 3.4 테스트 (Testing)

| 항목 | 현 상태 | 평가 |
|---|---|:-:|
| 테스트 프레임워크 | pytest — 4,291+ 테스트 케이스, 89% statement coverage | **Strong** |
| 요구사항 기반 테스트 | RTM VER 열 21/21 (100%) 매핑 | **Strong** |
| 구조적 커버리지 (Statement) | 89% — DAL-D 최소 기준 (Statement) 충족 | **Strong** |
| 테스트 절차 문서화 | `CLAUDE.md §6` Quick Commands, 별도 테스트 절차서 부재 | **Partial** |
| 재현성 | `np.random.default_rng(seed)` + `PYTHONHASHSEED=0` — 18차 독립 재현 검증 | **Strong** |

### 3.5 형상관리 (Configuration Management)

| 항목 | 현 상태 | 평가 |
|---|---|:-:|
| 버전 관리 | git + GitHub, 브랜치 전략 적용 | **Strong** |
| 변경 이력 | `CHANGELOG.md` + git commit history | **Strong** |
| 문제 추적 | GitHub Issues + `TECH_DEBT_LEDGER.md` | **Adequate** |
| 릴리스 관리 | git tag 기반, 빌드 환경 재현성 문서화 부족 | **Partial** |

### 3.6 품질보증 (Quality Assurance)

| 항목 | 현 상태 | 평가 |
|---|---|:-:|
| 코드 리뷰 | PR 기반 리뷰 프로세스, `code-reviewer` 에이전트 활용 | **Adequate** |
| 프로세스 감사 | 자체 규칙 준수 확인, 독립 감사 부재 | **Partial** |
| 비준수 추적 | `TECH_DEBT_LEDGER.md` — 기술 부채 및 mock 기능 공시 | **Adequate** |
| CI/CD | GitHub Actions 자동 테스트, 별도 QA 게이트 미정의 | **Partial** |

---

## 4. 격차 요약 (Gap Summary)

| # | 격차 영역 | DO-178C 목표 | 심각도 | 현 상태 | 필요 조치 |
|:-:|---|---|:-:|---|---|
| G1 | 소프트웨어 계획 문서 | A1-1~A1-5 | **Medium** | `CLAUDE.md`로 부분 대체 | SDP·SVP·SCMP·SQAP 4대 계획서 작성 |
| G2 | 시스템 요구사항 사양서 (SRS) | A2-1, A2-3 | **High** | RTM이 부분 대체, 정식 SRS 부재 | DO-178C §5.1 준수 정식 SRS 작성 |
| G3 | 저수준 요구사항/설계 문서 (SDD) | A3-2, A4-2 | **High** | 모듈별 docstring 수준 | 모듈별 SDD 작성, LLR→코드 추적성 확보 |
| G4 | 자료흐름/제어흐름 문서 | A3-1 보완 | **Medium** | 아키텍처 정의 존재, 흐름도 부재 | DFD/CFD 다이어그램 작성 |
| G5 | 함수 수준 코드 추적성 | A4-2 | **Medium** | 파일 수준만 추적 | RTM IMP 열을 함수 수준으로 세분화 |
| G6 | 테스트 절차서 | A6-1, A6-2 | **Low** | pytest 코드 존재, 절차 문서 부재 | 테스트 계획서·절차서 작성 (SVP 통합) |
| G7 | 변경 통제 위원회 (CCB) | A8-4 | **Low** | PR 리뷰로 대체 | CCB 절차 정의 (소규모 팀 간소화 허용) |
| G8 | 빌드 환경 문서화 | A8-6 | **Medium** | `requirements.txt` 존재, 빌드 환경 재현 문서 부족 | 빌드 환경 사양서 (SAS 항목) 작성 |
| G9 | SQA 기록부 | A9-3, A9-4 | **Low** | git log + PR 기록 | SQA 감사 로그 정식 양식 도입 |
| G10 | 도구 검증 (DO-330) | 보조 | **Low** | pytest·pylint·mypy 미검증 | TQL-5 (DAL-D 대응) 도구 자격 평가 |

### 충족도 집계

| 충족도 | 목표 수 | 비율 |
|---|:-:|:-:|
| **Fulfilled** | 14 | 48% |
| **Partial** | 13 | 45% |
| **Gap** | 2 | 7% |
| **N/A** (DAL-D 불요) | 2 | — |
| **합계** | 31 | 100% |

> DAL-D에서는 MC/DC 및 검증 독립성이 요구되지 않으므로, 전체 31개 목표 중 N/A 2건을 제외한 29건이 평가 대상이다. 이 중 14건(48%)이 충족, 13건(45%)이 부분 충족, 2건(7%)이 격차로 식별되었다.

---

## 5. 격상 계획 (Remediation Roadmap)

우선순위: **P1** (인증 차단) → **P2** (인증 권고) → **P3** (품질 개선)

| 우선순위 | 격차 # | 조치 | 산출물 | 예상 Phase |
|:-:|:-:|---|---|:-:|
| **P1** | G2 | 정식 SRS 작성 — 5계층 안전망 + 시스템 요구사항 기술 | `docs/certification/SRS_SDACS.md` | GENESIS 310 |
| **P1** | G3 | 모듈별 SDD 작성 — 저수준 요구사항 및 인터페이스 정의 | `docs/certification/SDD_*.md` (모듈별) | GENESIS 311 |
| **P2** | G1 | 4대 계획서 (SDP/SVP/SCMP/SQAP) 작성 | `docs/certification/plans/` | GENESIS 312 |
| **P2** | G4 | DFD/CFD 다이어그램 — 4계층 자료흐름·제어흐름 시각화 | `docs/certification/DFD_CFD.md` | GENESIS 313 |
| **P2** | G5 | RTM IMP 열 함수 수준 세분화 | `RTM_5LAYER_COVERAGE.md` 갱신 | GENESIS 306 갱신 |
| **P2** | G8 | 빌드 환경 사양서 — Python 버전, 의존성, Docker 설정 기록 | `docs/certification/BUILD_ENV_SPEC.md` | GENESIS 314 |
| **P3** | G6 | 테스트 절차서 — pytest 테스트 슈트 구조 및 실행 절차 문서화 | SVP 통합 | GENESIS 312 통합 |
| **P3** | G7 | CCB 절차 정의 — 소규모 팀 간소화 변경 통제 | SCMP 통합 | GENESIS 312 통합 |
| **P3** | G9 | SQA 감사 로그 양식 도입 | SQAP 통합 | GENESIS 312 통합 |
| **P3** | G10 | 도구 자격 평가 (TQL-5) — pytest, pylint, mypy | `docs/certification/TOOL_QUAL.md` | GENESIS 315 |

### 단계별 목표

```
Phase 310-311 (P1): SRS + SDD 작성 → Fulfilled 비율 48% → 62% 목표
Phase 312-314 (P2): 계획서 + DFD/CFD + 빌드 환경 → Fulfilled 비율 62% → 83% 목표
Phase 315+   (P3): 도구 검증 + SQA 기록 정비 → Fulfilled 비율 83% → 93%+ 목표
```

---

## 6. DAL 격상 시 추가 요구사항 참고

향후 SDACS가 실 드론 제어 시스템으로 전환될 경우, DAL-C 이상 격상이 필요하다. 아래는 격상 시 추가되는 주요 요구사항이다.

| 항목 | DAL-D (현재) | DAL-C (격상 시) | DAL-B (참고) |
|---|---|---|---|
| 구조적 커버리지 | Statement | + Decision | + MC/DC |
| 검증 독립성 | 불요 | **필요** | 필요 |
| 소스→객체 추적 | 불요 | 불요 | **필요** |
| 도구 자격 | TQL-5 | TQL-4 | TQL-3 |

> 본 분석은 캡스톤 시뮬레이터 범위에서 DAL-D를 적용한다. Sim-to-Real 전환(TRANSCENDENCE 261-280) 시 DAL 재평가가 필수이다.

---

## 7. 관련 링크

- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — 요구사항 추적 매트릭스 (GENESIS 306)
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 항공안전법 적합성 매트릭스 (GENESIS 301)
- [`KC_RADIO_CERTIFICATION.md`](KC_RADIO_CERTIFICATION.md) — KC 전파인증 체크리스트 (GENESIS 304)
- [`AIRSPACE_CLASS_MAPPING.md`](AIRSPACE_CLASS_MAPPING.md) — ICAO 공역 클래스 매핑 (ODYSSEY 408)
- [`PILOT_LICENSE_MAPPING.md`](PILOT_LICENSE_MAPPING.md) — 조종자 자격증명 매핑
- [`../hardware/fmea_report.md`](../hardware/fmea_report.md) — FMEA 보고서 (P700)
- [`../TECH_DEBT_LEDGER.md`](../TECH_DEBT_LEDGER.md) — 기술 부채 원장 (GENESIS 388)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 인증 Phase 301-320
