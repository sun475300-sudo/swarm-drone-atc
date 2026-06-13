# 📑 요구사항 추적 매트릭스 (RTM) — 5계층 안전망 (GENESIS Phase 306)

*Created: 2026-06-12 · 근거: SDACS Capstone Report v200·v6·v7, IROS 2026 §3 RELATED WORK*
*용도: 캡스톤 심사·인증 적합성 평가용 추적성 (DO-178C 갭 분석 — GENESIS 305 입력)*

> **요구사항(REQ) → 설계(DSN) → 구현(IMP) → 검증(VER)** 사슬 — 끊김 0건.

---

## 1. 5계층 안전망 정의 (재확인)

| 계층 | 이름 | 시간 단위 | 결정 단위 | 역할 |
|---|---|:-:|:-:|---|
| L1 | **APF** (Artificial Potential Field) | 10Hz | 개별 드론 | 가까운 장애물에 대한 즉시 척력 |
| L2 | **CBS** (Conflict-Based Search) | 0.1Hz | 다중 에이전트 | 사전 경로 충돌 해소 (MAPF) |
| L3 | **CPA** (Closest Point of Approach) | 1Hz | 쌍별 예측 | 90초 미래 충돌 시점 외삽 경보 |
| L4 | **ATC** (Air Traffic Controller) | 1Hz | 전역 관제 | 명령·우선순위·핸드오프 |
| L5 | **UTM** (Unmanned Traffic Management) | 0.1Hz | 전략적 | NFZ·회랑·Remote ID·LAANC |

## 2. 추적 매트릭스 (REQ ↔ DSN ↔ IMP ↔ VER)

### L1 — APF

| ID | REQ (요구) | DSN (설계) | IMP (구현) | VER (검증) |
|---|---|---|---|---|
| L1-R1 | 100m 이내 장애물 즉시 척력 | 인공 잠재력장 V(d) ∝ 1/d² | `simulation/swarm_simulator.py` `apf_avoidance()` · `swarm_3d_simulator.html` `apfCollisionAvoidance()` | 회귀 (pytest)·E2E |
| L1-R2 | 강풍 시 게인 자동 조정 | `APF_PARAMS_WINDY` 프리셋 (>10m/s 전환) | `src/airspace_control/apf_params.py` | unit + property `test_property_telemetry.py` |
| L1-R3 | 로컬 미니마 회복 | 회랑 유도 + `_conflictCooldown` + L2 폴백 | 위 동일 + corridorGroup | E2E ATC scenario |

### L2 — CBS

| ID | REQ | DSN | IMP | VER |
|---|---|---|---|---|
| L2-R1 | 다중 드론 경로 충돌 해소 | Conflict-Based Search (Sharon et al.) | `simulation/cbs_planner.py` | `tests/test_cbs_*.py` 회귀 |
| L2-R2 | 완전성 보장 (이산·유한) | MAPF 표준 정리 | 동일 | 비교 실험 (ORCA/VO 대비) |
| L2-R3 | 실시간 timebox | 200ms 컷오프 → L1 폴백 | controller `_cbs_attempts` 카운터 | 부하 테스트 100기 |

### L3 — CPA

| ID | REQ | DSN | IMP | VER |
|---|---|---|---|---|
| L3-R1 | 90초 lookahead 예측 | t* = -(Δp·Δv)/\|Δv\|² 해석해 | `swarm_3d_simulator.html` `CPA_LOOKAHEAD=12` 윈도우 + 외삽 | E2E TAC + property |
| L3-R2 | NEAR_MISS 거리 임계 | 8m → near_miss, <2m → collision | `NEAR_MISS_DIST` 상수 | 충돌 해결률 KPI |
| L3-R3 | 위험쌍 시각 마커 | `_cvLabelData` 풀 + 색상 단계 | `drawTopDown` Q2 (분석 뷰) | 시각 회귀 (스크린샷) |

### L4 — ATC

| ID | REQ | DSN | IMP | VER |
|---|---|---|---|---|
| L4-R1 | HOLD/RTB/REROUTE/ALT±/SPD±/TURN/CLEAR 명령 | 9종 명령 · 우선순위 | `_sdacs.atcCommand()` (production) | `test_simulator_production_core.py` 핵심 12종 |
| L4-R2 | 음성·시각 피드백 | TTS + 발광 링 + CSV 로그 | `_sdacs.setAtcAudio()` | E2E ATC |
| L4-R3 | 감사 로그 (불변) | CSV 추출 + 시간순 보존 | `_sdacs.atcLog` getter | production getter 회귀 |

### L5 — UTM

| ID | REQ | DSN | IMP | VER |
|---|---|---|---|---|
| L5-R1 | NFZ 지오펜스 (정적 + 동적) | 박스 + 원형 zone (만료시간) | `inNFZ()` + `_dynNfzList` + `injectDynamicNFZ()` | E2E + fuzz |
| L5-R2 | Remote ID 송출 | ASTM F3411 v2.0 | `src/utm/remote_id.py` | 회귀 (Python) |
| L5-R3 | LAANC 승인 인터페이스 | FAA LAANC 모델 | `src/utm/faa_laanc.py` | 회귀 (지연 분포 검증) |
| L5-R4 | 9층 고도 레이어 | `ALTITUDE_LAYERS` | `_sdacs.setLayer('altitude', on)` | E2E + layer toggle |
| L5-R5 | SORA 인증 평가 | JARUS 2.0 표 결정적 산정 | `_sdacs.soraAssess()` (GENESIS 302) | E2E 6건 + fuzz 20건 |

## 3. 횡단 요구사항 (Cross-cutting)

| ID | REQ | 처리 |
|---|---|---|
| X-R1 | 재현성 — 동일 시드 → 동일 결과 | `np.random.default_rng(seed)` 전역 · PYTHONHASHSEED=0 Docker · 18차 독립 재현 GREEN |
| X-R2 | 정직성 — 미구현 기능 명시 | maturity 4단계 분류 + Mock Detector + TECH_DEBT_LEDGER |
| X-R3 | 정합성 — 문서 ↔ 실측 | `extract_sdacs_api.py --check` CI 게이트 |
| X-R4 | 4 사본 동기화 | md5 일치 CI 게이트 |

## 4. 커버리지 요약

| 계층 | REQ 수 | 검증 충족 | 갭 |
|---|:-:|:-:|---|
| L1 APF | 3 | 3 (100%) | — |
| L2 CBS | 3 | 3 (100%) | — |
| L3 CPA | 3 | 3 (100%) | — |
| L4 ATC | 3 | 3 (100%) | — |
| L5 UTM | 5 | 5 (100%) | — |
| 횡단 | 4 | 4 (100%) | — |
| **합계** | **21** | **21 / 21** | **0** |

> 본 RTM은 sandbox-검증 가능한 범위에 한정. Sim-to-Real 실측(TRANSCENDENCE 261-280)·실 하드웨어 검증(Track A 실기)·실제 LAANC 응답(외부 API)은 사용자 환경 의존으로 분리 추적.

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 법령 12조항 매핑 (Phase 301)
- [`../SIMULATOR_GENESIS_PLAN.md`](../SIMULATOR_GENESIS_PLAN.md) — Track 🏭 인증 Phase 301-320
- [`../paper/latex/sections_4to7.tex`](../paper/latex/sections_4to7.tex) — IROS §4-§7 Ablation
- [`../TECH_DEBT_LEDGER.md`](../TECH_DEBT_LEDGER.md) — mock/speculative 공시 (GENESIS 388)
