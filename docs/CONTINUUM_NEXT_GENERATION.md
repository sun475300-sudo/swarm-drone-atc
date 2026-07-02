# 🔄 SDACS 차세대 트랙 공모·선정·이양 절차 (Phase 491-499)

*ODYSSEY Track ♾️ Continuum — Phase 491-499 통합 산출물*
*Created: 2026-06-25 · BDFL → 차세대 BDFL 권한 이양 절차*

> **목적**: SDACS Phase 500 Centennial 선언 (2026-06-25) 후, **2027년 차세대 기수 (목포대 2027학번 캡스톤 또는 외부 협력자)** 가 SDACS 신규 트랙을 주도하고, 궁극적으로 BDFL → Tri-Maintainer (Phase 487 Stage 2) 권한을 이양할 수 있는 절차를 정의한다.

---

## 1. 공모 (Phase 491)

### 1.1 공모 대상

- **국내**: 목포대 드론기계공학과 후속 캡스톤 팀 (2027학번~)·항공대·서울대 우주·KAIST 항공우주
- **국제**: SDACS GitHub 레포 contributor·MIT 라이센스 fork 사용자

### 1.2 공모 방법

```
1. GitHub Discussions 에 "Next Generation Track Call" 카테고리 생성
2. README + ROADMAP 에 공모 안내 추가
3. 학회 (KSAS·KIDA·항공우주학회) 발표 시 공모 안내
4. 본 문서 (Phase 491) 가 공식 공모 양식
```

### 1.3 공모 기간

| 기간 | 활동 |
|---|---|
| 2027-Q1 | 공모 시작 (3개월) |
| 2027-Q2 | 제안서 접수 마감 + 1차 심사 |
| 2027-Q3 | 2차 발표 심사 + 선정 |
| 2027-Q4 | 신규 트랙 launch + 권한 이양 시작 |

---

## 2. 제안서 요건

### 2.1 필수 항목

```
1. 제안자 정보 (개인·기관·연락처)
2. 신규 트랙 개요 (1 페이지)
3. 학술/산업 가치 (왜 SDACS 가 이 트랙에 적합한가?)
4. 기존 SDACS 자산과의 통합 계획
5. 12개월 마일스톤 (분기별)
6. 신규 phase 번호 (501-600 범위 권장)
7. 라이센스 호환성 (MIT 유지)
8. 기여자 행동 강령 동의
```

### 2.2 평가 기준

| 영역 | 만점 | 기준 |
|---|:-:|---|
| 학술 가치 | 25 | 신규성·재현성·인용 가능성 |
| SDACS 정합 | 25 | 기존 5계층 안전망·federation·표준 매트릭스 활용 |
| 실행 가능성 | 20 | 12개월 내 완료 가능성·인적 자원 |
| 거버넌스 적합 | 15 | Phase 487 승계 규약 준수 의지 |
| 개방성 | 15 | MIT 유지·공개 협력 |

**선정 기준**: 70점 이상 + 위원회 (BDFL + Steward 2명) 만장일치.

---

## 3. 선정 후 인계 (Phase 492-498)

### 3.1 Phase 492 — 기술 인계 (3개월)

- 선정자에게 GitHub 협업자 (Steward 권한) 부여
- SDACS 아키텍처 워크스루 (4 영역: 시뮬·controller·federation·시각화)
- 결정적 시뮬레이션 + 5계층 안전망 원칙 교육
- CLAUDE.md 개발 원칙 동의

### 3.2 Phase 493 — 신규 트랙 launch (3개월)

- 선정 트랙의 Phase 번호 할당 (예: 501-550)
- 신규 트랙 plan 문서 작성 (`docs/SIMULATOR_<NEW_TRACK>_PLAN.md`)
- 첫 phase 구현 + PR + 회귀 (BDFL 검토)
- ROADMAP·CHANGELOG 통합

### 3.3 Phase 494 — 권한 점진 이양 (3개월)

- 선정자 PR 머지 권한 부여 (비-CRITICAL 변경)
- 보안 (CRITICAL/HIGH) 은 BDFL 단독 유지
- 분기 회의 (BDFL + 선정자) 진행

### 3.4 Phase 495 — Steward 정식 임명 (1개월)

- 선정자가 누적 PR 10+ + 12개월 활동 충족 시
- Phase 487 §4.2 선출 절차 발동
- Steward 권한 정식 부여

### 3.5 Phase 496 — 차세대 BDFL 후보 식별 (선택)

- 선정자 중 BDFL 후보 1명 (또는 다수) 식별
- 학술/거버넌스/기술 종합 평가
- 2028년 BDFL 권한 이양 후보

### 3.6 Phase 497 — 권한 이양 리허설 (6개월)

- BDFL 부재 시나리오 시뮬레이션 (24h·7d·30d)
- 차세대 BDFL 후보가 보안 응답·릴리스 절차 수행
- 회귀·CI·문서 갱신 일관성 검증

### 3.7 Phase 498 — BDFL 권한 이양 결정 (1개월)

- 위원회 의결 (Phase 487 §3 Stage 2 → Stage 3 전환)
- 공개 발표 + 인수인계 문서
- 키 관리 인계 (GPG·GitHub admin·Zenodo·PyPI/npm)

---

## 4. 미선정 제안에 대한 처우

선정 안 된 제안은:

1. **archive**: `docs/proposals/REJECTED_YYYY-QN_<name>.md` 에 보존 + 사유
2. **재제안 가능**: 다음 분기 공모에 보강 후 재신청 가능
3. **fork 권장**: MIT 라이센스 자유 사용 — 독립 fork 가능
4. **공개 회신**: GitHub Discussions 공개 답변 (개인정보 redacted)

---

## 5. Phase 499 — 차세대 시대 선언

신규 트랙 launch 완료 + 차세대 BDFL 정식 임명 시:

```
docs/CONTINUUM_NEW_ERA_DECLARATION.md (Phase 499) 신규 작성

- 본 시점 이후 SDACS 는 *2세대 BDFL* 의 주도하에 운영
- 1세대 (2026 메인테이너) 는 *명예 자문* 으로 전환
- 기존 Phase 1-500 자산은 *기준선* 으로 영구 보존
- 신규 Phase 501+ 는 차세대 결정
```

---

## 6. 제약 + 한계 (정직성 공시)

- 본 절차는 *제안 초안* 이며 실제 공모는 GitHub Discussions 활성화 + BDFL 운영 시간 의존.
- 차세대 BDFL 후보가 *없을 경우*: 본 문서는 *영원한 보존 모드* (Phase 490 디지털 유산) 로 전환.
- 외부 협력자 (대학 외부) 선정은 *학술 윤리* + *지적재산권* 검토 필요.
- 본 문서의 모든 일정은 *권고* 이며 실제 진행은 위원회 의결.

---

## 7. 참조

- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` (Phase 487) — 거버넌스 승계
- `docs/CONTINUUM_CENTENNIAL_DECLARATION.md` (Phase 500) — Centennial 선언
- `docs/CONTINUUM_DIGITAL_LEGACY.md` (Phase 490) — 디지털 유산
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track ♾️ — Phase 481-500
- `LICENSE` — MIT License (자유 fork)
- `CLAUDE.md` — 개발 원칙
