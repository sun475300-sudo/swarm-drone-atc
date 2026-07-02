# 🇰🇷 국내 KS 표준 제안서 — UAS 군집 충돌 해결 시험 방법 (Phase 471)

*ODYSSEY Track 🏛 Standards & Policy — Phase 471 산출물*
*Created: 2026-06-25 · KSA (한국표준협회) 경유 제안 양식*
> **자매 산출물 (Phase 471 이중 트랙)**: 본 문서는 *제출용 산문 트랙*. 기계 검증 게이트 트랙은 [`KS_STANDARD_PROPOSAL_GATE.md`](KS_STANDARD_PROPOSAL_GATE.md) + `simulation/ks_standard_proposal.py` (결정적 준비도 판정·회귀 테스트 포함) — 두 트랙은 상보적이며 서로 대체하지 않는다.


> **정직성 공시**: 본 제안서는 SDACS 연구 산출물 기반 *KS X 표준 제안 초안* 이며, 실 KSA 제출은 사용자 환경(목포대 산학·KSA 회원 등록·표준위원회 참여)에 의존. 본 문서는 *기술 자산 정렬 + KS 제안 양식* 을 제공한다.

---

## 1. 제안 표준 정보

| 항목 | 내용 |
|---|---|
| **표준 번호 (제안)** | KS X UAS-CR-1 |
| **표준 제목** | 무인이동체 군집 충돌 해결 시험 방법 (UAS Swarm Conflict Resolution Test Method) |
| **국제 정합** | ASTM F3478-23 D&A · ISO 23629-5 UTM 구조 · EASA SORA OSO #07 |
| **분야** | 정보기술 → 정보처리 → 무인이동체 |
| **제안 기관** | 국립 목포대학교 드론기계공학과 (Mokpo National University) |
| **제안 일자** | 2026-06-25 (초안) |

---

## 2. 표준 개요 (Scope)

### 2.1 적용 범위

본 표준은 **2대 이상의 무인이동체** (드론·UAV·UAS) 가 동일 공역에서 운용될 때 발생하는 *충돌 위험* 을 **결정적·재현 가능한 시뮬레이션** 으로 평가하는 시험 방법을 정의한다.

### 2.2 적용 제외

- 단일 드론 비행 시험 (별도 표준)
- 실 비행 시험 (별도 표준 — 항공안전법 시행규칙)
- 인명 위협 평가 (별도 표준 — SORA Ground Risk)

---

## 3. 인용 표준 (Normative References)

- ISO/IEC 21384-1:2020 UAS 일반 사양
- ISO 23629-5:2023 UTM 기능 구조
- ISO 21895:2020 UAS 분류
- ASTM F3478-23 Detect & Avoid Type Certification
- 항공안전법 (법률 제20127호) 제129조 비행계획
- 항공안전법 시행규칙 제161조 비행제한구역

---

## 4. 용어 + 정의 (Terms and Definitions)

| 용어 | 정의 |
|---|---|
| **충돌 (Collision)** | 두 드론의 중심 간 거리 ≤ 5m |
| **근접 회피 실패 (Near Miss)** | 두 드론의 중심 간 거리 5~10m |
| **충돌 해결률** | `1 - collisions / (conflicts + collisions)` (출처: CLAUDE.md §8) |
| **CPA Lookahead** | Closest Point of Approach 예측 시간 (기본 90초) |
| **APF** | Artificial Potential Field — 인공 포텐셜 장 회피 |
| **CBS** | Conflict-Based Search — 다중 에이전트 경로 계획 |
| **NFZ** | No Fly Zone — 비행 금지 구역 |
| **결정적 의사난수** | `numpy.random.default_rng(seed)` 기반 — 재현 가능 |

---

## 5. 시험 절차 (Test Procedure)

### 5.1 시험 환경 요건

| 항목 | 요건 |
|---|---|
| 시뮬레이션 엔진 | SimPy 기반 결정적 이산 사건 시뮬레이션 (또는 동등) |
| 시드 | 5개 이상 (1·42·100·1337·9999) |
| 시간 해상도 | 10 Hz 이상 (드론 에이전트) + 1 Hz 컨트롤러 |
| 측정 시간 | 최소 60초 시뮬레이션 |
| 리포트 | JSON + 시각화 영상 |

### 5.2 시험 시나리오 (SDACS-SBS-10 채택)

| ID | 시나리오 | 통제 축 |
|:-:|---|---|
| B01 | 정면 충돌 (Head-On) | 직접 충돌 |
| B02 | 직각 교차 (Crossing) | 측면 충돌 |
| B03 | 추월 (Overtaking) | 후방 충돌 |
| B04 | 고밀도 (high_density) | 군집 밀도 |
| B05 | 대규모 이륙 (mass_takeoff) | 패드 밀집 |
| B06 | 다중 NFZ (multi_nfz) | 동적 NFZ |
| B07 | 통신 두절 (comms_loss) | 통신 장애 |
| B08 | 강풍 (wind_high) | 환경 외란 |
| B09 | 적대적 침입 (adversarial_intrusion) | 보안 위협 |
| B10 | 공칭 기준선 (nominal_baseline) | 대조군 |

각 시나리오는 5 시드 × 시뮬 60초 = **50 trial / 시나리오** 측정.

### 5.3 측정 지표

| 지표 | 단위 | 합격 기준 |
|---|:-:|---:|
| **충돌 해결률** | % | ≥ 95% (N ≤ 100) · ≥ 90% (N ≥ 500) |
| **최소 분리 거리** | m | ≥ 10m |
| **APF 활성 지연** | ms | p95 ≤ 100ms |
| **CBS 재계획 빈도** | events/min | ≤ 60 |
| **NFZ 위반** | count | = 0 |

---

## 6. 시험 보고서 양식 (Test Report Template)

```
시험 보고서 — KS X UAS-CR-1
시험 일자: YYYY-MM-DD
시험 기관: <기관명>
시험자: <이름·자격>

시험 환경:
- 시뮬레이션 엔진: <엔진명·버전>
- 시드: [1, 42, 100, 1337, 9999]
- 시간 해상도: 10 Hz
- 측정 시간: 60초

시나리오별 결과:
[표: B01-B10 × 5 지표]

합격 여부: PASS / FAIL
미달 항목: <리스트>
개선 권고: <리스트>

서명: <시험자> + <감리자>
```

---

## 7. SDACS 참조 구현

본 표준의 *참조 구현* 으로 SDACS (MIT 라이센스) 가 제공된다:

```bash
# 본 표준 시험 자동화
git clone https://github.com/sun475300-sudo/swarm-drone-atc.git
cd swarm-drone-atc

# 시뮬레이션 (B01-B10 × 5 시드)
python main.py scenario B01 --seed 42 --duration 60
# ... (B02-B10 반복)

# 또는 표준 시나리오 도구 (Phase 465)
python -m simulation.standard_scenarios --validate

# 결과 JSON 출력
python -m simulation.standard_scenarios --manifest > test_report.json
```

본 도구의 출처: `simulation/standard_scenarios.py` (SDACS-SBS-10) + `simulation/policy_impact.py` (정책 영향 비교).

---

## 8. 제안 일정 (Submission Roadmap)

| 단계 | 시기 | 결과물 |
|---|---|---|
| 1. KSA 회원 등록 | 2026-Q4 | KSA 학술 회원 |
| 2. 정보기술 분과위원회 (TC X) 문의 | 2026-Q4 | 본 제안서 회람 |
| 3. 표준 초안 워킹그룹 | 2027-Q1 | KS X UAS-CR-1 초안 |
| 4. 산업 협의 (KAIA·드론산업협회) | 2027-Q2 | 의견 수렴 |
| 5. 공청회 | 2027-Q3 | 시민·전문가 의견 |
| 6. KS X 표준 채택 | 2027-Q4 | 정식 KS 표준 |
| 7. ISO 기고 (Phase 462 정합) | 2028-Q1+ | ISO/TC 20/SC 16 |

**제약**: KSA 회원 등록·표준위원회 참여·공청회 개최는 사용자 환경(목포대 산학·KSA 등록비) 의존.

---

## 9. 부속 자료 (Attachments)

본 제안 제출 시 동봉:

1. **SDACS 5계층 안전망 백서** (Phase 464)
2. **SDACS-SBS-10 표준 시나리오 사양** (Phase 465)
3. **본 시험 방법의 SDACS 자동화 사례** (`simulation/standard_scenarios.py`)
4. **회귀 검증 결과** (5,500+ pass / 0 fail)
5. **MIT 라이센스 확인서** (`LICENSE`)

---

## 10. 한계 (정직성 공시)

- 본 제안서는 *학술 연구 산출물 기반 KS 표준 초안* 이며 KSA 정식 제출은 사용자 환경 의존.
- 표준 채택 결정은 KSA 정보기술 분과위원회 의결.
- 실 비행 시험·인적 요인·환경 요인은 본 표준 범위 외.
- SDACS 참조 구현은 *권고* 이며 다른 도구로도 본 표준 충족 가능.

---

## 11. 참조

- `docs/standards/SDACS_BENCHMARK_SUITE.md` — Phase 465 SDACS-SBS-10
- `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` — Phase 464 5계층 백서
- `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` — Phase 461 ASTM F38 (자매)
- `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md` — Phase 462 ISO/TC 20/SC 16
- `docs/standards/SDACS_KDRONE_POLICY_PROPOSAL.md` — Phase 463 K-드론 정책
- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470 종합 대시보드
- KSA (한국표준협회): <https://www.ksa.or.kr> (외부)
- KAIA (한국무인항공기협회): <https://kaia.or.kr> (외부)
- ISO/TC 20/SC 16: <https://www.iso.org/committee/5336224.html> (외부)
