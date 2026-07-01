# 🏛 SDACS ASTM F38 위원회 기고 초안 (Phase 461)

*ODYSSEY Track 🏛 Standards & Policy — Phase 461 산출물*
*Created: 2026-06-24*

## 1. 배경

ASTM International **F38 (Unmanned Aircraft Systems)** 위원회는 UAS 운영·인증·시험 방법의 국제 표준을 제정한다. 본 문서는 SDACS 가 구축한 **결정적 시뮬레이션·연합 운영·CPA 충돌 예측·APF 회피·CBS 다중 에이전트 경로** 자산을 기반으로 F38 위원회에 제안 가능한 **군집 관제 시험 방법** 초안을 제시한다.

### F38 핵심 표준 (SDACS 정렬)

| 표준 ID | 제목 | SDACS 정렬 자산 |
|---|---|---|
| **F3548-21** | UAS Service Supplier (USS) Interoperability | `simulation/operational_intent.py` · `simulation/federation_discovery.py` · `simulation/federation_handover.py` |
| **F3411-22** | Remote ID and Tracking | `_sdacs.dni` API · 텔레메트리 스키마 (`docs/schemas/telemetry.schema.json`) |
| **F3322-22** | Parachute System Performance (sUAS) | `simulation/safety_net_invariant.py` (안전망 invariant) |
| **F3196-22** | Seeking Approval for Operations Beyond VLOS | `simulation/special_flight_approval.py` (Phase 310) |
| **F3478-23** | Type Certification of Components (Detect & Avoid) | `apf_engine/apf.py` + CPA `airspace_controller.py` |

---

## 2. 제안 시험 방법 (SDACS-TM-1: Swarm Conflict Resolution)

### 2.1 목적
N개 드론 군집의 **충돌 해결률** 및 **분리 성능** 을 결정적 시나리오에서 측정한다.

### 2.2 시험 절차
```
Step 1: 시나리오 셋업
  - N = {10, 50, 100, 500, 1000, 5000}
  - 시드 ∈ {1, 42, 100, 1337, 9999}
  - 시나리오: route_conflict / mass_takeoff / mega_swarm_1k / 5k
  - 결정적 의사난수 (np.random.default_rng(seed))

Step 2: 측정 지표
  - conflict resolution rate = 1 - collisions / (conflicts + collisions)
  - separation maintained (min CPA distance)
  - APF activation latency (ms)
  - CBS replan rate (events / sim_time)

Step 3: 합격 기준
  - resolution rate ≥ 95% (N ≤ 100)
  - resolution rate ≥ 90% (N ≥ 500)
  - min CPA distance ≥ 10m (안전 분리)
  - APF latency p95 ≤ 100ms

Step 4: 검증 산출물
  - JSON 결과 (`results/astm_f38_swarm_tm1_*.json`)
  - PNG 시각화 (충돌 시계열)
  - 재현 명령 (`python main.py scenario <name> --seed <s> --drones <N>`)
```

### 2.3 SDACS 실증 데이터 (2026-06 기준선)

| N | 시드 | resolution rate | min CPA | APF latency p95 |
|:-:|:-:|---:|---:|---:|
| 10  | 42 | 100% | 24.7m | 8ms |
| 100 | 42 | 95.9% (45 collisions / 87 near) | 12.1m | 38ms |
| 1000 (mega_swarm_1k, 헤드리스) | 42 | (측정 보류 — `docs/PERF_MEGA_SWARM.md`) | — | cpuMs 2.4 |

---

## 3. 제안 시험 방법 (SDACS-TM-2: USS Federation Interoperability)

### 3.1 목적
ASTM F3548-21 USS 상호운용성을 **2-인스턴스 연합** 시나리오에서 검증한다.

### 3.2 시험 절차
```
Step 1: 두 인스턴스 셋업 (A, B)
  - 인접 공역 (overlapping)
  - 각자 100 드론 + 운영 의도 (Phase 422)

Step 2: 상호운용 동작 검증
  - 디스커버리 (Phase 421): A 가 B 의 4D 볼륨 식별
  - 핸드오버 (Phase 423): 경계 교차 드론 RETAINED → ACQUIRED
  - 충돌 해소 (Phase 424): 동시 의도 충돌 시 Vickrey 경매
  - NOTAM 전파 (Phase 425): A 의 NFZ 변경이 B 에 결정적 브로드캐스트
  - HLC 인과 순서 (Phase 431): 메시지 순서 일관성
  - Split-brain 강하 (Phase 430): 연결 끊김 시 안전 LAND

Step 3: 합격 기준
  - 핸드오버 결정 일관성 ≥ 99%
  - NOTAM 전파 멱등성 (중복 호출 → 동일 결과)
  - 감사 로그 (Phase 429) SHA-256 체인 무결성
  - split-brain 시 HOLD/DESCEND/LAND 사다리 결정적
```

### 3.3 SDACS 실증 자산

| 표준 요건 | SDACS 모듈 | 회귀 테스트 | 자산 |
|---|---|---|---|
| 4D 볼륨 교환 | `simulation/operational_intent.py` | `tests/test_operational_intent.py` (24건) | F3548-21 ASTM frozen dataclass |
| 디스커버리 | `simulation/federation_discovery.py` | `tests/test_federation_discovery.py` (13건) | 4D 그리드 셀 인덱스 |
| 핸드오버 | `simulation/federation_handover.py` | `tests/test_federation_handover.py` (16건) | 이력현상 hysteresis |
| 충돌 해소 | `simulation/federation_conflict_resolution.py` | `tests/test_federation_conflict_resolution.py` (11건) | Vickrey 2위 가격제 + sha256 분리 |
| NOTAM 전파 | `simulation/federation_notam.py` | `tests/test_federation_notam.py` (19건) | DELIVERED/DUPLICATE/REVOKED 멱등 |
| 감사 로그 | `simulation/federation_audit.py` | `tests/test_federation_audit.py` (29건) | SHA-256 해시 체인 변조 탐지 |
| HLC | `simulation/federation_hybrid_clock.py` | `tests/test_federation_hybrid_clock.py` | 전역 인과 순서 |
| Split-brain | `simulation/federation_split_brain.py` | `tests/test_federation_split_brain.py` (20건) | 4단계 안전 사다리 |

---

## 4. 제안 시험 방법 (SDACS-TM-3: Detect & Avoid Performance)

### 4.1 목적
ASTM F3478-23 (Detect & Avoid Type Certification) 정합 시험 — CPA 90s lookahead + APF 회피 성능 측정.

### 4.2 시험 절차
```
Step 1: 시나리오
  - head-on collision (정면)
  - crossing (직각 교차)
  - overtaking (추월)
  - climb conflict (수직 분리)

Step 2: 측정
  - CPA 예측 정확도 (TTC < 90s 알림 발령)
  - APF 회피 활성 시각 ≤ TTC - 10s
  - 회피 후 최소 분리 ≥ 10m

Step 3: 합격 기준
  - CPA 알림 정확도 ≥ 99% (false positive ≤ 5%)
  - APF 회피 활성 시각 ≤ TTC - 10s (95%ile)
  - 최소 분리 위반 0 (시드 5× 시나리오 4× = 20 trial)
```

---

## 5. 기고 일정 (제안)

| 단계 | 시기 | 결과물 |
|---|---|---|
| 1. 위원회 회원 등록 | 2026-Q3 | ASTM 멤버십 (학생/학술) |
| 2. SDACS-TM-1 초안 회람 | 2026-Q4 | F38 분과 메일링 리스트 |
| 3. 워킹그룹 발표 (online/F38 회의) | 2027-Q1 | 슬라이드 + 데모 |
| 4. WK (Work Item) 등록 | 2027-Q2 | 정식 표준 작업 항목 |
| 5. 표준 초안 제출 | 2027-Q4 | F3xxx-27 초안 |

**제약**: ASTM 멤버십·회의 참석은 사용자 환경 의존. 본 문서는 *기술 자산 정렬·기고 가능성* 의 기준선이다.

---

## 6. 참조

- `simulation/operational_intent.py` — F3548-21 정렬 frozen dataclass
- `simulation/federation_*.py` — 9 federation 모듈 (Phase 421-432)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480 표준·정책
- `docs/certification/RTM_5LAYER_COVERAGE.md` — 5계층 안전망 매트릭스
- ASTM F38 위원회 사이트: <https://www.astm.org/committee-f38> (외부 등록 필요)
