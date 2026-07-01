# GUTMA 회원 활동 시나리오 — SDACS 기고 적합성

> ODYSSEY Phase 410 · Track 🌏 International Expansion
> 산출물: [`simulation/gutma_contribution.py`](../../simulation/gutma_contribution.py) ·
> 테스트 [`tests/test_gutma_contribution.py`](../../tests/test_gutma_contribution.py) (49 PASS)

## 1. 목적

GUTMA(Global UTM Association)는 UTM 상호운용을 위한 공개 기술 사양을 산출하는
산업 컨소시엄이다. 본 문서는 SDACS가 GUTMA 회원으로서 **어떤 작업 항목에 무엇으로
기여할 수 있는가**를 결정적 매트릭스로 정리한다. Phase 401(EASA U-space)·407(ICAO
UTM)의 자매편으로, 같은 기능 자산을 GUTMA의 작업그룹 축으로 재평가한다.

본 매핑은 **기능적 기여 가능성** 평가이며 GUTMA 공식 채택이 아니다(법적·표준화
구속력 없음).

## 2. 작업그룹(Working Group)

| 코드 | 작업그룹 |
|---|---|
| **FDP** | Flight Declaration Protocol — 비행 선언 교환 |
| **USSI** | USS Interoperability & Discovery — USS 상호운용·발견 |
| **DATA** | Data Common Dictionary & GeoJSON — 공통 데이터·공역 표현 |
| **NRID** | Network Remote ID — 네트워크 원격 식별 |
| **SURV** | Surveillance Data Exchange — 감시 데이터 교환 |

## 3. 기고 준비도 상태(정직성 3값)

- **ready** — 참조 구현으로 즉시 기여 가능한 모듈 보유.
- **partial** — 관련 모듈은 있으나 사양 일부만 충족(추가 작업 필요).
- **gap** — 대응 모듈 없음. 기여 불가를 정직히 표면화한다.

**정직성 결속**: `status == "gap"` ⟺ `sdacs_module is None`. `ready`·`partial`은
반드시 디스크에 실재하는 모듈을 인용하며, 테스트
`test_cited_modules_exist_on_disk`가 인용 경로의 실재를 결정적으로 강제한다.
모듈 없는 기여 주장을 구조적으로 금지한다.

## 4. 기고 매트릭스

| 그룹 | 작업 항목 | 상태 | SDACS 참조 구현 |
|---|---|:--:|---|
| FDP | Flight Declaration Protocol | ✓ ready | `simulation/flight_plan_filing.py` |
| FDP | Operation Plan Sharing | ✓ ready | `simulation/operational_intent.py` |
| USSI | USS-to-USS Interoperability | ~ partial | `simulation/federation_conflict_resolution.py` |
| USSI | Discovery & Synchronization Service | ✗ gap | — (호스팅형 DSS 미운영) |
| DATA | GeoJSON Airspace Representation | ✓ ready | `simulation/geo_zones.py` |
| DATA | Geo-awareness Data Exchange | ✓ ready | `simulation/geofence_manager.py` |
| NRID | Network Remote ID | ✓ ready | `simulation/remote_id.py` |
| SURV | Surveillance Data Exchange | ~ partial | `simulation/telemetry_validator.py` |
| SURV | Conformance Monitoring Feedback | ✓ ready | `simulation/compliance_checker.py` |

**준비도 요약**: 9개 항목 — ready 6 · partial 2 · gap 1 · 가중 준비도 **78%**.

## 5. 정직히 표면화된 갭

- **Discovery & Synchronization Service (호스팅형 DSS)** — GUTMA/ASTM F3548-21의
  DSS는 다중 USS가 공유하는 호스팅 발견·동기화 서비스다. SDACS는 단일 인스턴스
  연합(`federation_conflict_resolution.py`)을 통한 인접 공역 협조는 제공하나,
  호스팅형 DSS 운영은 현 범위 밖이다. 이는 USSI 작업그룹 기여 시 명시할 한계다.

## 6. 근거(권위 있는 공개 출처)

- GUTMA Flight Declaration Protocol — `gutma/flight_declaration_protocol`
- GUTMA USS Interoperability / Discovery & Synchronization (ASTM F3548-21 DSS 정렬)
- GUTMA Data Common Dictionary + GeoJSON 공역/UAS Volume 표현
- ASTM F3411 Network Remote ID

## 7. 사용

```bash
python simulation/gutma_contribution.py --report      # 기고 준비도 요약
python simulation/gutma_contribution.py --matrix      # 전체 기고 매트릭스
python simulation/gutma_contribution.py --group FDP   # 작업그룹별 항목
python simulation/gutma_contribution.py --gaps        # 미대응(갭) 항목
```

표준화 기고 추적은 [`simulation/standardization_tracker.py`](../../simulation/standardization_tracker.py)
(Phase 470, STD-08 GUTMA)가 단일 출처로 관리한다.
