# 🌍 SDACS ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스 (Phase 462)

*ODYSSEY Track 🏛 Standards & Policy — Phase 462 산출물*
*Created: 2026-06-24*

## 1. 배경

**ISO/TC 20/SC 16 (Unmanned aircraft systems)** 는 무인항공기 시스템의 국제 표준(ISO 21384, 21895, 24355 등) 을 제정하는 ISO 분과위원회다. 본 문서는 SDACS 가 정합 또는 기여 가능한 ISO 표준을 **추적 매트릭스 + 격차 분석** 으로 정리한다.

---

## 2. 추적 매트릭스

### 2.1 ISO/TC 20/SC 16 핵심 표준 (UAS Operations)

| 표준 ID | 제목 | 상태 | SDACS 정렬 |
|---|---|:-:|---|
| **ISO 21384-1:2020** | UAS – Part 1: General specifications | 발간 | `simulation/simulator.py` SwarmSimulator + DRONE_PROFILES |
| **ISO 21384-2:2021** | UAS – Part 2: Product systems | 발간 | `src/airspace_control/agents/drone_profiles.py` |
| **ISO 21384-3:2023** | UAS – Part 3: Operational procedures | 발간 | `_sdacs.atcCommand()` · 5계층 안전망 |
| **ISO 21384-4:2024** | UAS – Part 4: Vocabulary | 발간 | `docs/INDEX.md` 용어집 |
| **ISO 21895:2020** | Categorization & classification of civil UAS | 발간 | `simulation/airspace_class.py` Phase 408 (A-G 클래스) |
| **ISO 23629-5:2023** | UAS Traffic Management (UTM) – Part 5: UTM functional structure | 발간 | `simulation/federation_*.py` (Phase 421-432) |
| **ISO 23629-7:2023** | UTM – Part 7: Data model for spatial data | 발간 | `simulation/operational_intent.py` (Phase 422) |
| **ISO 23629-8:2024** | UTM – Part 8: Remote pilot | 발간 | `simulation/pilot_certification.py` (Phase 309) |
| **ISO 23629-12:2024** | UTM – Part 12: Requirements for USS providers | 발간 | `api/fastapi_server.py` + JWT/RBAC (Phase 711) |
| **ISO 24355:2023** | Vertiports for UAS – General requirements | 발간 | `simulation/uam_vertiport.py` (UAM 트랙) |

### 2.2 작업 중 표준 (WD/CD/DIS)

| 표준 ID | 제목 | 상태 | SDACS 잠재 기여 |
|---|---|:-:|---|
| **ISO/CD 5491** | UAS – Geofencing | CD | `inNFZ` + `simulation/geo_zones.py` 결정적 NFZ |
| **ISO/CD 23665** | UAS – Operator personnel competence | CD | `simulation/pilot_certification.py` 1-4종 매핑 |
| **ISO/WD 5012** | UAS – Cybersecurity | WD | CSP 헤더 + JWT alg + WS 검증 (6차 점검) |
| **ISO/AWI 5413** | UAS – Reliability & FMEA | AWI | `tests/test_safety_net_invariant.py` (Phase 442) |
| **ISO/AWI 24356** | Vertiports – Operations | AWI | (보류) |

> 상태: WD (Working Draft) · CD (Committee Draft) · DIS (Draft International Standard) · AWI (Approved Work Item)

---

## 3. 격차 분석

### 3.1 강한 정합 (즉시 기여 가능)

| 표준 | SDACS 강점 |
|---|---|
| ISO 23629-5 UTM 구조 | Federation 9 모듈 + HLC + split-brain 사다리 — *참조 구현 후보* |
| ISO 23629-7 데이터 모델 | F3548-21 정렬 operational_intent + telemetry.schema.json (Phase 466) |
| ISO 21895 분류 | airspace_class.py A-G 결정적 매핑 (Phase 408) |
| ISO/CD 5491 Geofencing | inNFZ + geo_zones.py + Phase 322 (전남 도서) 실 좌표 |

### 3.2 부분 정합 (확장 필요)

| 표준 | SDACS 격차 |
|---|---|
| ISO 21384-3 운영 절차 | 5계층 안전망 정렬 OK / 다만 **실 비행 데이터** 부재 (Track A) |
| ISO 23629-8 원격 조종사 | pilot_certification.py 매핑 OK / 다만 **HITL 검증** 부재 (Track Phase 261-280) |
| ISO/CD 23665 인적 역량 | 매핑 정의 OK / **15주 커리큘럼** Phase 381-387 진척 필요 |

### 3.3 미정합 (외부 환경/장기)

| 표준 | 한계 |
|---|---|
| ISO 24355 Vertiports | 물리 인프라 표준 — SDACS 시뮬은 *논리* 만 정의 |
| ISO/AWI 5413 Reliability MTBF | 실 비행 시간 누적 데이터 필요 |

---

## 4. 추적 절차

### 4.1 분기별 갱신

```bash
# 분기마다 본 문서 갱신
# 1. ISO 사이트에서 TC 20/SC 16 작업항목 status 확인
# 2. 신규 표준(WD/CD/DIS) 발견 시 §2.2 추가
# 3. 발간 표준(WD → IS) 승격 시 §2.1 이동
# 4. SDACS 신규 모듈 추가 시 정렬 컬럼 갱신
```

### 4.2 정합 게이트

| 게이트 | 검증 방법 |
|---|---|
| ISO 23629-7 (UTM 데이터 모델) | `python -m pytest tests/test_operational_intent.py tests/test_telemetry_validator.py` |
| ISO 21895 (분류) | `python -m pytest tests/test_airspace_class.py` |
| ISO/CD 5491 (Geofencing) | `python -m pytest tests/test_geo_zones.py` |

---

## 5. 기고 우선순위 (제안)

| 우선 | 표준 | 기고 방식 | 시기 |
|:-:|---|---|---|
| 🥇 | ISO 23629-5 UTM 구조 | 참조 구현 (Federation 9 모듈 공개 코드) | 2026-Q4 |
| 🥈 | ISO 23629-7 UTM 데이터 모델 | telemetry.schema.json + operational_intent dataclass | 2027-Q1 |
| 🥉 | ISO/CD 5491 Geofencing | inNFZ + geo_zones.py 알고리즘 | 2027-Q2 |

**제약**: ISO 표준 기고는 한국공업표준협회(KSA) 경유 KS-X (산업통상자원부) 표준안 제출 후 ISO/TC 20/SC 16 한국 대표 KAIA(한국 무인항공기협회) 가 처리. 사용자 환경 의존.

---

## 6. 참조

- ISO/TC 20/SC 16 위원회: <https://www.iso.org/committee/5336224.html> (외부)
- KAIA 한국무인항공기협회: <https://kaia.or.kr> (외부)
- `docs/standards/SDACS_ASTM_F38_PROPOSAL.md` — Phase 461 (자매 문서)
- `docs/SIMULATOR_ODYSSEY_PLAN.md` Track 🏛 — Phase 461-480
- `simulation/federation_*.py` — 9 모듈 정합 자산
