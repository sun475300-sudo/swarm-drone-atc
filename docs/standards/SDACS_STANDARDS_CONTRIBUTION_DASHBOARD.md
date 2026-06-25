# 📡 SDACS 표준화 기고 추적 대시보드 (Phase 470)

*ODYSSEY Track 🏛 Standards & Policy — Phase 470 산출물*
*Created: 2026-06-25 · 분기별 갱신*

## 1. 목적

SDACS 가 정합·기여 가능한 국내외 표준의 **추적 상태** 를 단일 대시보드로 집계. Phase 461 (ASTM F38)·462 (ISO/TC 20/SC 16)·463 (K-드론 정책)·464 (안전 백서) 등 개별 기고 산출물의 종합 진행 현황.

---

## 2. 종합 대시보드 (2026-06-25 기준)

### 2.1 표준 정합 매트릭스

| 표준 기관 | 표준 ID | 정합 상태 | SDACS 산출물 | 다음 단계 |
|:-:|---|:-:|---|---|
| **ASTM F38** | F3548-21 USS Interop | 🟢 강한 정합 | federation_* 9 모듈 + operational_intent | F38 위원회 회람 (Phase 461) |
| **ASTM F38** | F3411 Remote ID | 🟡 부분 정합 | `_sdacs.dni` + telemetry.schema | 텔레메트리 스키마 확장 |
| **ASTM F38** | F3478 D&A | 🟢 강한 정합 | apf+CPA airspace_controller | TM-3 시험 방법 회람 |
| **ASTM F38** | F3196 BVLOS | 🟡 부분 정합 | special_flight_approval (P310) | HITL 데이터 통합 (Track A) |
| **ISO/TC 20/SC 16** | ISO 23629-5 UTM 구조 | 🟢 강한 정합 | federation_* | 참조 구현 공개 (Phase 461·462) |
| **ISO/TC 20/SC 16** | ISO 23629-7 데이터 모델 | 🟢 강한 정합 | telemetry.schema + operational_intent | KSA → KS-X → ISO 경유 기고 |
| **ISO/TC 20/SC 16** | ISO 21895 분류 | 🟢 강한 정합 | airspace_class (P408) | (정합 완료) |
| **ISO/TC 20/SC 16** | ISO/CD 5491 Geofencing | 🟢 강한 정합 | inNFZ + geo_zones | CD 의견서 (Phase 462) |
| **국토부** | K-드론 시스템 ConOps | 🟡 부분 정합 | 6개 제안 (Phase 463) | 국토부 협의 (2026-Q4) |
| **항공안전법** | 제132조 조종자 자격 | 🟢 강한 정합 | pilot_certification (P309) | (정합 완료) |
| **항공안전법** | 제129조 비행계획 | 🟢 강한 정합 | flight_plan_filing (P303) | (정합 완료) |
| **항공안전법** | 제161조 NFZ | 🟢 강한 정합 | inNFZ + geo_zones | (정합 완료) |
| **ICAO** | Annex 13 사고 조사 | 🟢 강한 정합 | incident_investigation_report (P467) | ICAO 의견서 (Phase 432·467) |
| **EASA** | SORA v2.0 | 🟡 부분 정합 | sora_assessment (P302) | OSO 6항 매트릭스 (Phase 464) |
| **EASA** | AI Roadmap 2.0 | 🟡 부분 정합 | (조사만, Phase 451) | AI/ML 1A 시범 (2027) |
| **FAA** | UTM ConOps v2.0 | 🟢 강한 정합 | federation_* | (정합 완료) |
| **JARUS** | SORA 2.5 | 🟡 부분 정합 | sora_assessment 확장 후보 | 워킹그룹 의견서 |
| **GUTMA** | UTM 표준 | 🟢 강한 정합 | telemetry.schema·federation_* | GUTMA 회의 발표 후보 |

> 🟢 강한 정합 (즉시 기고 가능) · 🟡 부분 정합 (확장 필요) · 🔴 미정합 (장기 후보)

### 2.2 기고 산출물 인벤토리

| 분야 | 산출물 | Phase | 상태 |
|---|---|:-:|:-:|
| 위원회 기고 초안 | `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` | 461 | ✅ 작성 |
| 동향 추적 매트릭스 | `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md` | 462 | ✅ 작성 |
| 정책 제안서 | `docs/standards/SDACS_KDRONE_POLICY_PROPOSAL.md` | 463 | ✅ 작성 |
| 안전 백서 | `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` | 464 | ✅ 작성 |
| 표준 시나리오 | `docs/standards/SDACS_BENCHMARK_SUITE.md` (SDACS-SBS-10) | 465 | ✅ 작성 |
| 데이터 스키마 | `docs/schemas/telemetry.schema.json` (Draft-07) | 466 | ✅ 적재 |
| 사고 조사 표준 | `docs/standards/INCIDENT_INVESTIGATION_REPORT.md` | 467 | ✅ 작성 |
| 인증 가능 ML 조사 | `docs/research/RL_GENERALIZATION_SURVEY.md` | 451 | ✅ 작성 |
| 본 대시보드 | `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` | 470 | ✅ 작성 |

### 2.3 기고 일정 통합 (제안)

| 시기 | 활동 | 대상 |
|---|---|---|
| 2026-Q3 | ASTM 멤버십 (학생) | F38 |
| 2026-Q4 | ISO 기고 초안 회람 (KSA 경유) | ISO/TC 20/SC 16 |
| 2026-Q4 | K-드론 정책 제안 회람 | 국토부 (Phase 463) |
| 2027-Q1 | F38 분과 회의 발표 + ASTM-TM-1 제출 | ASTM F38 |
| 2027-Q1 | EASA AI Concept Paper 의견서 | EASA |
| 2027-Q2 | ISO/CD 5491 Geofencing 의견서 | ISO/TC 20/SC 16 |
| 2027-Q2 | GUTMA UTM 회의 발표 | GUTMA |
| 2027-Q3 | 국토부 K-UTM ConOps 2.0 초안 협력 | 국토부 |
| 2027-Q4 | F38 WK 등록 (정식 작업 항목) | ASTM F38 |
| 2028-Q1 | KS-X 표준안 (KAIA 경유 ISO 기고) | KSA / KAIA |
| 2028-Q4 | 항공안전법 시행규칙 개정 | 국토부 |

---

## 3. 회의·컨퍼런스 참석 추적

| 시기 | 행사 | 대상 | SDACS 산출물 |
|---|---|:-:|---|
| 2026-09 | KSAS (한국항공우주학회) 추계 | 학술 | Phase 464 백서 발표 |
| 2026-10 | IROS 2026 | 학술 | Phase 707 논문 투고 |
| 2027-Q1 | F38 Spring Meeting | ASTM | Phase 461 SDACS-TM-1 회람 |
| 2027-Q2 | GUTMA Harmony | 산업 | Phase 466 telemetry 스키마 |
| 2027-Q3 | ICRA 2027 | 학술 | Phase 451 RL 조사 확장 |
| 2027-Q4 | ISO/TC 20/SC 16 회의 (한국 대표) | 표준 | Phase 462 의견서 |

**제약**: 회의 참석은 사용자 환경(목포대 산학·여행·등록비) 의존. 본 표는 *기고 가능성* 의 기준선.

---

## 4. 분기 갱신 절차

```bash
# 본 대시보드 분기 갱신:
# 1. 새 표준 정합 항목 발견 시 §2.1 추가
# 2. 산출물 신규 작성 시 §2.2 추가 (Phase 번호 + 상태)
# 3. 회의 일정 확정 시 §3 갱신
# 4. 정합 상태 변경 (🔴→🟡→🟢) 시 다음 단계 갱신
# 5. 회귀 테스트 갱신 (tests/test_standards_dashboard.py)
```

---

## 5. 한계 (정직성 공시)

- 본 대시보드는 *SDACS 자산 정렬 + 기고 가능성* 의 추적 도구.
- 실제 표준화 위원회 가입·기고·회의 참석은 사용자 환경 의존.
- 표준 채택 결정은 위원회 의결이며 본 문서는 *기술 자산 정렬* 만 보장.
- 분기 갱신을 유지하지 않으면 stale (정직성 공시).

---

## 6. 참조

- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480 Standards & Policy
- `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` (Phase 461)
- `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md` (Phase 462)
- `docs/standards/SDACS_KDRONE_POLICY_PROPOSAL.md` (Phase 463)
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` (Phase 464)
- `docs/standards/SDACS_BENCHMARK_SUITE.md` (Phase 465)
- `docs/standards/INCIDENT_INVESTIGATION_REPORT.md` (Phase 467)
- `docs/research/RL_GENERALIZATION_SURVEY.md` (Phase 451)
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` (Phase 487 — 위원회 의결 정합)
