# 🇰🇷 K-드론 시스템 고도화 정책 제안서 (Phase 463)

*ODYSSEY Track 🏛 Standards & Policy — Phase 463 산출물*
*Created: 2026-06-25 · 국토교통부 제출 형식*

> **정직성 공시**: 본 제안서는 SDACS 연구 산출물 기반 *정책 권고 초안* 이며, 실제 국토부 제출은 사용자 환경(목포대 캡스톤·산학·인증) 의존. 본 문서는 제출 형식 + SDACS 정렬 자산 매핑을 제공한다.

---

## 1. 제목 + 요약

**제목**: K-드론 시스템(K-UTM) 고도화 — 결정적 시뮬레이션 기반 안전망·연합 운영·교육 자산 통합 제안

**요약**: 한국 도심 항공 모빌리티(K-UAM) 와 K-UTM 의 정합성 강화를 위해, **5계층 안전망**(APF+CBS+CPA+ATC+UTM) + **연합 운영**(인스턴스 간 디스커버리·핸드오버·NOTAM·신뢰·감사) + **인증 가능 ML 조사** + **결정적 표준 시나리오 10종**(SDACS-SBS-10) 의 통합 적용을 제안한다.

---

## 2. 배경 + 문제 정의

### 2.1 K-드론 시스템 현황 (2026년)

| 항목 | 현황 | 격차 |
|---|---|---|
| **K-UTM 운영 인프라** | 한국항공우주연구원(KARI) + 한국교통연구원(KOTI) 협력 | 다중 인스턴스 연합 운영 미정의 |
| **공역 분류** | 비행제한구역(NFZ) + 비행금지구역(NFZ-1) 정적 | 동적 NOTAM 자동 전파 부족 |
| **충돌 회피** | APF·CPA 개별 솔루션 | 5층 안전망 통합 표준 부재 |
| **사고 조사** | ARAIB(항공·철도사고조사위원회) 표준 | 시뮬레이션 데이터 ↔ 표준 양식 변환기 부재 |
| **조종자 자격** | 항공안전법 제132조 1-4종 | 시뮬 교육 모드 정렬 부족 |

### 2.2 본 제안의 차별점

본 제안은 SDACS (목포대 캡스톤) 가 결정적·재현 가능 형태로 구현한 200+ Phase 자산을 기반으로 한다:

- 5계층 안전망 (Phase 1-690 Core)
- ODYSSEY Federation Operations 9 모듈 (Phase 421-432)
- 인증 가능 ML 조사 (Phase 451)
- 표준 시나리오 SDACS-SBS-10 (Phase 465)

---

## 3. 제안 사항

### 3.1 제안 1: K-UTM 결정적 시험 환경 표준화

**근거**: 현 K-UTM 평가가 인스턴스마다 시드·시나리오·소프트 버전이 다름 → 재현·비교 곤란.

**제안**:
- SDACS-SBS-10 표준 시나리오 10종 (`docs/standards/SDACS_BENCHMARK_SUITE.md`) 을 K-UTM 평가 baseline 으로 채택.
- 결정적 시드 (`np.random.default_rng(seed)`) 의무화 + 시드 + 소프트 버전 + 시나리오 파일 hash 함께 보고.
- 회귀 게이트: resolution rate ≥ 95% (N ≤ 100), ≥ 90% (N ≥ 500).

### 3.2 제안 2: 5계층 안전망 통합 표준

**근거**: 단일 계층(APF only 또는 CPA only) 솔루션은 silent breakage 위험. SDACS Phase 464 백서 §3 사례에서 5층 통합 시만 100% resolution.

**제안**:
- 항공안전법 시행규칙에 *5계층 안전망 권고* 추가.
- L1 APF · L2 CBS · L3 CPA · L4 ATC · L5 UTM 우선순위 매트릭스 명시.
- Phase 441 TLA+ 형식 명세를 표준 invariant 로 채택.

### 3.3 제안 3: 다중 인스턴스 연합 운영 ConOps

**근거**: 현 K-UTM 은 단일 운영자 모델. 다중 USS(UAS Service Supplier) 인접 공역 충돌 시 결정적 규칙 부재.

**제안**:
- ASTM F3548-21 (USS Interoperability) 호환 인스턴스 간 디스커버리·핸드오버·충돌 해소 채택.
- SDACS Federation 9 모듈을 *참조 구현* 으로 제공 (오픈 소스 MIT 라이센스).
- 분할 뇌(split-brain) 안전 강하 4단계 사다리 (NOMINAL → HOLD → DESCEND → LAND) 의무화.

### 3.4 제안 4: 인증 가능 ML 단계적 도입

**근거**: K-UTM 에 RL 도입 시 인증 기준 부재 → 사고 조사 곤란.

**제안**:
- EASA AI Roadmap 2.0 의 AI/ML 1A → 1B → 2A 단계적 도입 (`docs/research/RL_GENERALIZATION_SURVEY.md` §5 권고).
- 학습 시 결정적 의사난수·시드 분리·multi-seed 평가 의무화.
- OOD 탐지 회귀 (Phase 447 fuzzer 변이 시나리오) 통과 시만 운영 인가.

### 3.5 제안 5: 사고 조사 표준 변환기

**근거**: 현 K-UTM 시뮬 로그 → ARAIB 표준 양식 변환이 수작업 → 사고 분석 지연.

**제안**:
- SDACS Phase 467 변환기 (`simulation/incident_investigation_report.py`) 를 KARI/KOTI 와 공유.
- ICAO Annex 13 정합 — 국제 사고 조사 호환.

### 3.6 제안 6: 교육 자산 표준화

**근거**: 현 조종자 자격(1-4종) 과 시뮬 교육 매핑 부재.

**제안**:
- SDACS Phase 309 (`docs/certification/PILOT_LICENSE_MAPPING.md`) 를 자격 인정 시뮬 표준으로 채택.
- 15주 커리큘럼 (Phase 381-387 GENESIS) 을 항공대·목포대 캡스톤 표준으로 제안.

---

## 4. 기대 효과

| 영역 | 효과 |
|---|---|
| 안전성 | 5계층 안전망 통합 → 단일 솔루션 대비 충돌률 감소 |
| 재현성 | 결정적 시드·SDACS-SBS-10 → K-UTM 평가 재현 가능 |
| 국제 정합 | ASTM F3548/F3478·ICAO Annex 13·EASA SORA 호환 |
| 산업 부담 | MIT 라이센스 참조 구현 → 중소 드론 사업자 진입 비용 감소 |
| 교육 | 15주 커리큘럼 + 시뮬 교육 모드 → 조종자 양성 표준화 |

---

## 5. 추진 일정 (제안)

| 단계 | 시기 | 산출물 |
|---|---|---|
| 1. 정책 협의 (국토부·KARI·KOTI) | 2026-Q4 | 본 제안서 회람 + 의견 수렴 |
| 2. 표준 초안 워킹그룹 | 2027-Q1 | K-UTM ConOps 2.0 초안 |
| 3. 산업 협의체 검토 (KAIA·KIDA) | 2027-Q2 | 의견 통합 |
| 4. 공청회 | 2027-Q3 | 시민·전문가 의견 |
| 5. 항공안전법 시행규칙 개정 | 2027-Q4 | 5계층 권고 명문화 |
| 6. 운영 가이드라인 배포 | 2028-Q1 | K-UTM 운영자 매뉴얼 |

**제약**: 정책 협의·공청회·시행규칙 개정은 사용자 환경(목포대 산학·국토부 의견 수렴)에 의존. 본 문서는 *기술 자산 정렬 + 제출 형식* 의 기준선이다.

---

## 6. 첨부 (SDACS 참조)

- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🌏 — Phase 401-420 Global Expansion
- `docs/standards/SDACS_BENCHMARK_SUITE.md` — Phase 465 SDACS-SBS-10
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` — Phase 464 5계층 안전망 백서
- `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` — Phase 461 ASTM F38 정렬
- `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md` — Phase 462 ISO/TC 20/SC 16
- `docs/research/RL_GENERALIZATION_SURVEY.md` — Phase 451 인증 가능 ML
- `docs/certification/AIR_SAFETY_ACT_MATRIX.md` — GENESIS 301 항공안전법 매트릭스
- `docs/certification/PILOT_LICENSE_MAPPING.md` — Phase 309 조종자 자격 매핑
- `simulation/federation_*.py` — 9 federation 모듈 (Phase 421-432)
- `simulation/incident_investigation_report.py` — Phase 467 ICAO Annex 13

---

## 7. 제출 정보 (template)

```
제목: K-드론 시스템(K-UTM) 고도화 정책 제안
제출처: 국토교통부 항공정책실 항공교통과
제출자: 국립 목포대학교 드론기계공학과 (Department of Drone Mechanical Engineering, Mokpo National University)
제출 일자: YYYY-MM-DD
연락처: <지도교수 / 산학협력단 경유>
첨부: SDACS GitHub 레포지터리 (MIT License)
```

본 제안서가 정식 제출 시 필요한 추가 자료:
- 첨부 1: SDACS 종합 백서 (현 ROADMAP + Phase Matrix)
- 첨부 2: 5계층 안전망 사례 연구 (Phase 464 백서)
- 첨부 3: 라이센스 호환성 확인서 (MIT)
- 첨부 4: 학회 발표 자료 (IROS 2026 또는 ICRA 2027)

---

## 8. 한계 (정직성 공시)

- 본 제안서는 *학술 연구 산출물 기반 권고* 이며 SDACS 가 실 운영 인증된 시스템이 아님을 명시.
- 정책 추진은 국토부·KARI·KOTI·KAIA 등 다자간 협의 필요.
- 실 비행 데이터·HITL 검증은 Track A (사용자 HW) 진행 필요.
