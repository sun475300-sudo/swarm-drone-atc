# 🌐 국제 워킹그룹 의견서 — GUTMA Harmony Working Group (Phase 474)

*ODYSSEY Track 🏛 Standards & Policy — Phase 474 산출물*
*Created: 2026-06-25 · GUTMA (Global UTM Association) Harmony 의견서*

> **정직성 공시**: 본 의견서는 SDACS 연구 산출물 기반 *GUTMA 의견서 초안* 이며, 실 제출은 GUTMA 회원 자격(유료) + Harmony WG 활동 등록 필요. 본 문서는 *기술 자산 정렬 + 의견서 양식* 을 제공한다. Phase 472 ICAO RPASP 의견서의 자매 문서.

---

## 1. 의견서 정보

| 항목 | 내용 |
|---|---|
| **대상 기구** | GUTMA (Global UTM Association) — Harmony Working Group |
| **카테고리** | Position Paper / Reference Implementation |
| **제출자** | 국립 목포대학교 드론기계공학과 (Republic of Korea) |
| **제출 일자** | 2026-XX-XX (Harmony WG 차기 화상회의 1주 전) |
| **자매 문서** | `docs/standards/SDACS_ICAO_RPASP_OPINION.md` (Phase 472) |

---

## 2. 요약 (Executive Summary)

GUTMA Harmony Working Group 의 핵심 목표인 **글로벌 USS (UAS Service Supplier) 상호운용성** 에 SDACS 의 **연합 운영(Federation Operations) 9 모듈** + **결정적 시뮬레이션** + **5계층 안전망** 자산을 *공개 참조 구현* 으로 제시한다. ASTM F3548-21 정합 9 모듈(Phase 421-432)·1,000+ 드론 환경 검증(`mega_swarm_1k` FPS 4·DC 677·CPU 4.1× scaling)·MIT 라이센스.

---

## 3. 행동 권고 (Recommended Actions)

GUTMA Harmony WG 가 다음을 *고려* 할 것을 요청한다:

1. **USS 상호운용성 시험 자동화** — SDACS Federation 9 모듈(`simulation/federation_*.py`)을 Harmony WG 의 *참조 시험 환경* 으로 평가.
2. **결정적 시뮬 SLA** — 동일 시드 → 동일 결과 (bit-exact) 의무화 (사고 재현 보장).
3. **HLC (Hybrid Logical Clock) 표준화** — Phase 431 HLC 모듈을 USS 간 전역 인과 순서 표준 후보로 검토.
4. **Split-brain 안전 강하 4단계 사다리** — Phase 430 모듈을 연결 끊김 시 ConOps 표준으로 권고.
5. **감사 로그 SHA-256 해시 체인** — Phase 429 모듈을 USS 간 변조 탐지 표준 후보로 권고.

---

## 4. 배경 (Background)

### 4.1 GUTMA Harmony WG 현 상태

GUTMA Harmony WG 는 글로벌 USS 간 *기술적 일관성* + *운영 정렬* 을 목표로 한다. 주요 활동:

- USS-to-USS 통신 프로토콜 (ASTM F3548-21 정합)
- 운영 의도(Operational Intent) 표준 (ISO 23629-7 정합)
- 사고·준사고 데이터 교환 (ICAO Annex 13 정합)

### 4.2 현 격차

| 격차 | 영향 |
|---|---|
| 다중 USS 환경 결정적 시험 베드 부재 | 회원사별 평가 결과 비교 곤란 |
| 인스턴스 간 신뢰 모델 부재 | 비정상 USS 격리·강하 절차 미정의 |
| 글로벌 인과 순서 표준 부재 | 분산 환경 메시지 순서 일관성 보장 곤란 |
| Split-brain 강하 표준 부재 | 연결 끊김 시 임의 동작 가능 |

### 4.3 SDACS 가 제시하는 해법

SDACS Federation 9 모듈 (Phase 421-432) 는 위 격차에 대한 *공개 참조 구현*:

| Phase | 모듈 | GUTMA 격차 정합 |
|:-:|---|---|
| 421 | `federation_discovery.py` | 다중 USS 시험 베드 — ASTM F3548 DSS 결정적 모델 |
| 422 | `operational_intent.py` | ISO 23629-7 정합 frozen dataclass + 라운드트립 직렬화 |
| 423 | `federation_handover.py` | 핸드오버 결정 hysteresis + 감사 로그 |
| 424 | `federation_conflict_resolution.py` | Vickrey 2위 가격제 + sha256 결정 분리 |
| 425 | `federation_notam.py` | 멱등 NOTAM 전파 (DELIVERED/DUPLICATE/REVOKED) |
| 428 | `federation_trust.py` | Beta-Bernoulli 평판 모델 (Phase 608 재사용) |
| 429 | `federation_audit.py` | SHA-256 해시 체인 변조 탐지 + CRDT 병합 |
| 430 | `federation_split_brain.py` | 4단계 안전 사다리 (NOMINAL→HOLD→DESCEND→LAND) |
| 431 | `federation_hybrid_clock.py` | HLC 전역 인과 순서 |
| 432 | `federation_mesh.py` | 메시 토폴로지 + 멀티홉 전파 |

---

## 5. 기술 상세 (Technical Discussion)

### 5.1 Federation Discovery (Phase 421)

```python
# ASTM F3548-21 DSS 유사 결정적 모델
from simulation.federation_discovery import DiscoveryRegistry, Volume4D

registry = DiscoveryRegistry()
registry.register(uss_id="A", volume=Volume4D(...))
neighbors = registry.discover(query_volume=Volume4D(...))
# → 결정적 셀 인덱스 기반 정밀 교차
```

### 5.2 HLC Global Causal Order (Phase 431)

```python
# Hybrid Logical Clock — Lamport + 물리 시계 결합
from simulation.federation_hybrid_clock import HLC

clock_a = HLC(node_id="A")
clock_b = HLC(node_id="B")
ts1 = clock_a.send_event()
clock_b.receive_event(ts1)  # 자동 인과 순서 보존
# → 분산 환경에서 결정적 전역 순서
```

### 5.3 Split-Brain Safety Ladder (Phase 430)

```python
# 4단계 안전 사다리
from simulation.federation_split_brain import classify_partition

partition = classify_partition(connectivity_graph, threshold=0.5)
# → NOMINAL | HOLD | DESCEND | LAND (이력현상 적용)
```

---

## 6. 실측 결과 (Empirical Results)

| 환경 | 결과 |
|---|---|
| 100 드론 단일 USS | resolution 95.9% (45 collisions · 87 near misses) |
| 1,000 드론 (mega_swarm_1k) | FPS 4.0 · cpuMs 2.40 · DC 677 (불변) · 100% visibleInstances |
| 5,000 드론 | FPS 3.0 · cpuMs 9.85 · DC 676 — CPU 4.1× scaling (선형 이하) |
| Federation 9 모듈 회귀 | 197+ 건 PASS (인접 federation) |

상세: `docs/PERF_MEGA_SWARM.md` §2.

---

## 7. 표준화 권고 일정

| 시기 | 활동 |
|---|---|
| 2026-Q4 | GUTMA 회원 등록 + Harmony WG 참여 신청 |
| 2027-Q1 | 차기 Harmony WG 화상 회의 의견서 제출 |
| 2027-Q2 | GUTMA Harmony 행사 발표 (대면 또는 화상) |
| 2027-Q3 | WG 의견 통합 + 표준 초안 협력 |
| 2027-Q4 | GUTMA-recommended practice 등록 |

**제약**: GUTMA 회원 자격 + 회의 참석은 사용자 환경 (목포대 산학·해외 출장) 의존.

---

## 8. 한계 (Limitations)

- 본 의견서는 *학술 연구 산출물 기반 의견* 이며 실 운영 USS 인증 아님.
- 본 SDACS Federation 9 모듈은 *결정적 시뮬* 위주 — 실 USS 통합은 다른 트랙(Phase 426-427 사용자 HW 의존).
- GUTMA Harmony WG 의 최종 표준 채택은 GUTMA Board 의결.
- 본 의견서의 모든 권고는 *오픈 소스 참조 구현* 으로 GUTMA 회원사에 무상 제공 (MIT 라이센스).

---

## 9. 첨부 (Annex)

| Annex | 자료 | 위치 |
|---|---|---|
| A | Federation 9 모듈 코드 | `simulation/federation_*.py` (Phase 421-432) |
| B | Federation 회귀 197+ 건 | `tests/test_federation_*.py` |
| C | ASTM F38 기고 자매 문서 | `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` (Phase 461) |
| D | ICAO RPASP 의견서 자매 | `docs/standards/SDACS_ICAO_RPASP_OPINION.md` (Phase 472) |
| E | 5계층 안전망 백서 | `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` (Phase 464) |
| F | 라이센스 (MIT) | `LICENSE` |

---

## 10. 제출 절차

```
1. GUTMA 회원 등록 (https://gutma.org/membership/)
2. Harmony WG 활동 등록
3. 차기 Harmony WG 화상 회의 1주 전 의견서 제출
4. 회의 발표 (옵션) + Q&A
5. 후속 의견서 (Action Item 식별)
```

---

## 11. 참조

- GUTMA (Global UTM Association): <https://gutma.org/> (외부)
- GUTMA Harmony WG: <https://gutma.org/working-groups/> (외부)
- ASTM F3548-21 USS Interoperability (외부)
- ISO 23629-7 UTM 데이터 모델 (외부)
- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470 종합 대시보드
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
