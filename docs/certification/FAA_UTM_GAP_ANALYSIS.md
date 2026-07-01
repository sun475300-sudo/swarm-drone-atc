# FAA UTM ConOps v2 USS 역할 요구사항 갭 분석 (ODYSSEY Phase 402)

*Created: 2026-06-20 · 근거: FAA UTM Concept of Operations v2.0 (2020), ASTM F3548-21 (USS Interoperability), 14 CFR Part 107/89*
*면책: 본 문서는 SDACS 시뮬레이터와 FAA UTM ConOps v2 USS 역할 요구사항 간 격차를 분석한 **개발자 참고 자료**이며, FAA 공식 USS 인증 심사를 갈음하지 않는다. 실 인증 시 FAA 최신 가이던스 및 ASTM 표준을 확인해야 한다.*

---

## 1. FAA UTM ConOps v2 개요

FAA UTM Concept of Operations v2 (2020)는 저고도 무인항공기(UAS) 교통 관리를 위한 연방 프레임워크다. UTM 생태계에서 USS(UAS Service Supplier)는 UAS 운영자와 FAA 시스템(FIMS) 사이의 중개자 역할을 수행한다.

### 1.1 USS 핵심 역할

| 역할 | 설명 |
|------|------|
| **등록 및 디스커버리** | UTM 생태계 등록, 타 USS/FIMS 디스커버리, 운영자 인증 |
| **비행 승인** | Operational Intent 수락, 비행 계획 제출(LAANC), 공역 제약 검증 |
| **텔레메트리** | 실시간 UAS 위치 수신, UTM 네트워크 보고, 데이터 아카이브 |
| **충돌 경고** | 잠재 충돌 탐지, 실시간 근접 경고 |
| **전략적 디컨플릭션** | 사전 비행 4D 볼륨 디컨플릭션, USS 간 협상, 우선순위 기반 순서 배정 |
| **적합성 감시** | 승인 운용 공역 적합성 감시, 비적합 시 비상 절차 |
| **데이터 교환** | USS 간 Operational Intent/위치 교환, NOTAM 발행/수신 |
| **네트워크** | FIMS 영구 연결, ASTM F3548 상호운용 |

---

## 2. 요구사항 x 충족도 매트릭스

| # | 요구사항 | 카테고리 | ConOps 참조 | SDACS 모듈 | 충족도 |
|:-:|----------|----------|-------------|-----------|:------:|
| USS-01 | UTM 생태계 등록 및 자격 유지 | Registration | §3.1 | `federation_discovery.py` | **Partial** |
| USS-02 | 타 USS/FIMS 디스커버리 지원 | Registration | §3.1.2 | `federation_discovery.py` | **Partial** |
| USS-03 | UAS 운영자 인증 및 조종사 자격 검증 | Registration | §3.1.3 | -- | **Gap** |
| USS-04 | Operational Intent 선언 수락 및 처리 | Flight Authorization | §4.1 | `operational_intent.py` | **Full** |
| USS-05 | 비행 계획 제출 및 LAANC 승인 | Flight Authorization | §4.2 | `flight_plan_filing.py` | **Partial** |
| USS-06 | 운용 공역 제약/TFR 검증 | Flight Authorization | §4.2.3 | `flight_plan_validator.py` | **Partial** |
| USS-07 | Part 107 waiver 요건 적용 (BVLOS/야간) | Flight Authorization | §4.3 | `airspace_controller.py` | **Partial** |
| USS-08 | 실시간 UAS 텔레메트리 수신 | Telemetry | §5.1 | `ws_bridge.py` | **Full** |
| USS-09 | UTM 네트워크 위치 보고 | Telemetry | §5.2 | `telemetry_recorder.py` | **Full** |
| USS-10 | 텔레메트리 데이터 아카이브 | Telemetry | §5.3 | `timescale.py` | **Full** |
| USS-11 | 잠재 충돌 탐지 및 경고 발행 | Conflict Advisory | §6.1 | `federation_conflict_resolution.py` | **Full** |
| USS-12 | 실시간 근접 경고 | Conflict Advisory | §6.2 | `apf_engine/apf.py` | **Full** |
| USS-13 | 사전 비행 전략적 디컨플릭션 | Strategic Deconfliction | §6.3 | `path_deconflict.py` | **Full** |
| USS-14 | USS 간 4D 볼륨 협상 | Strategic Deconfliction | §6.3.2 | `federation_conflict_resolution.py` | **Partial** |
| USS-15 | 우선순위 기반 혼잡 공역 순서 배정 | Strategic Deconfliction | §6.4 | `priority_queue.py` | **Full** |
| USS-16 | 승인 운용 공역 적합성 감시 | Conformance Monitoring | §7.1 | `compliance_checker.py` | **Full** |
| USS-17 | 비적합 시 비상 절차 트리거 | Conformance Monitoring | §7.2 | `federation_handover.py` | **Partial** |
| USS-18 | USS 간 Operational Intent/위치 교환 | Data Exchange | §8.1 | `operational_intent.py` | **Partial** |
| USS-19 | NOTAM 및 공역 제약 발행/수신 | Data Exchange | §8.2 | `federation_notam.py` | **Partial** |
| USS-20 | FIMS 영구 연결 유지 | Network | §9.1 | `federation_mesh.py` | **Partial** |
| USS-21 | ASTM F3548 USS-USS 상호운용 준수 | Network | §9.2 | `federation_mesh.py` | **Partial** |

---

## 3. 갭 분석 요약

| 항목 | 수치 |
|------|:----:|
| 총 요구사항 | 21 |
| 완전 충족 (Full) | 9 |
| 부분 충족 (Partial) | 11 |
| 갭 (Gap) | 1 |
| 비해당 (N/A) | 0 |
| **충족률** | **69.05%** |

> **충족률 산정 공식**: (full + 0.5 * partial) / (total - not_applicable) * 100

### 3.1 카테고리별 현황

| 카테고리 | Full | Partial | Gap |
|----------|:----:|:-------:|:---:|
| Registration | 0 | 2 | 1 |
| Flight Authorization | 1 | 3 | 0 |
| Telemetry | 3 | 0 | 0 |
| Conflict Advisory | 2 | 0 | 0 |
| Strategic Deconfliction | 2 | 1 | 0 |
| Conformance Monitoring | 1 | 1 | 0 |
| Data Exchange | 0 | 2 | 0 |
| Network | 0 | 2 | 0 |

### 3.2 강점 영역

- **텔레메트리**: 3/3 완전 충족 -- WebSocket 브리지, 텔레메트리 레코더, TimescaleDB 아카이브
- **충돌 경고**: 2/2 완전 충족 -- CPA 기반 충돌 탐지 + APF 실시간 회피
- **전략적 디컨플릭션**: 2/3 완전 충족 -- 4D 경로 디컨플릭션, 우선순위 큐

### 3.3 갭 항목

| 요구사항 | 설명 | 비고 |
|----------|------|------|
| USS-03 | UAS 운영자 인증 및 조종사 자격 검증 | 인증/자격 관리 모듈 신규 개발 필요 |

---

## 4. 갭 해소 로드맵

### Phase 1: 핵심 갭 해소 (단기)

| 우선순위 | 대상 | 조치 | 예상 산출물 |
|:--------:|------|------|-------------|
| P1 | USS-03 (운영자 인증) | 조종사 자격 검증 모듈 신규 개발 | `simulation/operator_auth.py` |
| P1 | USS-05 (LAANC) | LAANC API 연동 계층 추가 | `simulation/laanc_adapter.py` |

### Phase 2: 부분 충족 -> 완전 충족 (중기)

| 우선순위 | 대상 | 조치 | 예상 산출물 |
|:--------:|------|------|-------------|
| P2 | USS-01/02 (등록/디스커버리) | FAA FIMS 등록 프로토콜 구현 | `simulation/fims_registration.py` |
| P2 | USS-06 (TFR 검증) | FAA TFMS 실시간 TFR 수신기 추가 | `simulation/tfr_receiver.py` |
| P2 | USS-07 (Part 107) | Part 107 waiver 규정 검증 로직 강화 | 기존 모듈 확장 |
| P2 | USS-14 (4D 볼륨 협상) | 다자간 4D 볼륨 협상 프로토콜 완성 | 기존 모듈 확장 |
| P2 | USS-17 (비상 절차) | 비적합 탐지 시 자동 비상 절차 체인 강화 | 기존 모듈 확장 |

### Phase 3: 네트워크 및 데이터 교환 고도화 (장기)

| 우선순위 | 대상 | 조치 | 예상 산출물 |
|:--------:|------|------|-------------|
| P3 | USS-18 (USS-USS 데이터 교환) | ASTM F3548 완전 적합 위치 교환 프로토콜 | 기존 모듈 확장 |
| P3 | USS-19 (NOTAM) | FAA FNS(NOTAM) 형식 변환기 추가 | `simulation/fns_converter.py` |
| P3 | USS-20/21 (네트워크) | FAA FIMS 인터페이스 + F3548 적합성 시험 | 기존 모듈 확장 + 시험 하네스 |

---

## 5. 연관 문서

| 문서 | 위치 |
|------|------|
| EASA U-space 서비스 매핑 (Phase 401) | `simulation/uspace_service_map.py` |
| ICAO 공역 클래스 매핑 (Phase 408) | `simulation/airspace_class.py` |
| DO-178C 갭 분석 (Phase 305) | `docs/certification/DO178C_GAP_ANALYSIS.md` |
| Operational Intent 형식 (Phase 404) | `simulation/operational_intent.py` |
| FAA UTM 갭 분석 모듈 | `simulation/faa_utm_gap.py` |

---

## 6. CLI 사용법

```bash
# 전체 갭 분석 리포트
python -m simulation.faa_utm_gap --report

# 갭 항목만 출력
python -m simulation.faa_utm_gap --gaps

# JSON 형식 출력
python -m simulation.faa_utm_gap --json

# 카테고리별 필터
python -m simulation.faa_utm_gap --category "Strategic Deconfliction"
```
