# ♾️ SDACS 거버넌스 — 유지보수자 승계 규약 (Phase 487)

*ODYSSEY Track ♾️ Continuum — Phase 487 산출물*
*Created: 2026-06-24 · Target: 10년 지속 가능성*

## 1. 목적

SDACS 가 단일 유지보수자(BDFL — Benevolent Dictator For Life) 모델에서 **유지보수 위원회(Maintenance Committee)** 모델로 전환되는 절차와 거버넌스를 규정한다. **Phase 500 Centennial 선언** 의 전제 조건이다.

---

## 2. 현재 상태 (2026-06)

| 항목 | 현황 |
|---|---|
| 거버넌스 모델 | **BDFL** — 단일 유지보수자 (sun475300-sudo) |
| Pull Request 머지 권한 | BDFL 1인 |
| 릴리스 권한 | BDFL 1인 |
| 보안 응답 책임 | BDFL 1인 |
| 코드 리뷰 | (선택적) Claude Code AI 어드바이저 |
| 의사결정 기록 | `docs/MASTER_PLAN_2026H2.md` · ROADMAP.md · CHANGELOG.md |

---

## 3. 승계 단계 (3-Stage Transition)

### Stage 1 — BDFL+Steward (현재 → 2027-Q1 목표)

- **BDFL**: 모든 머지 권한 유지
- **Steward(s)** 1-2명 모집 — read+comment 권한, 보안 응답 백업
- 권한:
  - PR 검토 (LGTM/Approve)
  - Issue triage
  - 보안 신고 1차 응답 (BDFL 부재 시 24h 내)
- 자격: 누적 PR 5+ 머지, 6개월 이상 활동

### Stage 2 — Tri-Maintainer (2027-Q2 → 2028)

- **3명 유지보수자 위원회** (BDFL + Steward 2명)
- 머지 권한:
  - 비-CRITICAL 변경: **1 LGTM + CI green** 충분
  - CRITICAL/보안: **2 LGTM 필수**
  - API breaking: **만장일치**
- 분기별 비공개 회의 (decisions log → `docs/governance/MINUTES_YYYY-QN.md`)
- 릴리스 권한: 위원회 과반

### Stage 3 — Committee (2029+)

- **5명 위원회** + 학술 자문 1명 (목포대 / 학회 representative)
- BDFL 직함 폐지 → **Lead Maintainer** (rotating, 1년 임기)
- 분기 회의 + 의결 기록 공개 (개인정보 redacted)
- 거버넌스 위반 신고 + 조사 절차

---

## 4. 위원 자격 + 선출 절차

### 4.1 자격 (모든 Stage 공통)

| 항목 | 기준 |
|---|---|
| 코드 기여 | 누적 PR 머지 10+ |
| 활동 기간 | 12개월 이상 |
| 인지도 | community 추천 2명 (issue/PR 추적 가능) |
| 보안 | GPG 서명 키 등록 + 2FA 활성 |
| 다양성 | 기술 영역 (sim/UI/docs/CI) 다양성 권장 |

### 4.2 선출 절차

```
1. 추천 (issue 등록 — public)
2. 자격 검증 (현 위원회, 1주)
3. Community RFC 의견 수렴 (2주, GitHub Discussion)
4. 위원회 의결 (2/3 찬성)
5. 권한 부여 + 공개 발표 (CHANGELOG)
```

### 4.3 해임/사임

- 사임: 본인 issue 등록 → 즉시 권한 회수
- 해임: 6개월 비활동 / 거버넌스 위반 / 보안 사고
- 해임 의결: 위원회 만장일치 (당사자 제외)

---

## 5. 의사결정 규칙

### 5.1 머지 권한 매트릭스

| 변경 유형 | 필요 승인 | CI 게이트 |
|---|:-:|---|
| 문서 (`.md`) | 1 LGTM | docs-only 게이트 |
| 코드 (비-CRITICAL) | 1 LGTM | 전체 CI green |
| 보안 (CSP·JWT·hooks 등) | 2 LGTM | + 보안 리뷰어 검토 |
| API breaking | 만장일치 | + Deprecation 정책 적용 |
| 릴리스 (semver bump) | 위원회 과반 | + CHANGELOG 갱신 |

### 5.2 의사결정 우선순위

1. **사용자 안전** (5계층 안전망 보존)
2. **데이터 무결성** (감사 로그·SHA-256 체인)
3. **재현성** (`np.random.default_rng(seed)` 원칙)
4. **호환성** (`docs/API_DEPRECATION_POLICY.md`)
5. **단순함** (CLAUDE.md §2 — 시니어가 과하다고 하면 단순화)

---

## 6. 비상 절차 (Stage 1·2 공통)

### 6.1 BDFL/Lead Maintainer 부재

- **24시간 부재**: Steward 가 보안 응답·CRITICAL 머지 권한 임시 행사
- **30일 부재**: Steward 가 정기 점검·릴리스 권한 행사
- **90일 부재**: Stage 전환 자동 발동 (Committee 의결)

### 6.2 키 관리

| 키 | 보유자 | 백업 |
|---|---|---|
| GPG 서명 키 | BDFL/Lead | 위원회 1명 (sealed envelope) |
| GitHub admin | BDFL/Lead | (Stage 2+) 위원장 |
| PyPI publish | BDFL/Lead | (Stage 3) 위원회 2명 |
| npm publish | BDFL/Lead | (Stage 3) 위원회 2명 |

---

## 7. 충돌 해결

- **기술 의견 충돌**: 위원회 토론 → 1주 cooldown → 재투표
- **개인 갈등**: 외부 중재자 (학술 자문)
- **법적 분쟁**: 변호사 자문 (라이센스 MIT 보호)

---

## 8. 라이센스/IP

- 모든 기여는 **MIT License** (LICENSE) 하에 공개
- 기여자는 PR 시 DCO (Developer Certificate of Origin) sign-off 필수: `git commit -s`
- 외부 기여 (3rd party) 의 호환 라이센스: MIT/BSD/Apache-2.0 만 수용

---

## 9. 본 문서 갱신

- Stage 전환 시 의무 갱신
- 분기별 review (단순한 노화 방지)
- 갱신 의결: 위원회 과반

---

## 10. 참조

- `docs/MASTER_PLAN_2026H2.md` — 2026 H2 실행 일정 (BDFL 단계)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track ♾️ — Phase 481-500 Continuum
- `docs/API_DEPRECATION_POLICY.md` — API 호환성 보존 정책 (Phase 209)
- `docs/MAINTENANCE_MINIMAL_MODE.md` — 1인 유지보수 핵심 워크플로 (Phase 389)
- `LICENSE` — MIT License
