# 🌐 국제 워킹그룹 의견서 — ICAO RPAS Panel (Phase 472)

*ODYSSEY Track 🏛 Standards & Policy — Phase 472 산출물*
*Created: 2026-06-25 · ICAO RPASP (Remotely Piloted Aircraft Systems Panel) 의견서 형식*

> **정직성 공시**: 본 의견서는 SDACS 연구 산출물 기반 *ICAO RPASP 회의 의견서 초안* 이며, 실 ICAO 제출은 한국 정부 대표단 (국토교통부 항공정책실) 또는 IFALPA·CANSO 등 국제 산업 협회 경유 필요. 본 문서는 *기술 자산 정렬 + 의견서 양식* 을 제공한다.

---

## 1. 의견서 정보

| 항목 | 내용 |
|---|---|
| **회의** | ICAO RPASP (Remotely Piloted Aircraft Systems Panel) |
| **세션** | 차기 정기 회의 (Twenty-First Meeting 추정) |
| **의제** | Detect & Avoid (DAA) for RPAS in Non-Segregated Airspace |
| **제출자** | 국립 목포대학교 드론기계공학과 (Republic of Korea) |
| **카테고리** | Working Paper / Information Paper |
| **제출 일자** | 2026-XX-XX (회의 1개월 전) |

---

## 2. 요약 (Summary)

본 의견서는 **결정적 시뮬레이션** 기반 **5계층 안전망**(APF + CBS + CPA 90s lookahead + ATC + UTM) 의 RPAS Detect & Avoid (DAA) 적용 사례 + 표준화 권고를 제시한다. SDACS (Swarm Drone Airspace Control System) 의 200+ phase 통합 자산을 기반으로, 군집(2-1,000+ 드론) 환경에서 **충돌 해결률 95.9%** (100 드론 기준), **드로우콜 불변 + CPU 4.1× scaling** (1K→5K 드론) 의 실측 결과를 보고한다.

---

## 3. 행동 권고 (Action Required)

RPASP 가 다음을 *고려* 할 것을 요청한다:

1. **DAA 시험 방법 표준화**: ASTM F3478 + ISO 23629-5 + 본 의견서의 SDACS-SBS-10 (10종 표준 시나리오) 통합.
2. **결정적 시뮬레이션 의무화**: 시드 + 소프트 버전 + 시나리오 hash 명시 — 재현 가능성 보장.
3. **5계층 안전망 권고**: 단일 솔루션 (APF only 또는 CPA only) 의 silent breakage 위험 명시.
4. **공개 참조 구현**: SDACS (MIT 라이센스) 와 같은 공개 자산을 회원국·산업체에 공유.

---

## 4. 배경 (Background)

### 4.1 현 RPAS DAA 의 격차

| 격차 | 영향 |
|---|---|
| 시험 방법 표준 부재 | 시드·시나리오·소프트 버전 차이로 평가 결과 비교 불가 |
| 군집 환경 미정의 | 단일 RPAS 기준만 정의, 2+ 다중 RPAS 환경 미규정 |
| 결정성 부족 | 사고 조사 시 *재현* 곤란 |
| 5계층 통합 모델 부재 | 단일 솔루션 인증 위주, 통합 안전망 미정의 |

### 4.2 SDACS 가 제시하는 해법

본 의견서는 **목포대 캡스톤 (2026)** 산출물 SDACS 를 *공개 참조 구현* 으로 제시한다. SDACS 는:

- **5계층 안전망**: APF (10Hz) + CBS (이벤트) + CPA (1Hz 90s lookahead) + ATC + UTM Federation
- **결정적 시뮬레이션**: `numpy.random.default_rng(seed)` 기반 — 시드 + 시나리오 hash + 소프트 버전 명시
- **공개 표준 시나리오**: SDACS-SBS-10 (10 통제 축 상호 배타) — Phase 465
- **MIT 라이센스**: 회원국·산업체 자유 사용·수정·재배포

---

## 5. 기술 상세 (Discussion)

### 5.1 5계층 안전망 (Defense in Depth)

| 층 | 명칭 | 주기 | 책임 |
|:-:|---|:-:|---|
| L1 | APF | 10 Hz | 즉시 회피 (반응형) |
| L2 | CBS | 이벤트 | 다중 에이전트 경로 재계획 |
| L3 | CPA | 1 Hz (90s lookahead) | 선제 충돌 예측 + advisory |
| L4 | ATC | 1 Hz | 인간 관제 명령 + 우선순위 |
| L5 | UTM | 이벤트 | 공역 인가·NOTAM·NFZ |

**우선순위 (Lexicographic)**: L5 (UTM) > L4 (ATC) > L3 (CPA) > L2 (CBS) > L1 (APF)

상세: `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` (Phase 464).

### 5.2 결정적 시험 환경 (Deterministic Test Bed)

**문제**: 비결정적 시뮬레이션은 사고 재현·표준 비교를 곤란하게 한다.

**해법**:
```python
# 결정적 시드 (Python)
rng = np.random.default_rng(42)
# 모든 의사난수는 rng 에서 추출 — random.random() 금지
```

**효과**: 동일 시드 + 동일 소프트 버전 + 동일 시나리오 → 동일 결과 (bit-exact).

### 5.3 공개 표준 시나리오 (SDACS-SBS-10)

| ID | 시나리오 | 통제 축 |
|:-:|---|---|
| B01-B10 | (`docs/standards/SDACS_BENCHMARK_SUITE.md` 참조) | 밀도·장애·이륙·경로·통신·기상·침입·다지역·자율·기준선 |

10 통제 축 *상호 배타* → 한 시나리오는 한 차원만 검증.

### 5.4 측정 결과 (2026-06 기준선)

| 환경 | 측정 |
|---|---|
| 100 드론 (high_density, 시드 42) | resolution 95.9% · 45 collisions · 87 near misses |
| 1,000 드론 (mega_swarm_1k, 헤드리스 SwiftShader) | FPS 4.0 · cpuMs 2.40 · DC 677 (불변) · 100% visibleInstances |
| 5,000 드론 | FPS 3.0 · cpuMs 9.85 · DC 676 · 100% (CPU 4.1× scaling, **선형 이하**) |

상세: `docs/PERF_MEGA_SWARM.md` §2.

---

## 6. 표준화 권고 (Recommendation for Standardization)

### 6.1 단기 (2026-2027)

- ICAO Annex 13 사고 조사 표준에 *결정적 시뮬 재현* 절차 추가.
- ASTM F3478 (DAA Type Cert) + ISO 23629-5 (UTM) 의 군집 환경 확장.

### 6.2 중기 (2027-2029)

- ICAO Document (예: Doc 10019 RPAS Manual) 갱신 — 5계층 안전망 권고.
- 결정적 시험 방법 ICAO Annex 11 (ATS) 부속서 신설 검토.

### 6.3 장기 (2029+)

- AI/ML 통합 RPAS 인증 (EASA AI Roadmap 정렬, Phase 451 조사 참조).
- 글로벌 USS Interoperability (ASTM F3548-21 정렬, Phase 461 SDACS-TM-2 참조).

---

## 7. 한계 (Limitations)

본 의견서가 다루지 않는 것:

- **실 비행 데이터**: 본 SDACS 는 *시뮬레이션* 위주. 실 비행 검증은 다른 트랙.
- **인적 요인**: 조종사 피로·스트레스 모델링 외.
- **법적 책임**: 회원국 입법 의존.
- **상업적 USS**: 본 의견서는 *공개 참조 구현* (MIT) 만 다룸.

---

## 8. 결론 (Conclusion)

ICAO RPASP 가 본 의견서의 권고 4건을 *고려* 하고, SDACS (MIT 라이센스) 를 *공개 참조 구현* 으로 회원국·산업체에 공유할 것을 제안한다. 본 의견서는 한국 (대한민국 — Republic of Korea) 정부 대표단 또는 산업 협회 경유 정식 제출 가능하다.

---

## 9. 첨부 (Annex)

| Annex | 자료 | 위치 |
|---|---|---|
| A | SDACS 5계층 안전망 백서 | `docs/standards/SDACS_SWARM_SAFETY_WHITEPAPER.md` (Phase 464) |
| B | SDACS-SBS-10 표준 시나리오 | `docs/standards/SDACS_BENCHMARK_SUITE.md` (Phase 465) |
| C | 측정 결과 (mega_swarm) | `docs/PERF_MEGA_SWARM.md` |
| D | ASTM F38 기고 자매 문서 | `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` (Phase 461) |
| E | ISO/TC 20/SC 16 추적 | `docs/standards/SDACS_ISO_TC20_SC16_TRACKER.md` (Phase 462) |
| F | KS X UAS-CR-1 자매 KS 제안 | `docs/standards/SDACS_KS_PROPOSAL_UAS_CR.md` (Phase 471) |
| G | 라이센스 (MIT) | `LICENSE` |

---

## 10. 제출 절차 (Submission Path)

ICAO RPASP 직접 제출은 회원국 정부 대표단 또는 인가된 국제 협회 (IFALPA·CANSO·IAOPA 등) 경유 필요. 본 의견서의 제출 경로:

```
1. 국토교통부 항공정책실 항공교통과 (한국 정부 대표) 의견 조회
2. KAIA (한국무인항공기협회) 산업 협회 의견 통합
3. ICAO RPASP 차기 회의 (Working Paper 또는 Information Paper) 제출
4. 회의 후속 — Action Item 식별 + 후속 의견서
```

**제약**: 정부 대표단 협의·ICAO 회의 등록·여행은 사용자 환경 의존.

---

## 11. 참조

- ICAO RPASP: <https://www.icao.int/safety/ua/Pages/default.aspx> (외부)
- ICAO Doc 10019 RPAS Manual (외부)
- IFALPA (조종사 협회): <https://www.ifalpa.org> (외부)
- CANSO (ATS 협회): <https://canso.org> (외부)
- `docs/standards/SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md` — Phase 470 종합 대시보드
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
