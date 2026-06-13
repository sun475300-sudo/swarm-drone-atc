# 🌐 ICAO 공역 클래스 A-G ↔ SDACS 고도 레이어 매핑 (ODYSSEY Phase 408)

*Created: 2026-06-12 · 근거: ICAO Annex 11 (Air Traffic Services), 항공안전법 시행규칙 §155*

> SDACS는 현재 9층 고도 레이어(`ALTITUDE_LAYERS`)와 NFZ·회랑으로 공역을 표현한다.
> 본 문서는 이를 **ICAO Class A-G 표준 공역 분류**에 매핑해 국제 호환성을 확보하기 위한 시작점이다.

---

## 1. ICAO 공역 클래스 정의 (요약)

| 클래스 | IFR | VFR | 관제 | 분리 | 통상 고도 |
|:-:|:-:|:-:|---|---|---|
| A | ✓ | ✗ | 강제 | IFR-IFR | FL180+ (5,486m+) |
| B | ✓ | ✓ | 강제 | 모두-모두 | 공항 주변 |
| C | ✓ | ✓ | IFR 강제·VFR 권고 | IFR-IFR, IFR-VFR | 중간 공항 |
| D | ✓ | ✓ | 강제 | IFR-IFR | 소규모 공항 |
| E | ✓ | ✓ | IFR 강제·VFR 자유 | IFR-IFR | 통제구역 |
| F | ✓ | ✓ | 권고만 | (조언) | 농촌 |
| G | ✓ | ✓ | 비통제 | 없음 | 지상~150m AGL |

> 한국은 A·B·C·D·E·G만 운용 (F 미사용). 무인비행장치는 **150m AGL 이하 (Class G)** 가 기본 운용 공역.

## 2. SDACS 9층 고도 레이어 (현행)

```javascript
ALTITUDE_LAYERS = [0, 30, 60, 90, 120, 150, 180, 210, 240]  // 단위: m AGL
```

| 레이어 | 고도 (m) | 용도 |
|:-:|:-:|---|
| L0 | 0 | 지상·이착륙 |
| L1 | 30 | 저고도 운반·검사 |
| L2 | 60 | 표준 순항 (소형) |
| L3 | 90 | 회랑 순항 |
| L4 | 120 | 회랑 순항 |
| L5 | 150 | **법정 상한** (Class G 경계) |
| L6 | 180 | 특별승인 필요 (Class E 진입) |
| L7 | 210 | 특별승인 필요 |
| L8 | 240 | 시뮬 한계 |

## 3. 매핑 매트릭스

| SDACS 레이어 | ICAO 클래스 (한국 적용) | SDACS 모듈 | 인증 요건 (SORA) |
|:-:|:-:|---|---|
| L0 — L5 (0~150m) | **G** (비통제) | 5계층 안전망 전부 | `soraAssess({populationDensity:'sparse'})` → SAIL II 통상 |
| L5 — L6 (150~180m) | **E** (통제 진입) | + 사전 비행승인 (UTM) | `soraAssess({bvlos:true})` → 특별승인 |
| L6 — L8 (180m+) | **D/C** (관제권) | + ATC 통신 의무 | SORA SAIL III+ |
| 공항 주변 NFZ | **B** | NFZ 지오펜스 + UTM 차단 | 운영 금지 |
| 군 작전 공역 | **(R/D)** | NOTAM + 동적 NFZ | 특별승인·면제 |

## 4. SDACS 기능 ↔ 공역 클래스 요구사항

| ICAO 요구 | SDACS 충족 | 모듈 |
|---|---|---|
| 분리 표준 (Class C/D, IFR-IFR 1000ft 수직) | CPA 90초 + APF + CBS 계층 협조 | 5계층 안전망 |
| 관제 통신 (Class C/D) | ATC 명령 9종 + 음성(TTS) | `_sdacs.atcCommand()` |
| Transponder (Mode S/ADS-B) | ADS-B 수신만 (송출은 사용자 HW) | `src/utm/adsb_receiver.py` |
| Remote ID (모든 비통제 운영) | ASTM F3411 v2.0 | `src/utm/remote_id.py` |
| NOTAM 준수 | NOTAM 매니저 + 시뮬 NFZ | `src/utm/notam_manager.py` |
| 비행계획 제출 (Class B/C/D) | 비행계획 양식 (GENESIS 303 계획) | (미구현 — 격상 대상) |

## 5. 갭 분석

| 영역 | 현재 | 격차 | 격상 |
|---|---|---|---|
| 9층 → A-G 자동 매핑 | 수동 매트릭스 | API 미제공 | 차기: `_sdacs.airspaceClass(altitude, location)` 신설 후보 |
| Class B/C 진입 차단 | 정적 NFZ로 표현 | 동적 NOTAM 미반영 | GENESIS 303 + Phase 24 NOTAM 격상 |
| ICAO 표준 보고 양식 | 미지원 | 사고 보고 Class별 차이 | GENESIS 307 사고 보고 격상 시 통합 |

## 6. 차기 격상 제안 (API 신설)

```typescript
// 신설 후보 — _sdacs.airspaceClass(altitudeM, lon?, lat?) → 'A'..'G' | 'R'(restricted)
// 결정 규칙 (sandbox 가능, 한국 특화):
//   1) altitude > 240m or lon/lat가 공항 NFZ 안 → 'B'
//   2) altitude in (150, 240] → 'E'
//   3) altitude in [0, 150] AND not in NFZ → 'G'
//   4) NFZ 안이지만 비행 가능(특별승인) → 'D'
//   5) 군 작전 공역 NFZ → 'R'
```

격상 시 production 등급 부여 (결정적 산정). E2E 테스트 5건 동반 권장.

## 🔗 관련
- [`AIR_SAFETY_ACT_MATRIX.md`](AIR_SAFETY_ACT_MATRIX.md) — 항공안전법 §127 등 (Phase 301)
- [`RTM_5LAYER_COVERAGE.md`](RTM_5LAYER_COVERAGE.md) — L5 UTM 추적 (Phase 306)
- [`../SIMULATOR_ODYSSEY_PLAN.md`](../SIMULATOR_ODYSSEY_PLAN.md) — Track 🌏 Global Expansion Phase 401-420
- 외부: [ICAO Annex 11](https://store.icao.int/en/annex-11-air-traffic-services) · [한국 항공정보 (AIP)](https://aim.koca.go.kr/)
