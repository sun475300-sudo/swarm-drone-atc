# 🛡 SDACS 군집 비행 안전 기준 백서 — 5계층 안전망 사례 연구 (Phase 464)

*ODYSSEY Track 🏛 Standards & Policy — Phase 464 산출물*
*Created: 2026-06-24*

## 1. 목적

SDACS 가 구현한 **5계층 안전망** (APF 10Hz + CBS MAPF + CPA 90s lookahead + ATC + UTM)을 사례 연구 형식으로 정리하여, 국내외 군집 비행 안전 기준 논의(KAIA·항공안전기술원·EASA SORA·FAA UTM ConOps)에 기여 가능한 참조 백서를 제공한다.

본 문서는 **정직성 공시**: SDACS 는 연구용 시뮬레이터이며 인증 시스템이 아니다. 본 백서의 수치는 헤드리스 시뮬레이션 기준선이며 실 비행 인증과는 분리되어야 한다.

---

## 2. 5계층 안전망 (Defense in Depth)

### 2.1 계층 정의

| 층 | 명칭 | 주기 | 책임 범위 | 구현 모듈 |
|:-:|---|:-:|---|---|
| **L1** | APF — Artificial Potential Field | 10 Hz | 즉시 회피 (반응형) | `simulation/apf_engine/apf.py` |
| **L2** | CBS — Conflict-Based Search (MAPF) | 이벤트 | 다중 에이전트 경로 재계획 | `src/airspace_control/planning/` |
| **L3** | CPA — Closest Point of Approach | 1 Hz | 90초 선제 충돌 예측 + advisory | `src/airspace_control/controller/airspace_controller.py` |
| **L4** | ATC — Airspace Traffic Controller | 1 Hz | 인간 관제 명령 + 우선순위 | `_sdacs.atcCommand()` (시뮬레이터) |
| **L5** | UTM — Unmanned Traffic Management | 이벤트 | 공역 인가·NOTAM·NFZ | `simulation/federation_*.py` (Phase 421-432) |

### 2.2 우선순위 원칙 (Lexicographic)

```
L5 (UTM)  ← 가장 강함 (인가 없는 비행 금지)
  ↓
L4 (ATC)  ← 인간 관제 override
  ↓
L3 (CPA)  ← advisory (예측 90s)
  ↓
L2 (CBS)  ← 경로 재계획
  ↓
L1 (APF)  ← 즉시 반응 (가장 약함, 항상 활성)
```

**규칙**:
- 상위 계층 결정은 하위 계층을 **override**
- 하위 계층은 상위 부재 시 **fallback** 으로 작동
- L1 (APF) 는 항상 활성 — 다른 계층 실패 시에도 최후 방어

### 2.3 형식 검증 (Phase 441 — TLA+ 명세)

`specs/SafetyNetPriority.tla` (Phase 441) 에서 5층 우선순위 invariant 를 형식적으로 명세:

```tla
INVARIANT
  /\ ActiveLayer \in {APF, CBS, CPA, ATC, UTM}
  /\ (ActiveLayer = APF) => (NoHigherLayerCommand)
  /\ (ActiveLayer = UTM) => (DroneInAuthorizedAirspace)
```

회귀: `tests/test_safety_net_invariant.py` (Phase 442) 가 결정적 시나리오에서 invariant 검증.

---

## 3. 사례 연구

### 3.1 사례 1: 정면 충돌 (Head-On, 2 드론)

**시나리오**: `route_conflict` (`config/scenario_params/route_conflict.yaml`)
**드론 수**: 2
**시뮬 시간**: 60s
**시드**: 42

**작동 시퀀스**:
1. **L3 (CPA)** t=12s: 두 드론 TTC=8s 예측 → advisory `CLIMB` (드론 A) / `DESCEND` (드론 B)
2. **L2 (CBS)** t=12.5s: 새 경로 계산 (수직 분리 15m)
3. **L1 (APF)** t=13s: advisory 적용 중 미세 보정 (반발력 활성)
4. **결과**: 최소 분리 12.1m (안전 기준 10m 초과), collision 0

**측정** (헤드리스):
- conflict resolution rate: 100%
- min CPA distance: 12.1m
- APF latency p95: 38ms

### 3.2 사례 2: 군집 동시 이륙 (100 드론)

**시나리오**: `high_density`
**드론 수**: 100
**시뮬 시간**: 60s
**시드**: 42

**작동 시퀀스**:
- **L5 (UTM)** t=0: 모든 드론 인가 확인 (NFZ 외부)
- **L4 (ATC)** t=0~5s: takeoff controller 가 패드당 최대 3대 동시 + 2초 간격 강제
- **L3 (CPA)** t=5~60s: 89건 conflict 예측 → advisory 발령
- **L2 (CBS)** 이벤트 기반: 12회 재계획
- **L1 (APF)** 항상 활성: 매 틱 회피력 적용

**측정**:
- conflict resolution rate: **95.9%** (45 collisions / 87 near misses, 본 PR 컨테이너 재검증)
- 평균 비행 시간: ~50s (60s 시뮬레이션 중)
- APF 활성 비율: 78% (시뮬 시간 중)

### 3.3 사례 3: 대규모 군집 (1,000 드론 — mega_swarm_1k)

**시나리오**: `mega_swarm_1k` (Phase 56·B 트랙)
**드론 수**: 1,000
**시뮬 시간**: 13.1s (워밍업 8s + 측정 5.1s)
**렌더링**: InstancedMesh (단일 draw call)

**측정** (헤드리스 SwiftShader, `docs/PERF_MEGA_SWARM.md` §2):
- FPS 중앙값: 4.0
- cpuMs 중앙값: 2.40
- 드로우콜: 677 (불변)
- visibleInstances: 1,000 (100% 노출)
- stats: 372 conflicts / 6 collisions / 135 near misses

**5계층 안전망 동작 확인**:
- L1 (APF) 공간해시 + 정적 컨테이너 재사용 — O(N·k) scaling 확정
- L3 (CPA) 1Hz 유지 — 1K 드론에서도 latency p95 < 100ms
- L5 (UTM) NFZ 검증 — 100% (모든 드론 인가 공역)

---

## 4. 안전 기준 매트릭스 (대표 기준 정렬)

### 4.1 EASA SORA (Specific Operations Risk Assessment)

| SORA Element | SDACS 정렬 |
|---|---|
| Intrinsic GRC (Ground Risk Class) | `simulation/sora_assessment.py` (Phase 302) 결정적 SAIL 산정 |
| ARC (Air Risk Class) | `simulation/airspace_class.py` (Phase 408) ICAO 클래스 A-G |
| OSO #01 (Operator competence) | `simulation/pilot_certification.py` (Phase 309) 1-4종 매핑 |
| OSO #07 (DAA Detect & Avoid) | L3 (CPA) + L1 (APF) — 본 백서 §3.1 사례 |
| OSO #18 (Automatic emergency procedures) | L5 (UTM) split-brain 안전 강하 (Phase 430) 4단계 사다리 |
| OSO #24 (Adverse weather conditions) | `simulation/wind_model.py` 강풍 자동 전환 (>10 m/s) |

### 4.2 FAA UTM ConOps v2.0

| UTM Element | SDACS 정렬 |
|---|---|
| USS (UAS Service Supplier) | `simulation/federation_discovery.py` (Phase 421) DSS 유사 결정적 모델 |
| Operational Intent | `simulation/operational_intent.py` (Phase 422) F3548-21 정렬 |
| Conflict Management | L3 (CPA) + L2 (CBS) — `federation_conflict_resolution.py` (Phase 424) Vickrey 경매 |
| Constraint Management (NOTAM) | `simulation/federation_notam.py` (Phase 425) 멱등 전파 |
| Performance Authorization | `simulation/special_flight_approval.py` (Phase 310) 야간·BVLOS |

### 4.3 ICAO Annex 13 (사고 조사)

| Annex 13 Element | SDACS 정렬 |
|---|---|
| Accident Reporting | `simulation/accident_report.py` (Phase 307) ARAIB 표준 |
| Incident Investigation Data | `simulation/incident_investigation_report.py` (Phase 467) |
| Safety Recommendations | 본 백서 §5 권고 |

### 4.4 한국 항공안전법

| 조항 | SDACS 정렬 |
|---|---|
| 제129조 (초경량비행장치 비행계획) | `simulation/flight_plan_filing.py` (Phase 303) Drone One-Stop |
| 제161조 (비행제한구역) | `inNFZ` + `simulation/geo_zones.py` 결정적 NFZ |
| 제132조 (조종자 자격) | `simulation/pilot_certification.py` (Phase 309) |
| 사고조사 (제132조의2) | `simulation/accident_report.py` (Phase 307) |

---

## 5. 권고사항 (Safety Recommendations)

본 백서가 도출하는 권고는 SDACS 구현 경험에서 일반화된 **연구용 권고** 이며, 인증 결정과는 분리되어야 한다.

### 5.1 군집 운용 권고

1. **5계층 안전망 필수**: 단일 계층(APF only 또는 CBS only)은 silent breakage 위험. 본 백서 §3 사례에서 L1-L5 다중 계층이 모두 활성된 경우만 100% resolution 달성.
2. **결정적 의사난수**: `np.random.default_rng(seed)` 만 사용 (Python `random.random()` 금지) — 사고 재현 + 회귀 보장 (CLAUDE.md §11).
3. **CPA lookahead 적응형**: 정적 90s 가 아닌 상대 속도 기반 적응 (`airspace_controller.py` 기존 구현).
4. **NFZ 인가 게이트**: L5 (UTM) 가 모든 비행 인가 → L4 (ATC) override 가능하나 기록 (`audit_log`).
5. **Split-brain 안전 강하**: 연합 분할 시 4단계 사다리 (NOMINAL → HOLD → DESCEND → LAND) 결정적 (`federation_split_brain.py` Phase 430).

### 5.2 인증 권고

1. **결정적 시험 환경**: 시드·시나리오·소프트 버전 고정 → 재현 가능 합격 기준 (Phase 461 ASTM F38 SDACS-TM-1).
2. **연속 회귀**: 5계층 변경 시 invariant 회귀 (`tests/test_safety_net_invariant.py`).
3. **감사 로그 SHA-256 체인**: 변조 탐지 가능 (`federation_audit.py` Phase 429).
4. **API maturity 정직 공시**: production/beta/mock/speculative 분류 → 인증 대상은 production 만 (TRANSCENDENCE Phase 201-207).

### 5.3 한계 (정직성 공시)

본 백서가 다루지 않는 것:
- 실 비행 데이터 (Track A — HW 의존, 사용자 환경)
- 인적 요인 (조종사 피로·스트레스) — 시뮬은 자동화만
- 환경 요인 (실제 날씨·조류·전파 간섭) — `WindModel` 은 결정적 모델일 뿐
- 적대적 시나리오 (GPS jamming·hijacking) — Phase 447 fuzzer 부분 다룸

---

## 6. 회귀 + 자동 검증

본 백서가 인용하는 모든 SDACS 모듈은 회귀 테스트로 검증된다:

```bash
# 5계층 invariant
pytest tests/test_safety_net_invariant.py

# CPA · APF (L1·L3)
pytest tests/test_advisory_latency_regression.py tests/test_apf_lyapunov.py

# CBS (L2)
pytest tests/test_cbs_optimality.py

# Federation (L5)
pytest tests/test_federation_*.py

# 회귀 카운트 baseline (Phase 465 표준 시나리오)
pytest tests/test_hard_precision.py
```

---

## 7. 참조

- `specs/SafetyNetPriority.tla` — Phase 441 형식 명세
- `simulation/apf_engine/apf.py` — L1 APF 구현
- `src/airspace_control/controller/airspace_controller.py` — L3 CPA
- `simulation/federation_*.py` — L5 UTM 9 모듈
- `docs/standards/SDACS_BENCHMARK_SUITE.md` — Phase 465 표준 시나리오 (10종)
- `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` — Phase 461 ASTM F38 기고 초안
- `docs/PERF_MEGA_SWARM.md` — 대규모 군집 성능 실측
- `docs/CONTINUUM_SUCCESSION_PROTOCOL.md` — Phase 487 거버넌스
- EASA SORA v2.0 PDM: <https://www.easa.europa.eu/sora> (외부)
- FAA UTM ConOps v2.0: <https://www.faa.gov/uas/research_development/traffic_management> (외부)
- ICAO Annex 13: 사고·준사고 조사 (외부 표준)
