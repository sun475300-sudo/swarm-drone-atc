# 🏭 항공안전법 · 드론활용촉진법 적합성 매트릭스 (GENESIS Phase 301)

*Created: 2026-06-12 · 근거 법령: 항공안전법(법률 제20183호, 2025-01-21 시행 기준) · 드론 활용의 촉진 및 기반조성에 관한 법률(법률 제19836호)*
*면책: 본 문서는 시뮬레이션 모듈과 법령 조항의 매핑을 정리한 **개발자 참고 자료**이며, 운영자의 법적 의무를 갈음하지 않는다. 실 운영 시 최신 개정판과 국토교통부 고시를 확인해야 한다.*

---

## 1. 매핑 매트릭스 (SDACS 기능 ↔ 법령 조항)

| 법령·조항 | 요구 사항 | SDACS 충족 모듈 | 성숙도 | 비고 |
|---|---|---|:-:|---|
| 항공안전법 §127 ① | 비행승인 — 관제권/비행제한구역 | `src/utm/airspace_reservation.py` + `_sdacs.injectDynamicNFZ()` | 🟢 production | NFZ 지오펜스 + 사전 승인 워크플로 |
| 항공안전법 §127 ② | 야간·비가시(BVLOS) 특별승인 | `_sdacs.soraAssess({bvlos:true})` → SAIL 산정 | 🟢 production | JARUS SORA 2.0 결정적 |
| 항공안전법 §129 ① | 조종자 준수사항 (충돌 회피) | 5계층 안전망 (APF·CBS·CPA·ATC·UTM) | 🟢 production | 자동 회피로 의무 충족 |
| 항공안전법 §129 ⑥ | 비행기록 보존(2년) | `src/storage/timescale.py` (30일 → 외부 백업) | 🔵 beta | TimescaleDB 보존정책 + 외부 아카이브 정책 필요 |
| 항공안전법 §131 | 자격증명 | GENESIS Phase 309 매핑 (계획) | ⬜ | 1~4종 ↔ 시뮬 교육 모드 |
| 항공안전법 §131의2 | 안전관리시스템(SMS) | `docs/hardware/fmea_report.md` (P700, 12 failure modes) | 🔵 beta | FMEA + 사고 보고 (GENESIS 307) |
| 드론활용촉진법 §6 | 드론산업기본계획 정렬 | K-드론시스템 고도화 정책 제안 (ODYSSEY 463 계획) | ⬜ | |
| 드론활용촉진법 §11 | 드론공역 지정·관리 | `airspace_reservation.py` + 9층 고도 레이어 | 🟢 production | |
| 드론활용촉진법 §15 | 안전기준 (SORA·SAIL) | `_sdacs.soraAssess()` (GENESIS 302) | 🟢 production | iGRC × ARC → SAIL I-VI |
| 드론활용촉진법 §16 | 보험 가입 | Phase 67 보험 mock → GENESIS 308 격상 계획 | 🟡 mock | 실 보험사 API 스펙화 필요 |
| 시행규칙 §306 | 비행계획 제출 (Drone One-Stop) | GENESIS Phase 303 (계획) | ⬜ | 신청서 export 자동화 |
| 시행규칙 §307 | Remote ID 방송 | `src/utm/remote_id.py` (P693 ASTM F3411 v2.0) | 🟢 production | 한국 RID 법규 정렬 |

## 2. 격차 분석 (Gap)

| 영역 | 현 상태 | 격차 | 격상 계획 |
|---|---|---|---|
| 보험 요율 산정 | mock 결정적 응답 | 실 보험사 데이터 미연동 | GENESIS 308 |
| 비행기록 2년 보존 | TimescaleDB 30일 + 외부 백업 정책 미정 | 장기 아카이브 운영 절차 부재 | GENESIS 345·390 |
| 자격증명 ↔ 교육 모드 | 교육 모드 미구현 | 자격증 요건 매핑 부재 | GENESIS 309·381 |
| 사고 보고 자동화 | 시뮬 로그는 있으나 항철위 양식 변환기 없음 | 양식 표준 변환기 부재 | GENESIS 307 |

## 3. 운영자 체크리스트 (요약)

운영 전:
- [ ] 운영 공역의 비행제한·관제권 확인 → `_sdacs.injectDynamicNFZ()` 또는 시나리오 NFZ 일치
- [ ] BVLOS·야간 운영 시 `soraAssess()` 실행 → 결과 SAIL 등급 ≤ 운영자 보유 인증
- [ ] Remote ID 송출 확인 (`src/utm/remote_id.py` 동작)
- [ ] 보험 증서 사본 (외부 절차)

운영 중:
- [ ] 5계층 안전망 활성 (`maturityReport().counts.production ≥ 90` 확인)
- [ ] 비행기록 수집 (TimescaleDB 또는 백업 파이프라인)

운영 후:
- [ ] 사고/준사고 발생 시 시뮬 로그 → 항철위 양식 변환 (Phase 307 도구 완성 시)
- [ ] 비행기록 2년 보존 정책 적용

## 🔗 관련
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 인증 Phase 301-320
- [`../track_f/p749_security_audit.md`](../track_f/p749_security_audit.md) — KISA CSAP 96항목
- [`../hardware/remote_id_broadcast.md`](../hardware/remote_id_broadcast.md) — Remote ID 송출 (P693)
- [`../SDACS_API.md`](../SDACS_API.md) — 407 API 라이브 실측 (`soraAssess` production)
